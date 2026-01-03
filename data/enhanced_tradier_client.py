#!/usr/bin/env python3
"""
Enhanced Tradier Client
Client Tradier optimisé avec support complet des options et Greeks
Basé sur les bonnes idées du options_screening_starter.py
"""

import os
import time
import requests
from typing import Dict, List, Any, Optional
import logging
from dataclasses import dataclass
import re

# Configuration des logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class OptionsContract:
    """Contrat d'option avec données de marché complètes"""
    symbol: str
    underlying: str
    expiration: str
    strike: float
    option_type: str  # 'call' ou 'put'
    bid: float
    ask: float
    last: float
    volume: int
    open_interest: int
    change: float = 0.0
    change_percentage: float = 0.0
    
    # Greeks (si disponibles)
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    rho: Optional[float] = None
    implied_volatility: Optional[float] = None
    
    # Métriques calculées
    intrinsic_value: Optional[float] = None
    extrinsic_value: Optional[float] = None
    mid_price: Optional[float] = None
    spread: Optional[float] = None
    spread_percentage: Optional[float] = None
    moneyness: Optional[str] = None  # ITM, OTM, ATM
    
    def __post_init__(self):
        """Calcul des métriques dérivées"""
        # Prix médian
        if self.bid > 0 and self.ask > 0:
            self.mid_price = (self.bid + self.ask) / 2
            self.spread = self.ask - self.bid
            if self.bid > 0:
                self.spread_percentage = (self.spread / self.bid) * 100
        
        # Valeur extrinsèque (si prix connu)
        if self.last > 0 and self.intrinsic_value is not None:
            self.extrinsic_value = max(0, self.last - self.intrinsic_value)
    
    def calculate_moneyness(self, underlying_price: float) -> str:
        """Calcule si l'option est ITM, OTM ou ATM"""
        if self.option_type.lower() == 'call':
            if underlying_price > self.strike:
                return 'ITM'
            elif abs(underlying_price - self.strike) < 0.01:
                return 'ATM'
            else:
                return 'OTM'
        else:  # put
            if underlying_price < self.strike:
                return 'ITM'
            elif abs(underlying_price - self.strike) < 0.01:
                return 'ATM'
            else:
                return 'OTM'
    
    def calculate_intrinsic_value(self, underlying_price: float) -> float:
        """Calcule la valeur intrinsèque"""
        if self.option_type.lower() == 'call':
            return max(0, underlying_price - self.strike)
        else:  # put
            return max(0, self.strike - underlying_price)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit le contrat en dictionnaire avec sanitisation"""
        import math
        
        def sanitize_float(value):
            if isinstance(value, float) and (math.isinf(value) or math.isnan(value)):
                return 0.0
            return value
        
        return {
            'symbol': self.symbol,
            'underlying': self.underlying,
            'expiration': self.expiration,
            'strike': sanitize_float(self.strike),
            'option_type': self.option_type,
            'bid': sanitize_float(self.bid),
            'ask': sanitize_float(self.ask),
            'last': sanitize_float(self.last),
            'volume': self.volume,
            'open_interest': self.open_interest,
            'change': sanitize_float(self.change),
            'change_percentage': sanitize_float(self.change_percentage),
            'delta': sanitize_float(self.delta),
            'gamma': sanitize_float(self.gamma),
            'theta': sanitize_float(self.theta),
            'vega': sanitize_float(self.vega),
            'rho': sanitize_float(self.rho),
            'implied_volatility': sanitize_float(self.implied_volatility),
            'intrinsic_value': sanitize_float(self.intrinsic_value),
            'extrinsic_value': sanitize_float(self.extrinsic_value),
            'mid_price': sanitize_float(self.mid_price),
            'spread': sanitize_float(self.spread),
            'spread_percentage': sanitize_float(self.spread_percentage),
            'moneyness': self.moneyness
        }

class OptionsSymbolParser:
    """Parseur de symboles d'options OCC standard"""
    
    @staticmethod
    def parse_option_symbol(symbol: str) -> Optional[Dict[str, Any]]:
        """
        Parse un symbole d'option format OCC
        Exemple: AAPL240315C00150000 -> AAPL, 2024-03-15, Call, 150.00
        """
        try:
            if len(symbol) < 18:
                return None
            
            # Format: TICKER + YYMMDD + C/P + PPPPPPPP (strike * 1000)
            pattern = r'^([A-Z]{1,5})(\d{6})([CP])(\d{8})$'
            match = re.match(pattern, symbol)
            
            if not match:
                return None
            
            ticker = match.group(1)
            date_str = match.group(2)  # YYMMDD
            option_type = 'call' if match.group(3) == 'C' else 'put'
            strike_int = int(match.group(4))
            strike = strike_int / 1000.0
            
            # Conversion de la date
            year = 2000 + int(date_str[:2])
            month = int(date_str[2:4])
            day = int(date_str[4:6])
            expiration = f"{year:04d}-{month:02d}-{day:02d}"
            
            return {
                'underlying': ticker,
                'expiration': expiration,
                'option_type': option_type,
                'strike': strike,
                'parsed': True
            }
            
        except Exception as e:
            logger.error(f"Erreur parsing symbole {symbol}: {e}")
            return None

