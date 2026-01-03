# hybrid_data_manager.py - Architecture hybride Tradier + Polygon.io optimale
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
from collections import defaultdict
import time

@dataclass
class HybridOptionData:
    """Structure unifiée pour les données d'options des deux sources"""
    # Identifiants
    symbol: str
    option_symbol: str
    underlying: str
    strike: float
    expiration: str
    option_type: str  # 'call' or 'put'
    
    # Données temps réel (Tradier)
    bid: float
    ask: float
    last_price: float
    volume: int
    open_interest: int
    bid_size: int = 0
    ask_size: int = 0
    
    # Greeks temps réel (Tradier)
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    implied_volatility: Optional[float] = None
    
    # Données historiques (Polygon.io)
    historical_avg_volume: Optional[float] = None
    volume_ratio: Optional[float] = None
    historical_volatility: Optional[float] = None
    
    # Métriques calculées
    bid_ask_spread: float = 0.0
    bid_ask_spread_pct: float = 0.0
    moneyness: float = 0.0
    time_value: float = 0.0
    
    # Scoring
    unusual_volume_score: float = 0.0
    greeks_anomaly_score: float = 0.0
    composite_score: float = 0.0
    
    # Métadonnées
    data_source: str = 'hybrid'
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        
        # Calculer les métriques dérivées
        self.bid_ask_spread = self.ask - self.bid if self.ask > 0 and self.bid > 0 else 0
        if self.last_price > 0:
            self.bid_ask_spread_pct = (self.bid_ask_spread / self.last_price) * 100

