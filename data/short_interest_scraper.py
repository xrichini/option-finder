#!/usr/bin/env python3
"""
Short Interest Scraper
Scraper modernisé pour HighShortInterest.com compatible avec l'architecture FastAPI
"""

import requests
from bs4 import BeautifulSoup
import yfinance as yf
from typing import List, Dict, Optional, Any
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ShortInterestStock:
    """Données d'un stock avec short interest élevé"""
    symbol: str
    company_name: str
    exchange: str
    short_interest_pct: float
    float_shares: Optional[float] = None
    outstanding_shares: Optional[float] = None
    industry: Optional[str] = None
    market_cap: Optional[int] = None
    avg_volume: Optional[int] = None
    price: Optional[float] = None
    sector: Optional[str] = None

@dataclass
class MarketFilterParams:
    """Paramètres de filtrage de marché"""
    min_market_cap: int = 100_000_000  # 100M
    min_avg_volume: int = 500_000      # 500K
    excluded_sectors: List[str] = None
    min_short_interest: float = 20.0   # 20%
    max_price: Optional[float] = None

class ShortInterestScraper:
    """Scraper pour HighShortInterest.com avec filtrage intelligent"""
    
    def __init__(self):
        self.base_url = "https://www.highshortinterest.com/"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/118.0.0.0 Safari/537.36"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def scrape_short_interest_stocks(self, exchange: str = "all") -> List[ShortInterestStock]:
        """
        Scrape les stocks avec short interest élevé depuis HighShortInterest.com
        
        Args:
            exchange: "all", "nasdaq", "nyse", ou "amex"
            
        Returns:
            Liste des stocks avec short interest élevé
        """
        try:
            logger.info(f"🔍 Scraping HighShortInterest.com pour {exchange}")
            
            # URL avec paramètre d'échange si spécifique
            url = self.base_url
            if exchange.lower() != "all":
                url += f"?exchange={exchange.lower()}"
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Chercher le tableau principal
            table = soup.find("table", {"class": "stocks"}) or soup.find("table")
            
            if not table:
                logger.error("❌ Aucun tableau trouvé sur HighShortInterest.com")
                return []
            
            stocks = []
            rows = table.find_all("tr")[1:]  # Skip header
            
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 4:  # Au minimum: Symbol, Company, Exchange, ShortInt
                    try:
                        stock = self._parse_table_row(cols)
                        if stock:
                            stocks.append(stock)
                    except Exception as e:
                        logger.debug(f"Erreur parsing ligne: {e}")
                        continue
            
            logger.info(f"✅ {len(stocks)} stocks avec short interest élevé trouvés")
            return stocks
            
        except requests.RequestException as e:
            logger.error(f"❌ Erreur réseau lors du scraping: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Erreur inattendue lors du scraping: {e}")
            return []

    def _parse_table_row(self, cols: List) -> Optional[ShortInterestStock]:
        """Parse une ligne du tableau HighShortInterest"""
        try:
            # Structure typique: Ticker, Company, Exchange, ShortInt%, Float, Outstanding, Industry
            symbol = cols[0].get_text(strip=True)
            company_name = cols[1].get_text(strip=True) if len(cols) > 1 else ""
            exchange = cols[2].get_text(strip=True) if len(cols) > 2 else ""
            
            # Parse le short interest (format: "XX.XX%")
            short_int_text = cols[3].get_text(strip=True) if len(cols) > 3 else "0%"
            short_interest_pct = float(short_int_text.replace("%", ""))
            
            # Parse les autres champs optionnels
            float_shares = self._parse_share_count(cols[4]) if len(cols) > 4 else None
            outstanding_shares = self._parse_share_count(cols[5]) if len(cols) > 5 else None
            industry = cols[6].get_text(strip=True) if len(cols) > 6 else None
            
            # Valider le symbole
            if not symbol or not symbol.isalpha() or len(symbol) > 5:
                return None
            
            return ShortInterestStock(
                symbol=symbol.upper(),
                company_name=company_name,
                exchange=exchange.upper(),
                short_interest_pct=short_interest_pct,
                float_shares=float_shares,
                outstanding_shares=outstanding_shares,
                industry=industry
            )
            
        except (ValueError, IndexError, AttributeError) as e:
            logger.debug(f"Erreur parsing ligne: {e}")
            return None

    def _parse_share_count(self, cell) -> Optional[float]:
        """Parse le nombre d'actions (format: "123.45M" ou "1.23B")"""
        try:
            text = cell.get_text(strip=True)
            if not text or text == "N/A":
                return None
            
            # Retirer les caractères non-numériques sauf . et lettres finales
            multiplier = 1
            if text.endswith("K"):
                multiplier = 1_000
                text = text[:-1]
            elif text.endswith("M"):
                multiplier = 1_000_000
                text = text[:-1]
            elif text.endswith("B"):
                multiplier = 1_000_000_000
                text = text[:-1]
            
            return float(text) * multiplier
            
        except (ValueError, AttributeError):
            return None

    def enrich_with_market_data(self, stocks: List[ShortInterestStock]) -> List[ShortInterestStock]:
        """Enrichit les stocks avec des données de marché via yfinance"""
        if not stocks:
            return stocks
        
        logger.info(f"📊 Enrichissement de {len(stocks)} stocks avec données de marché")
        
        # Traitement par batch pour optimiser les appels yfinance
        enriched_stocks = []
        batch_size = 50
        
        for i in range(0, len(stocks), batch_size):
            batch = stocks[i:i + batch_size]
            symbols = [stock.symbol for stock in batch]
            
            try:
                # Récupération en batch
                tickers = yf.Tickers(' '.join(symbols))
                
                for stock in batch:
                    try:
                        ticker = tickers.tickers[stock.symbol]
                        info = ticker.info
                        hist = ticker.history(period='5d')
                        
                        if info and not hist.empty:
                            # Enrichir avec les données de marché
                            stock.market_cap = info.get('marketCap', 0)
                            stock.avg_volume = info.get('averageVolume', 0)
                            stock.price = info.get('currentPrice') or (hist['Close'].iloc[-1] if len(hist) > 0 else 0)
                            stock.sector = info.get('sector', 'Unknown')
                        
                    except Exception as e:
                        logger.debug(f"Erreur enrichissement {stock.symbol}: {e}")
                    
                    enriched_stocks.append(stock)
                    
            except Exception as e:
                logger.warning(f"Erreur enrichissement batch: {e}")
                # Ajouter les stocks sans enrichissement
                enriched_stocks.extend(batch)
        
        logger.info(f"✅ Enrichissement terminé pour {len(enriched_stocks)} stocks")
        return enriched_stocks

    def filter_stocks_by_criteria(self, stocks: List[ShortInterestStock], 
                                 params: MarketFilterParams) -> List[ShortInterestStock]:
        """Filtre les stocks selon les critères de marché"""
        if not stocks:
            return stocks
        
        logger.info(f"🔍 Filtrage de {len(stocks)} stocks par critères de marché")
        
        filtered = []
        excluded_sectors = params.excluded_sectors or ['Real Estate Investment Trusts']
        
        for stock in stocks:
            # Filtre par short interest
            if stock.short_interest_pct < params.min_short_interest:
                continue
            
            # Filtre par market cap (si disponible)
            if stock.market_cap and stock.market_cap < params.min_market_cap:
                continue
            
            # Filtre par volume (si disponible)
            if stock.avg_volume and stock.avg_volume < params.min_avg_volume:
                continue
            
            # Filtre par secteur (si disponible)
            if stock.sector and stock.sector in excluded_sectors:
                continue
            
            # Filtre par prix (si spécifié)
            if params.max_price and stock.price and stock.price > params.max_price:
                continue
            
            filtered.append(stock)
        
        logger.info(f"✅ {len(filtered)} stocks après filtrage ({len(stocks) - len(filtered)} exclus)")
        return filtered

    async def check_optionable_symbols(self, symbols: List[str]) -> List[str]:
        """Vérifie quels symboles ont des options disponibles (version simplifiée)"""
        # Pour l'instant, retourne tous les symboles
        # TODO: Intégrer avec EnhancedTradierClient pour vérifier les options
        logger.info(f"📋 Vérification des options pour {len(symbols)} symboles")
        
        # Simulation - dans la vraie version, on utiliserait TradierClient
        optionable = [s for s in symbols if len(s) <= 4]  # Heuristique simple
        
        logger.info(f"✅ {len(optionable)} symboles avec options probables")
        return optionable
    
    async def get_high_short_interest_data(
        self, 
        exchange: str = "all",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Méthode principale pour récupérer les données de short interest.
        Compatible avec les endpoints FastAPI et la fonction legacy.
        
        Args:
            exchange: Exchange à scraper ('all', 'nasdaq', 'nyse')
            limit: Limite du nombre de résultats
            
        Returns:
            Liste de dictionnaires avec les données des stocks
        """
        try:
            # Scraping initial
            stocks = self.scrape_short_interest_stocks(exchange=exchange)
            
            if not stocks:
                return []
            
            # Limiter le nombre de stocks
            if limit and limit > 0:
                stocks = stocks[:limit]
            
            # Enrichissement avec données de marché
            enriched_stocks = self.enrich_with_market_data(stocks)
            
            # Conversion en dictionnaires pour compatibilité
            result = []
            for stock in enriched_stocks:
                stock_dict = {
                    'symbol': stock.symbol,
                    'company_name': stock.company_name,
                    'exchange': stock.exchange,
                    'short_interest_percent': stock.short_interest_pct,
                    'market_cap': stock.market_cap,
                    'sector': stock.sector,
                    'price': stock.price,
                    'volume': stock.avg_volume,
                    'float': stock.float_shares,
                    'outstanding_shares': stock.outstanding_shares,
                    'industry': stock.industry
                }
                
                # Calculer days to cover si possible
                if stock.avg_volume and stock.float_shares and stock.avg_volume > 0:
                    short_shares = (stock.float_shares * stock.short_interest_pct) / 100
                    stock_dict['days_to_cover'] = short_shares / stock.avg_volume
                else:
                    stock_dict['days_to_cover'] = None
                    
                result.append(stock_dict)
            
            logger.info(f"✅ Données short interest récupérées: {len(result)} stocks")
            return result
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la récupération des données: {e}")
            return []
    
    def filter_stocks(
        self,
        stocks: List[Dict[str, Any]],
        min_market_cap: float = None,
        max_market_cap: float = None,
        min_short_interest: float = None,
        sectors: List[str] = None,
        min_volume: int = None
    ) -> List[Dict[str, Any]]:
        """
        Filtre une liste de stocks selon des critères.
        Compatible avec les dictionnaires retournés par get_high_short_interest_data.
        
        Args:
            stocks: Liste des stocks à filtrer
            min_market_cap: Capitalisation minimum
            max_market_cap: Capitalisation maximum
            min_short_interest: % de short interest minimum
            sectors: Liste des secteurs autorisés
            min_volume: Volume minimum
            
        Returns:
            Liste filtrée des stocks
        """
        if not stocks:
            return stocks
        
        logger.info(f"🔍 Filtrage de {len(stocks)} stocks par critères")
        
        filtered = []
        for stock in stocks:
            # Filtre par short interest
            if min_short_interest and stock.get('short_interest_percent', 0) < min_short_interest:
                continue
            
            # Filtre par market cap
            market_cap = stock.get('market_cap', 0) or 0
            if min_market_cap and market_cap < min_market_cap:
                continue
            if max_market_cap and market_cap > max_market_cap:
                continue
            
            # Filtre par secteur
            if sectors and stock.get('sector'):
                if stock['sector'] not in sectors:
                    continue
            
            # Filtre par volume
            if min_volume and (stock.get('volume', 0) or 0) < min_volume:
                continue
            
            filtered.append(stock)
        
        logger.info(f"✅ Filtrage terminé: {len(filtered)} stocks correspondent aux critères")
        return filtered

# Fonctions utilitaires pour compatibilité avec l'ancien système
def get_high_short_interest_symbols(
    enable_prefiltering: bool = True,
    min_market_cap: int = 100_000_000,
    min_avg_volume: int = 500_000,
    exchange: str = "all"
) -> List[str]:
    """
    Fonction compatible avec l'ancien système Streamlit
    Retourne une liste de symboles avec short interest élevé
    """
    scraper = ShortInterestScraper()
    
    # Scraping initial
    stocks = scraper.scrape_short_interest_stocks(exchange=exchange)
    
    if not stocks:
        return []
    
    # Enrichissement avec données de marché
    if enable_prefiltering:
        stocks = scraper.enrich_with_market_data(stocks)
        
        # Filtrage
        filter_params = MarketFilterParams(
            min_market_cap=min_market_cap,
            min_avg_volume=min_avg_volume
        )
        stocks = scraper.filter_stocks_by_criteria(stocks, filter_params)
    
    # Retourner seulement les symboles
    return [stock.symbol for stock in stocks]


def get_high_short_interest_symbols_legacy(
    min_short_interest: float = 5.0,
    max_results: int = 100,
    exchange: str = "all"
) -> List[str]:
    """
    Fonction de compatibilité pour récupérer les symboles avec short interest élevé.
    Compatible avec l'ancien code Streamlit.
    
    Args:
        min_short_interest: Pourcentage minimum de short interest
        max_results: Nombre maximum de résultats
        exchange: Exchange à scraper ('nasdaq', 'nyse', 'all')
        
    Returns:
        List[str]: Liste des symboles
    """
    try:
        scraper = ShortInterestScraper()
        
        # Utilisation synchrone (compatible avec ancien code)
        import asyncio
        
        # Récupérer les données
        stocks = asyncio.run(scraper.get_high_short_interest_data(
            exchange=exchange,
            limit=max_results
        ))
        
        # Filtrer par short interest minimum
        filtered_stocks = [
            stock for stock in stocks 
            if stock.get('short_interest_percent', 0) >= min_short_interest
        ]
        
        # Retourner seulement les symboles
        symbols = [stock['symbol'] for stock in filtered_stocks[:max_results]]
        
        logger.info(f"🔗 Fonction legacy: {len(symbols)} symboles retournés (SI >= {min_short_interest}%)")
        return symbols
        
    except Exception as e:
        logger.error(f"❌ Erreur fonction legacy: {e}")
        return []


# Exemple d'utilisation et test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    scraper = ShortInterestScraper()
    
    # Test du scraping
    stocks = scraper.scrape_short_interest_stocks()
    print(f"📊 {len(stocks)} stocks trouvés")
    
    if stocks:
        # Enrichissement
        enriched = scraper.enrich_with_market_data(stocks[:5])  # Test sur 5 stocks
        
        # Affichage des résultats
        for stock in enriched:
            print(f"🎯 {stock.symbol}: {stock.short_interest_pct}% short interest, "
                  f"Market cap: ${stock.market_cap:,}" if stock.market_cap else "N/A")