class EnhancedTradierClient:
    """Client Tradier optimisé pour les options avec support des Greeks"""
    
    def __init__(self, api_token: str, sandbox: Optional[bool] = None):
        self.api_token = api_token
        
        # Détection automatique de l'environnement si non spécifié
        if sandbox is None:
            # Essaie d'importer Config pour détecter l'environnement
            try:
                import sys
                import os
                sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'utils'))
                from config import Config
                self.sandbox = Config.is_development_mode()
                # Utilise la clé de la config au lieu du paramètre
                self.api_token = Config.get_tradier_api_key()
            except ImportError:
                # Fallback: production par défaut si pas de config
                self.sandbox = False
                logger.warning("Config non disponible, utilisation de la production par défaut")
        else:
            self.sandbox = sandbox
        
        self.base_url = "https://sandbox.tradier.com/v1" if self.sandbox else "https://api.tradier.com/v1"
        self.headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Accept': 'application/json'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Cache pour éviter les appels répétés
        self.cache = {}
        self.cache_ttl = 60  # secondes
        
        # Parser de symboles
        self.symbol_parser = OptionsSymbolParser()
        
        environment = "sandbox" if self.sandbox else "production"
        logger.info(f"Enhanced Tradier client initialisé (environnement: {environment})")
    
    def get_options_chains(self, symbol: str, expiration: Optional[str] = None,
                          strikes: Optional[List[float]] = None) -> List[OptionsContract]:
        """
        Récupère la chaîne d'options complète pour un symbole
        
        Args:
            symbol: Symbole du sous-jacent (ex: AAPL)
            expiration: Date d'expiration spécifique (YYYY-MM-DD)
            strikes: Liste de strikes spécifiques à récupérer
        
        Returns:
            Liste des contrats d'options
        """
        # L'expiration est toujours obligatoire selon l'API Tradier
        if not expiration:
            # Récupérer d'abord les expirations disponibles
            expirations = self.get_options_expirations(symbol)
            if not expirations:
                logger.warning(f"Aucune expiration trouvée pour {symbol}")
                return []
            # Utiliser la première expiration disponible
            expiration = expirations[0]
            logger.info(f"Auto-sélection expiration {expiration} pour {symbol}")
        
        cache_key = f"chains_{symbol}_{expiration}_{strikes}"
        
        # Vérification cache
        if self._is_cached_valid(cache_key):
            return self.cache[cache_key]['data']
        
        url = f"{self.base_url}/markets/options/chains"
        params = {
            'symbol': symbol,
            'greeks': 'true'  # Demander les Greeks dans la réponse
        }
        
        if expiration:
            params['expiration'] = expiration
        
        try:
            logger.info(f"Récupération chaîne options pour {symbol}")
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            contracts = self._parse_options_chains(data, symbol)
            
            # Filtrage par strikes si spécifié
            if strikes:
                contracts = [c for c in contracts if c.strike in strikes]
            
            # Mise en cache
            self.cache[cache_key] = {
                'data': contracts,
                'timestamp': time.time()
            }
            
            logger.info(f"Récupéré {len(contracts)} contrats pour {symbol}")
            return contracts
            
        except Exception as e:
            logger.error(f"Erreur récupération chaîne {symbol}: {e}")
            return []
    
    def get_options_quotes(self, symbols: List[str]) -> Dict[str, OptionsContract]:
        """
        Récupère les cotations pour plusieurs contrats d'options
        
        Args:
            symbols: Liste de symboles d'options
        
        Returns:
            Dictionnaire {symbol: OptionsContract}
        """
        if not symbols:
            return {}
        
        # Tradier limite à 200 symboles par requête
        all_quotes = {}
        chunk_size = 200
        
        for i in range(0, len(symbols), chunk_size):
            chunk = symbols[i:i + chunk_size]
            quotes = self._get_options_quotes_chunk(chunk)
            all_quotes.update(quotes)
            
            # Pause pour respecter les limites d'API
            if len(symbols) > chunk_size:
                time.sleep(0.1)
        
        return all_quotes
    
    def _get_options_quotes_chunk(self, symbols: List[str]) -> Dict[str, OptionsContract]:
        """Récupère les cotations pour un chunk de symboles"""
        cache_key = f"quotes_{'_'.join(sorted(symbols))}"
        
        if self._is_cached_valid(cache_key):
            return self.cache[cache_key]['data']
        
        url = f"{self.base_url}/markets/options/quotes"
        params = {
            'symbols': ','.join(symbols),
            'greeks': 'true'  # Demander les Greeks dans la réponse
        }
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            quotes = self._parse_options_quotes(data)
            
            # Mise en cache
            self.cache[cache_key] = {
                'data': quotes,
                'timestamp': time.time()
            }
            
            return quotes
            
        except Exception as e:
            logger.error(f"Erreur récupération quotes: {e}")
            return {}
    
    def get_options_expirations(self, symbol: str) -> List[str]:
        """
        Récupère les dates d'expiration disponibles pour un symbole
        
        Returns:
            Liste des dates d'expiration (YYYY-MM-DD)
        """
        cache_key = f"expirations_{symbol}"
        
        if self._is_cached_valid(cache_key):
            return self.cache[cache_key]['data']
        
        url = f"{self.base_url}/markets/options/expirations"
        params = {'symbol': symbol}
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            expirations = []
            if 'expirations' in data and data['expirations'] and 'date' in data['expirations']:
                dates = data['expirations']['date']
                if isinstance(dates, str):
                    dates = [dates]
                expirations = dates
            
            # Mise en cache
            self.cache[cache_key] = {
                'data': expirations,
                'timestamp': time.time()
            }
            
            return expirations
            
        except Exception as e:
            logger.error(f"Erreur récupération expirations {symbol}: {e}")
            return []
    
    def get_options_strikes(self, symbol: str, expiration: str) -> List[float]:
        """
        Récupère les strikes disponibles pour un symbole et une expiration
        
        Returns:
            Liste des strikes disponibles
        """
        url = f"{self.base_url}/markets/options/strikes"
        params = {
            'symbol': symbol,
            'expiration': expiration
        }
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            strikes = []
            if 'strikes' in data and data['strikes'] and 'strike' in data['strikes']:
                strike_data = data['strikes']['strike']
                if isinstance(strike_data, list):
                    strikes = [float(s) for s in strike_data]
                else:
                    strikes = [float(strike_data)]
            
            return strikes
            
        except Exception as e:
            logger.error(f"Erreur récupération strikes {symbol}: {e}")
            return []
    
    def get_multiple_underlying_quotes(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Récupère les cotations de plusieurs sous-jacents en un seul appel API
        
        Args:
            symbols: Liste des symboles de sous-jacents
            
        Returns:
            Dictionnaire {symbole: données_quote} pour chaque symbole
        """
        if not symbols:
            return {}
        
        # Suppression des doublons et nettoyage
        unique_symbols = list(set(s.upper().strip() for s in symbols if s.strip()))
        
        if not unique_symbols:
            return {}
        
        # Clé de cache pour cette combinaison de symboles
        cache_key = f"multi_underlying_{'_'.join(sorted(unique_symbols))}"
        
        if self._is_cached_valid(cache_key, ttl=30):  # Cache court pour temps réel
            return self.cache[cache_key]['data']
        
        # Paramètres pour l'API Tradier (accepte plusieurs symboles séparés par virgule)
        url = f"{self.base_url}/markets/quotes"
        params = {'symbols': ','.join(unique_symbols)}
        
        logger.info(f"📊 Récupération quotes multiples: {', '.join(unique_symbols)}")
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            quotes_dict = {}
            
            if 'quotes' in data and data['quotes'] and 'quote' in data['quotes']:
                quote_data = data['quotes']['quote']
                
                # L'API peut retourner un dict (1 symbole) ou une liste (plusieurs symboles)
                if isinstance(quote_data, dict):
                    quote_data = [quote_data]
                
                for quote in quote_data:
                    symbol = quote.get('symbol', '').upper()
                    if symbol:
                        quotes_dict[symbol] = {
                            'symbol': symbol,
                            'last': self._safe_float(quote.get('last')),
                            'price': self._safe_float(quote.get('last')),  # Alias pour compatibilité
                            'bid': self._safe_float(quote.get('bid')),
                            'ask': self._safe_float(quote.get('ask')),
                            'change': self._safe_float(quote.get('change')),
                            'change_percentage': self._safe_float(quote.get('change_percentage')),
                            'volume': self._safe_int(quote.get('volume')),
                            'high': self._safe_float(quote.get('high')),
                            'low': self._safe_float(quote.get('low')),
                            'open': self._safe_float(quote.get('open')),
                            'prevclose': self._safe_float(quote.get('prevclose')),
                            'type': quote.get('type', 'stock')
                        }
            
            # Mise en cache
            if quotes_dict:
                self.cache[cache_key] = {
                    'data': quotes_dict,
                    'timestamp': time.time()
                }
                
                logger.info(f"✅ Récupéré {len(quotes_dict)} quotes: {', '.join(quotes_dict.keys())}")
            else:
                logger.warning(f"⚠️ Aucune quote récupérée pour: {', '.join(unique_symbols)}")
            
            return quotes_dict
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération quotes multiples {unique_symbols}: {e}")
            return {}
    
    def get_underlying_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Récupère la cotation d'un seul sous-jacent
        Utilise la méthode optimisée pour maintenir la compatibilité
        
        Args:
            symbol: Symbole du sous-jacent
            
        Returns:
            Dictionnaire avec les données du sous-jacent ou None si non trouvé
        """
        # Utilise la méthode optimisée pour éviter la duplication de code
        quotes = self.get_multiple_underlying_quotes([symbol])
        return quotes.get(symbol.upper())
    
    def _parse_options_chains(self, data: Dict[str, Any], underlying: str) -> List[OptionsContract]:
        """Parse la réponse de l'API chains en liste de contrats"""
        contracts = []
        
        try:
            if 'options' not in data or not data['options']:
                return contracts
            
            options_data = data['options']
            if 'option' not in options_data:
                return contracts
            
            option_list = options_data['option']
            if not isinstance(option_list, list):
                option_list = [option_list]
            
            for option in option_list:
                contract = self._create_contract_from_data(option, underlying)
                if contract:
                    contracts.append(contract)
                    
        except Exception as e:
            logger.error(f"Erreur parsing chains: {e}")
        
        return contracts
    
    def _parse_options_quotes(self, data: Dict[str, Any]) -> Dict[str, OptionsContract]:
        """Parse la réponse de l'API quotes en dictionnaire de contrats"""
        quotes = {}
        
        try:
            if 'quotes' not in data or not data['quotes']:
                return quotes
            
            quotes_data = data['quotes']
            if 'quote' not in quotes_data:
                return quotes
            
            quote_list = quotes_data['quote']
            if not isinstance(quote_list, list):
                quote_list = [quote_list]
            
            for quote in quote_list:
                symbol = quote.get('symbol')
                if symbol:
                    # Parse le symbole pour obtenir les détails
                    parsed = self.symbol_parser.parse_option_symbol(symbol)
                    if parsed:
                        underlying = parsed['underlying']
                        contract = self._create_contract_from_data(quote, underlying)
                        if contract:
                            quotes[symbol] = contract
                            
        except Exception as e:
            logger.error(f"Erreur parsing quotes: {e}")
        
        return quotes
    
    def _safe_float(self, value, default=0.0):
        """Conversion sécurisée vers float avec sanitisation"""
        if value is None:
            return default
        try:
            result = float(value)
            # Vérifier si la valeur est inf ou NaN
            if not self._is_valid_float(result):
                logger.warning(f"⚠️ Valeur float invalide détectée: {result}, utilisation de la valeur par défaut {default}")
                return default
            return result
        except (ValueError, TypeError):
            return default
    
    def _safe_int(self, value, default=0):
        """Conversion sécurisée vers int"""
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def _is_valid_float(self, value: float) -> bool:
        """Vérifie si une valeur float est valide (pas inf ou NaN)"""
        import math
        return not (math.isinf(value) or math.isnan(value))
    
    def sanitize_for_json(self, data):
        """Sanitise récursivement les données pour la sérialisation JSON"""
        import math
        
        if isinstance(data, dict):
            return {key: self.sanitize_for_json(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self.sanitize_for_json(item) for item in data]
        elif isinstance(data, float):
            if math.isinf(data) or math.isnan(data):
                logger.warning(f"⚠️ Valeur float invalide sanitizée: {data} -> 0.0")
                return 0.0
            return data
        else:
            return data
    
    def _extract_greek(self, option_data: Dict[str, Any], greek_name: str) -> float:
        """Extrait une valeur Greek de l'objet greeks ou directement de l'option"""
        symbol = option_data.get('symbol', 'UNKNOWN')
        
        # DEBUG: Afficher les données brutes greeks la première fois
        if 'greeks' in option_data and option_data['greeks'] and greek_name == 'delta':
            logger.debug(f"   🔍 DEBUG: Données greeks brutes pour {symbol}: {option_data['greeks']}")
        
        # Essaie d'abord depuis l'objet greeks (quand greeks=true)
        if 'greeks' in option_data and option_data['greeks']:
            greeks = option_data['greeks']
            if isinstance(greeks, dict) and greek_name in greeks:
                raw_value = greeks[greek_name]
                if raw_value is not None:
                    try:
                        greek_value = float(raw_value)
                        logger.debug(f"   ✅ {greek_name.upper()} {symbol}: {greek_value} (depuis greeks)")
                        return greek_value
                    except (ValueError, TypeError):
                        logger.warning(f"   ⚠️ Impossible de convertir {greek_name.upper()} pour {symbol}: {raw_value}")
        
        # Fallback : directement depuis l'option (ancien format)
        direct_value = option_data.get(greek_name)
        if direct_value is not None:
            try:
                greek_value = float(direct_value)
                logger.debug(f"   ✅ {greek_name.upper()} {symbol}: {greek_value} (direct)")
                return greek_value
            except (ValueError, TypeError):
                pass
        
        logger.debug(f"   ❌ {greek_name.upper()} {symbol}: 0.0 (fallback)")
        return 0.0
    
    def _is_greek_value_valid(self, greek_name: str, value: float, symbol: str) -> bool:
        """Valide si une valeur Greek est cohérente"""
        if value is None or value == 0:
            return False
            
        # Validations spécifiques par Greek
        if greek_name == 'delta':
            # Delta doit être entre -1 et 1
            return -1 <= value <= 1
        elif greek_name == 'gamma':
            # Gamma doit être positif et pas trop élevé
            return 0 <= value <= 1
        elif greek_name == 'theta':
            # Theta est généralement négatif pour les options longues
            return -1000 <= value <= 1000  # Large plage pour accepter différentes unités
        elif greek_name == 'vega':
            # Vega doit être positif
            return 0 <= value <= 1000
        elif greek_name == 'rho':
            # Rho peut être positif ou négatif
            return -1000 <= value <= 1000
        
        return True
    
    def _estimate_greek_value(self, option_data: Dict[str, Any], greek_name: str) -> float:
        """Estime une valeur Greek basique si les données sont manquantes"""
        # Pour l'instant, retourner 0 - nous pourrions implémenter des estimations plus sophistiquées
        return 0.0
    
    def _extract_iv(self, option_data: Dict[str, Any]) -> float:
        """Extrait la volatilité implicite depuis l'objet greeks ou option"""
        symbol = option_data.get('symbol', 'UNKNOWN')
        
        # Essaie depuis l'objet greeks (priorité : mid_iv > bid_iv/ask_iv > smv_vol)
        if 'greeks' in option_data and option_data['greeks']:
            greeks = option_data['greeks']
            
            if isinstance(greeks, dict):
                # 1. Préférer mid_iv si disponible et > 0
                mid_iv = greeks.get('mid_iv')
                if mid_iv is not None and float(mid_iv) > 0:
                    iv = float(mid_iv)
                    logger.debug(f"   ✅ IV {symbol}: {iv:.4f} (mid_iv)")
                    return iv
                
                # 2. Moyenne de bid_iv et ask_iv si disponibles
                bid_iv = greeks.get('bid_iv', 0) or 0
                ask_iv = greeks.get('ask_iv', 0) or 0
                bid_iv = float(bid_iv) if bid_iv else 0
                ask_iv = float(ask_iv) if ask_iv else 0
                
                if bid_iv > 0 or ask_iv > 0:
                    iv = (bid_iv + ask_iv) / 2 if (bid_iv > 0 and ask_iv > 0) else (bid_iv or ask_iv)
                    logger.debug(f"   ✅ IV {symbol}: {iv:.4f} (bid/ask: {bid_iv:.4f}/{ask_iv:.4f})")
                    return iv
                
                # 3. Fallback sur smv_vol (Smart Money Vol)
                smv_vol = greeks.get('smv_vol')
                if smv_vol is not None and float(smv_vol) > 0:
                    iv = float(smv_vol)
                    logger.debug(f"   ✅ IV {symbol}: {iv:.4f} (smv_vol)")
                    return iv
        
        # 4. Fallback : directement depuis l'option
        direct_iv = option_data.get('implied_volatility')
        if direct_iv and float(direct_iv) > 0:
            iv = float(direct_iv)
            logger.debug(f"   ✅ IV {symbol}: {iv:.4f} (direct)")
            return iv
        
        # Si aucune IV trouvée, retourner 0
        logger.debug(f"   ❌ IV {symbol}: 0.0000 (pas de données)")
        return 0.0
    
    def _create_contract_from_data(self, option_data: Dict[str, Any], underlying: str) -> Optional[OptionsContract]:
        """Crée un OptionsContract à partir des données API avec parsing sécurisé"""
        try:
            symbol = option_data.get('symbol', '')
            
            # Parse le symbole si les détails ne sont pas fournis
            parsed = self.symbol_parser.parse_option_symbol(symbol)
            
            expiration = option_data.get('expiration_date', '')
            if not expiration and parsed:
                expiration = parsed['expiration']
            
            strike = option_data.get('strike')
            if strike is None and parsed:
                strike = parsed['strike']
            
            option_type = option_data.get('option_type', '')
            if not option_type and parsed:
                option_type = parsed['option_type']
            
            # Parsing sécurisé des valeurs numériques
            contract = OptionsContract(
                symbol=symbol,
                underlying=underlying,
                expiration=expiration,
                strike=self._safe_float(strike),
                option_type=option_type,
                bid=self._safe_float(option_data.get('bid')),
                ask=self._safe_float(option_data.get('ask')),
                last=self._safe_float(option_data.get('last')),
                volume=self._safe_int(option_data.get('volume')),
                open_interest=self._safe_int(option_data.get('open_interest')),
                change=self._safe_float(option_data.get('change')),
                change_percentage=self._safe_float(option_data.get('change_percentage')),
                
                # Greeks (dans l'objet 'greeks' quand greeks=true est passé)
                delta=self._safe_float(self._extract_greek(option_data, 'delta')),
                gamma=self._safe_float(self._extract_greek(option_data, 'gamma')),
                theta=self._safe_float(self._extract_greek(option_data, 'theta')),
                vega=self._safe_float(self._extract_greek(option_data, 'vega')),
                rho=self._safe_float(self._extract_greek(option_data, 'rho')),
                implied_volatility=self._safe_float(self._extract_iv(option_data))
            )
            
            return contract
            
        except Exception as e:
            logger.error(f"Erreur création contrat: {e}")
            return None
    
    def _is_cached_valid(self, cache_key: str, ttl: Optional[int] = None) -> bool:
        """Vérifie si une entrée de cache est valide"""
        if cache_key not in self.cache:
            return False
        
        ttl = ttl or self.cache_ttl
        age = time.time() - self.cache[cache_key]['timestamp']
        return age < ttl
    
    def clear_cache(self):
        """Vide le cache"""
        self.cache.clear()
    
    def get_market_status(self) -> Dict[str, Any]:
        """Récupère le statut du marché"""
        url = f"{self.base_url}/markets/clock"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            
            if 'clock' in data:
                return data['clock']
            
        except Exception as e:
            logger.error(f"Erreur récupération statut marché: {e}")
        
        return {}

# Exemple d'utilisation et test
if __name__ == "__main__":
    # Configuration
    TRADIER_TOKEN = os.getenv('TRADIER_API_TOKEN')
    
    if not TRADIER_TOKEN:
        print("❌ TRADIER_API_TOKEN requis!")
        exit(1)
    
    # Initialisation du client
    client = EnhancedTradierClient(TRADIER_TOKEN, sandbox=True)
    
    # Test avec AAPL
    symbol = "AAPL"
    
    print(f"🔍 Test du client Tradier avec {symbol}")
    print("="*50)
    
    # 1. Récupération du sous-jacent
    underlying = client.get_underlying_quote(symbol)
    if underlying:
        print(f"📈 Sous-jacent {symbol}:")
        print(f"  Prix: ${underlying['price']:.2f}")
        print(f"  Changement: {underlying['change']:+.2f} ({underlying['change_percentage']:+.2f}%)")
    
    # 2. Récupération des expirations
    expirations = client.get_options_expirations(symbol)
    if expirations:
        print(f"\n📅 Expirations disponibles: {len(expirations)}")
        print(f"  Prochaines: {expirations[:3]}")
    
    # 3. Récupération d'une chaîne d'options
    if expirations:
        chains = client.get_options_chains(symbol, expirations[0])
        print(f"\n⛓️ Chaîne pour {expirations[0]}: {len(chains)} contrats")
        
        # Affiche quelques contrats
        calls = [c for c in chains if c.option_type == 'call'][:5]
        puts = [c for c in chains if c.option_type == 'put'][:5]
        
        if calls:
            print("\n📞 Top 5 Calls:")
            for call in calls:
                print(f"  {call.strike:.0f} - Vol: {call.volume:,} - OI: {call.open_interest:,} - Last: ${call.last:.2f}")
        
        if puts:
            print("\n📉 Top 5 Puts:")
            for put in puts:
                print(f"  {put.strike:.0f} - Vol: {put.volume:,} - OI: {put.open_interest:,} - Last: ${put.last:.2f}")
    
    # 4. Test de quotes multiples
    if chains:
        test_symbols = [c.symbol for c in chains[:5]]
        quotes = client.get_options_quotes(test_symbols)
        print(f"\n💰 Quotes pour {len(quotes)} contrats récupérées")
    
    print("\n✅ Tests terminés!")