@dataclass
class UnderlyingData:
    """Données de l'underlying depuis Tradier temps réel"""
    symbol: str
    price: float
    change: float
    change_pct: float
    volume: int
    avg_volume: Optional[float] = None
    market_cap: Optional[float] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class HybridDataManager:
    """
    Gestionnaire hybride optimisant Tradier (temps réel) + Polygon.io (historique)
    
    Architecture:
    - Tradier: Source principale pour données temps réel options + Greeks
    - Polygon.io: Source historique pour tendances et moyennes
    - Fusion intelligente des données
    """
    
    def __init__(self, tradier_api_key: str, polygon_api_key: Optional[str] = None):
        self.tradier_api_key = tradier_api_key
        self.polygon_api_key = polygon_api_key
        
        # Tradier configuration
        self.tradier_base_url = "https://api.tradier.com/v1"
        self.tradier_headers = {
            'Authorization': f'Bearer {tradier_api_key}',
            'Accept': 'application/json'
        }
        
        # Polygon.io configuration (si disponible)
        self.polygon_base_url = "https://api.polygon.io"
        self.polygon_rate_limit = 12  # 12s entre requêtes pour free tier
        self.last_polygon_request = 0
        
        # Cache pour optimiser les performances
        self.underlying_cache = {}
        self.historical_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
        print("🔄 Hybrid Data Manager initialized:")
        print("   Tradier (primary): ✅")
        print(f"   Polygon.io (historical): {'✅' if polygon_api_key else '❌'}")
    
    def _make_tradier_request(self, endpoint: str, params: Dict = None) -> Dict:
        """Requête Tradier avec gestion d'erreurs"""
        if params is None:
            params = {}
        
        url = f"{self.tradier_base_url}{endpoint}"
        
        try:
            response = requests.get(url, headers=self.tradier_headers, params=params, timeout=15)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                print("⚠️ Tradier rate limit hit, waiting...")
                time.sleep(5)
                return self._make_tradier_request(endpoint, params)  # Retry once
            raise e
        except Exception as e:
            print(f"❌ Tradier request failed: {e}")
            raise e
    
    def _make_polygon_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Requête Polygon.io avec rate limiting"""
        if not self.polygon_api_key:
            return None
        
        # Rate limiting
        current_time = time.time()
        elapsed = current_time - self.last_polygon_request
        if elapsed < self.polygon_rate_limit:
            sleep_time = self.polygon_rate_limit - elapsed
            time.sleep(sleep_time)
        
        if params is None:
            params = {}
        
        params['apikey'] = self.polygon_api_key
        url = f"{self.polygon_base_url}{endpoint}"
        
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            self.last_polygon_request = time.time()
            
            if data.get('status') == 'OK':
                return data
            else:
                print(f"⚠️ Polygon.io warning: {data.get('status')}")
                return None
                
        except Exception as e:
            print(f"❌ Polygon.io request failed: {e}")
            self.last_polygon_request = time.time()
            return None
    
    def get_underlying_data(self, symbol: str) -> Optional[UnderlyingData]:
        """Récupère les données temps réel de l'underlying via Tradier"""
        
        # Vérifier le cache
        cache_key = f"underlying_{symbol}"
        if cache_key in self.underlying_cache:
            cached_data, timestamp = self.underlying_cache[cache_key]
            if (datetime.now() - timestamp).seconds < self.cache_ttl:
                return cached_data
        
        try:
            # Tradier quote endpoint
            response = self._make_tradier_request("/markets/quotes", {'symbols': symbol})
            
            quotes = response.get('quotes', {})
            if isinstance(quotes, dict):
                quote_data = quotes.get('quote', {})
            else:
                quote_data = quotes[0] if quotes else {}
            
            if not quote_data:
                return None
            
            underlying = UnderlyingData(
                symbol=symbol,
                price=float(quote_data.get('last', 0)),
                change=float(quote_data.get('change', 0)),
                change_pct=float(quote_data.get('change_percentage', 0)),
                volume=int(quote_data.get('volume', 0))
            )
            
            # Cache les données
            self.underlying_cache[cache_key] = (underlying, datetime.now())
            
            print(f"📊 {symbol}: ${underlying.price:.2f} ({underlying.change_pct:+.2f}%) Vol: {underlying.volume:,}")
            
            return underlying
            
        except Exception as e:
            print(f"❌ Error fetching underlying data for {symbol}: {e}")
            return None
    
    def get_options_chain_realtime(self, 
                                 underlying: str,
                                 expiration: str = None,
                                 option_type: str = None) -> List[HybridOptionData]:
        """
        Récupère la chaîne d'options temps réel via Tradier avec Greeks
        
        Args:
            underlying: Symbole de l'underlying (ex: 'SPY')
            expiration: Date d'expiration YYYY-MM-DD (optionnel)
            option_type: 'call' ou 'put' (optionnel)
        """
        
        print(f"📋 Fetching options chain for {underlying} (real-time + Greeks)")
        
        try:
            # 1. Récupérer les expirations disponibles
            exp_response = self._make_tradier_request("/markets/options/expirations", {'symbol': underlying})
            expirations = exp_response.get('expirations', {}).get('date', [])
            
            if not expirations:
                print(f"⚠️ No options available for {underlying}")
                return []
            
            # Filtrer les expirations si spécifié
            if expiration:
                if expiration in expirations:
                    target_expirations = [expiration]
                else:
                    print(f"⚠️ Expiration {expiration} not available for {underlying}")
                    return []
            else:
                # Prendre les 3 prochaines expirations
                target_expirations = expirations[:3]
            
            # 2. Récupérer les données sous-jacentes
            underlying_data = self.get_underlying_data(underlying)
            underlying_price = underlying_data.price if underlying_data else 0
            
            all_options = []
            
            for exp_date in target_expirations:
                try:
                    # 3. Récupérer la chaîne d'options pour cette expiration
                    chain_response = self._make_tradier_request(
                        "/markets/options/chains",
                        {'symbol': underlying, 'expiration': exp_date}
                    )
                    
                    options = chain_response.get('options', {}).get('option', [])
                    if not isinstance(options, list):
                        options = [options] if options else []
                    
                    # 4. Récupérer les Greeks pour cette expiration
                    greeks_response = self._make_tradier_request(
                        "/markets/options/strikes",
                        {'symbol': underlying, 'expiration': exp_date, 'greeks': 'true'}
                    )
                    
                    # Parser les Greeks
                    greeks_data = {}
                    strikes_data = greeks_response.get('strikes', {}).get('strike', [])
                    if not isinstance(strikes_data, list):
                        strikes_data = [strikes_data] if strikes_data else []
                    
                    for strike_info in strikes_data:
                        strike = strike_info.get('strike')
                        if strike:
                            greeks_data[f"{strike}_call"] = {
                                'delta': strike_info.get('call', {}).get('delta'),
                                'gamma': strike_info.get('call', {}).get('gamma'),
                                'theta': strike_info.get('call', {}).get('theta'),
                                'vega': strike_info.get('call', {}).get('vega'),
                                'iv': strike_info.get('call', {}).get('implied_volatility')
                            }
                            greeks_data[f"{strike}_put"] = {
                                'delta': strike_info.get('put', {}).get('delta'),
                                'gamma': strike_info.get('put', {}).get('gamma'),
                                'theta': strike_info.get('put', {}).get('theta'),
                                'vega': strike_info.get('put', {}).get('vega'),
                                'iv': strike_info.get('put', {}).get('implied_volatility')
                            }
                    
                    # 5. Créer les objets HybridOptionData
                    for option in options:
                        opt_type = option.get('option_type', '').lower()
                        
                        # Filtrer par type si spécifié
                        if option_type and opt_type != option_type:
                            continue
                        
                        strike = float(option.get('strike', 0))
                        
                        # Récupérer les Greeks pour cette option
                        greeks_key = f"{strike}_{opt_type}"
                        greeks = greeks_data.get(greeks_key, {})
                        
                        hybrid_option = HybridOptionData(
                            symbol=option.get('symbol', ''),
                            option_symbol=option.get('symbol', ''),
                            underlying=underlying,
                            strike=strike,
                            expiration=exp_date,
                            option_type=opt_type,
                            bid=float(option.get('bid', 0)),
                            ask=float(option.get('ask', 0)),
                            last_price=float(option.get('last', 0)),
                            volume=int(option.get('volume', 0)),
                            open_interest=int(option.get('open_interest', 0)),
                            bid_size=int(option.get('bidsize', 0)),
                            ask_size=int(option.get('asksize', 0)),
                            delta=self._safe_float(greeks.get('delta')),
                            gamma=self._safe_float(greeks.get('gamma')),
                            theta=self._safe_float(greeks.get('theta')),
                            vega=self._safe_float(greeks.get('vega')),
                            implied_volatility=self._safe_float(greeks.get('iv')),
                            data_source='tradier_realtime'
                        )
                        
                        # Calculer la moneyness
                        if underlying_price > 0:
                            hybrid_option.moneyness = underlying_price - strike
                        
                        all_options.append(hybrid_option)
                        
                except Exception as e:
                    print(f"⚠️ Error processing expiration {exp_date}: {e}")
                    continue
            
            print(f"✅ Retrieved {len(all_options)} options for {underlying}")
            return all_options
            
        except Exception as e:
            print(f"❌ Error fetching options chain for {underlying}: {e}")
            return []
    
    def enrich_with_historical_data(self, options: List[HybridOptionData]) -> List[HybridOptionData]:
        """Enrichit les options avec les données historiques Polygon.io"""
        
        if not self.polygon_api_key or not options:
            return options
        
        print(f"📈 Enriching {len(options)} options with Polygon.io historical data...")
        
        # Grouper par underlying pour optimiser les requêtes
        by_underlying = defaultdict(list)
        for option in options:
            by_underlying[option.underlying].append(option)
        
        for underlying, underlying_options in by_underlying.items():
            try:
                # Récupérer données historiques de l'underlying
                end_date = datetime.now()
                start_date = end_date - timedelta(days=30)
                
                historical_data = self._make_polygon_request(
                    f"/v2/aggs/ticker/{underlying}/range/1/day/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"
                )
                
                if not historical_data or not historical_data.get('results'):
                    continue
                
                # Calculer moyennes de volume
                volumes = [r['v'] for r in historical_data['results'] if r.get('v', 0) > 0]
                avg_volume = np.mean(volumes) if volumes else 0
                
                # Pour chaque option de cet underlying
                for option in underlying_options:
                    try:
                        # Enrichir avec données historiques si disponible
                        if avg_volume > 0:
                            option.historical_avg_volume = avg_volume
                            if option.volume > 0:
                                option.volume_ratio = option.volume / avg_volume
                                option.unusual_volume_score = min(100, option.volume_ratio * 25)
                    
                    except Exception as e:
                        print(f"⚠️ Error enriching option {option.option_symbol}: {e}")
                        continue
                        
            except Exception as e:
                print(f"⚠️ Error getting historical data for {underlying}: {e}")
                continue
        
        print("✅ Historical enrichment complete")
        return options
    
    def calculate_composite_scores(self, options: List[HybridOptionData]) -> List[HybridOptionData]:
        """Calcule les scores composites pour chaque option"""
        
        print(f"🧮 Calculating composite scores for {len(options)} options...")
        
        for option in options:
            score_components = []
            
            # 1. Score de volume inhabituel (0-40 points)
            if option.volume_ratio and option.volume_ratio > 1:
                volume_score = min(40, (option.volume_ratio - 1) * 20)
                score_components.append(volume_score)
            
            # 2. Score de spread bid-ask (0-20 points) - meilleur = plus serré
            if option.bid_ask_spread_pct > 0:
                # Inverser: spread plus serré = meilleur score
                spread_score = max(0, 20 - option.bid_ask_spread_pct)
                score_components.append(spread_score)
            
            # 3. Score de liquidité (0-20 points)
            if option.volume > 0 and option.open_interest > 0:
                liquidity_score = min(20, (option.volume + option.open_interest) / 1000 * 10)
                score_components.append(liquidity_score)
            
            # 4. Score de moneyness (0-20 points) - proche ATM = mieux
            if abs(option.moneyness) < 50:  # Dans les 50$ de ATM
                moneyness_score = 20 - (abs(option.moneyness) / 50) * 20
                score_components.append(moneyness_score)
            
            # Score composite final
            option.composite_score = sum(score_components)
        
        # Trier par score composite décroissant
        options.sort(key=lambda x: x.composite_score, reverse=True)
        
        print("✅ Composite scoring complete")
        return options
    
    def screen_unusual_activity(self,
                              tickers: List[str],
                              min_volume: int = 100,
                              min_open_interest: int = 100,
                              min_composite_score: float = 30.0,
                              max_days_to_expiration: int = 30) -> List[HybridOptionData]:
        """
        Screening principal d'activité inhabituelle
        
        Pipeline:
        1. Récupérer données temps réel Tradier
        2. Enrichir avec historique Polygon.io
        3. Calculer scores composites
        4. Filtrer selon critères
        """
        
        print(f"🎯 Screening unusual activity for {len(tickers)} tickers")
        print(f"   Min volume: {min_volume}, Min OI: {min_open_interest}")
        print(f"   Min score: {min_composite_score}, Max DTE: {max_days_to_expiration}")
        
        all_options = []
        
        for ticker in tickers:
            try:
                print(f"\n📊 Processing {ticker}...")
                
                # 1. Récupérer chaîne d'options temps réel
                options = self.get_options_chain_realtime(ticker)
                
                if not options:
                    print(f"   No options found for {ticker}")
                    continue
                
                # 2. Filtrer par DTE
                cutoff_date = datetime.now() + timedelta(days=max_days_to_expiration)
                options = [
                    opt for opt in options 
                    if datetime.strptime(opt.expiration, '%Y-%m-%d') <= cutoff_date
                ]
                
                # 3. Filtres de base
                options = [
                    opt for opt in options
                    if opt.volume >= min_volume 
                    and opt.open_interest >= min_open_interest
                    and opt.last_price > 0.05  # Éviter les options sans valeur
                ]
                
                print(f"   After basic filters: {len(options)} options")
                
                if not options:
                    continue
                
                # 4. Enrichir avec données historiques
                options = self.enrich_with_historical_data(options)
                
                # 5. Calculer scores composites
                options = self.calculate_composite_scores(options)
                
                # 6. Filtrer par score minimum
                filtered_options = [
                    opt for opt in options 
                    if opt.composite_score >= min_composite_score
                ]
                
                print(f"   Final results: {len(filtered_options)} options with score >= {min_composite_score}")
                
                # Afficher le top 3
                for i, opt in enumerate(filtered_options[:3], 1):
                    print(f"      {i}. {opt.option_symbol} ${opt.strike} {opt.option_type.upper()}")
                    print(f"         Score: {opt.composite_score:.1f}, Vol: {opt.volume}, OI: {opt.open_interest}")
                
                all_options.extend(filtered_options)
                
            except Exception as e:
                print(f"❌ Error processing {ticker}: {e}")
                continue
        
        # Trier tous les résultats par score
        all_options.sort(key=lambda x: x.composite_score, reverse=True)
        
        print("\n🎯 SCREENING COMPLETE")
        print(f"   Total unusual options found: {len(all_options)}")
        
        if all_options:
            print(f"   Top signal: {all_options[0].option_symbol} (Score: {all_options[0].composite_score:.1f})")
        
        return all_options
    
    def _safe_float(self, value) -> Optional[float]:
        """Convertit une valeur en float de manière sécurisée"""
        try:
            return float(value) if value is not None else None
        except (ValueError, TypeError):
            return None
    
    def export_results_to_dataframe(self, options: List[HybridOptionData]) -> pd.DataFrame:
        """Exporte les résultats vers un DataFrame pour analyse"""
        
        if not options:
            return pd.DataFrame()
        
        data = []
        for option in options:
            data.append({
                'symbol': option.option_symbol,
                'underlying': option.underlying,
                'type': option.option_type,
                'strike': option.strike,
                'expiration': option.expiration,
                'last_price': option.last_price,
                'bid': option.bid,
                'ask': option.ask,
                'volume': option.volume,
                'open_interest': option.open_interest,
                'delta': option.delta,
                'gamma': option.gamma,
                'theta': option.theta,
                'vega': option.vega,
                'implied_volatility': option.implied_volatility,
                'bid_ask_spread_pct': option.bid_ask_spread_pct,
                'volume_ratio': option.volume_ratio,
                'unusual_volume_score': option.unusual_volume_score,
                'composite_score': option.composite_score,
                'moneyness': option.moneyness,
                'timestamp': option.timestamp
            })
        
        df = pd.DataFrame(data)
        return df

# Factory function
def create_hybrid_manager(tradier_api_key: str, polygon_api_key: Optional[str] = None) -> HybridDataManager:
    """Factory pour créer le gestionnaire hybride"""
    return HybridDataManager(tradier_api_key, polygon_api_key)

# Test function
def test_hybrid_manager():
    """Test du gestionnaire hybride"""
    print("🧪 Testing Hybrid Data Manager...")
    
    # Nécessite des vraies clés API pour fonctionner
    tradier_key = "your_tradier_key_here"
    polygon_key = "your_polygon_key_here"  # Optionnel
    
    try:
        manager = create_hybrid_manager(tradier_key, polygon_key)
        
        # Test screening
        results = manager.screen_unusual_activity(
            tickers=['SPY', 'QQQ'],
            min_volume=50,
            min_open_interest=50,
            min_composite_score=20.0
        )
        
        print(f"Test results: {len(results)} unusual options found")
        
        # Export to DataFrame
        if results:
            df = manager.export_results_to_dataframe(results)
            print(f"DataFrame shape: {df.shape}")
            print(f"Top 3 scores: {df['composite_score'].head(3).tolist()}")
        
        print("✅ Hybrid manager test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_hybrid_manager()