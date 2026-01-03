# market_chameleon_scraper.py - Scraper pour Market Chameleon Unusual Option Volume
import requests
from bs4 import BeautifulSoup
from typing import List
from dataclasses import dataclass
from datetime import datetime
import re

@dataclass
class UnusualOptionVolumeData:
    """Structure des données Market Chameleon"""
    symbol: str
    option_symbol: str
    option_type: str  # 'call' or 'put'
    strike: float
    expiration: str
    volume: int
    avg_volume: int
    volume_ratio: float  # volume / avg_volume
    open_interest: int
    last_price: float
    bid: float
    ask: float
    implied_volatility: float
    delta: float
    dte: int
    underlying_price: float
    timestamp: datetime

class MarketChameleonScraper:
    """Scraper pour récupérer les données d'options inhabituelles de Market Chameleon"""
    
    def __init__(self):
        self.base_url = "https://marketchameleon.com/Reports/UnusualOptionVolumeReport"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def scrape_unusual_volume_data(self, limit: int = 100) -> List[UnusualOptionVolumeData]:
        """
        Scrape les données de volumes inhabituels depuis Market Chameleon
        
        Args:
            limit: Nombre maximum d'enregistrements à récupérer
            
        Returns:
            Liste des données d'options avec volumes inhabituels
        """
        try:
            print("🔍 Scraping Market Chameleon unusual option volume data...")
            
            # Faire la requête principale
            response = self.session.get(self.base_url, timeout=30)
            response.raise_for_status()
            
            # Parser le HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Trouver le tableau de données (ajuster selon la structure réelle)
            # Note: Cette partie devra être adaptée selon la structure HTML réelle
            data_table = soup.find('table', {'class': 'table-hover'}) or soup.find('table')
            
            if not data_table:
                print("❌ Impossible de trouver le tableau de données")
                return []
            
            # Parser les données du tableau
            results = []
            rows = data_table.find_all('tr')[1:]  # Skip header row
            
            for i, row in enumerate(rows[:limit]):
                try:
                    cols = row.find_all('td')
                    if len(cols) < 10:  # Minimum expected columns
                        continue
                    
                    # Extraire les données (indices à ajuster selon la structure réelle)
                    symbol = self._clean_text(cols[0])
                    option_symbol = self._clean_text(cols[1]) if len(cols) > 1 else ""
                    
                    # Parser le type d'option depuis le symbole
                    option_type = self._parse_option_type(option_symbol)
                    strike = self._parse_float(cols[2]) if len(cols) > 2 else 0.0
                    expiration = self._clean_text(cols[3]) if len(cols) > 3 else ""
                    
                    volume = self._parse_int(cols[4]) if len(cols) > 4 else 0
                    avg_volume = self._parse_int(cols[5]) if len(cols) > 5 else 0
                    volume_ratio = self._parse_float(cols[6]) if len(cols) > 6 else 0.0
                    
                    open_interest = self._parse_int(cols[7]) if len(cols) > 7 else 0
                    last_price = self._parse_float(cols[8]) if len(cols) > 8 else 0.0
                    
                    # Calculer DTE depuis l'expiration
                    dte = self._calculate_dte(expiration)
                    
                    result = UnusualOptionVolumeData(
                        symbol=symbol,
                        option_symbol=option_symbol,
                        option_type=option_type,
                        strike=strike,
                        expiration=expiration,
                        volume=volume,
                        avg_volume=avg_volume,
                        volume_ratio=volume_ratio,
                        open_interest=open_interest,
                        last_price=last_price,
                        bid=0.0,  # Pas toujours disponible
                        ask=0.0,  # Pas toujours disponible
                        implied_volatility=0.0,  # À récupérer séparément si nécessaire
                        delta=0.0,  # À récupérer séparément si nécessaire
                        dte=dte,
                        underlying_price=0.0,  # À récupérer séparément si nécessaire
                        timestamp=datetime.now()
                    )
                    
                    results.append(result)
                    
                except Exception as e:
                    print(f"⚠️ Erreur parsing ligne {i}: {e}")
                    continue
            
            print(f"✅ {len(results)} enregistrements récupérés de Market Chameleon")
            return results
            
        except Exception as e:
            print(f"❌ Erreur scraping Market Chameleon: {e}")
            return []
    
    def get_unusual_options_for_symbols(self, symbols: List[str], min_volume_ratio: float = 2.0) -> List[UnusualOptionVolumeData]:
        """
        Récupère les options inhabituelles pour des symboles spécifiques
        
        Args:
            symbols: Liste des symboles à filtrer
            min_volume_ratio: Ratio volume/moyenne minimum
            
        Returns:
            Données filtrées pour les symboles demandés
        """
        all_data = self.scrape_unusual_volume_data()
        
        filtered_data = [
            data for data in all_data
            if data.symbol.upper() in [s.upper() for s in symbols]
            and data.volume_ratio >= min_volume_ratio
            and data.volume > 0
        ]
        
        # Trier par ratio de volume décroissant
        filtered_data.sort(key=lambda x: x.volume_ratio, reverse=True)
        
        return filtered_data
    
    def _clean_text(self, element) -> str:
        """Nettoie le texte extrait"""
        if element is None:
            return ""
        return element.get_text().strip()
    
    def _parse_float(self, element) -> float:
        """Parse un élément en float"""
        try:
            text = self._clean_text(element)
            # Enlever les caractères non-numériques sauf . et -
            cleaned = re.sub(r'[^\d.-]', '', text)
            return float(cleaned) if cleaned else 0.0
        except:
            return 0.0
    
    def _parse_int(self, element) -> int:
        """Parse un élément en int"""
        try:
            text = self._clean_text(element)
            # Enlever les caractères non-numériques sauf -
            cleaned = re.sub(r'[^\d-]', '', text)
            return int(cleaned) if cleaned else 0
        except:
            return 0
    
    def _parse_option_type(self, option_symbol: str) -> str:
        """Détermine le type d'option depuis le symbole"""
        if not option_symbol:
            return "unknown"
        
        # Les symboles d'options suivent généralement le format OCC
        # Ex: AAPL250117C00150000 (Call) ou AAPL250117P00150000 (Put)
        if 'C' in option_symbol.upper():
            return "call"
        elif 'P' in option_symbol.upper():
            return "put"
        else:
            return "unknown"
    
    def _calculate_dte(self, expiration_str: str) -> int:
        """Calcule les jours jusqu'à expiration"""
        try:
            # Essayer différents formats de date
            formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y%m%d']
            
            for fmt in formats:
                try:
                    exp_date = datetime.strptime(expiration_str, fmt).date()
                    dte = (exp_date - datetime.now().date()).days
                    return max(0, dte)
                except:
                    continue
            
            return 0
        except:
            return 0

class MarketChameleonEnhancer:
    """Intègre les données Market Chameleon dans notre screener existant"""
    
    def __init__(self):
        self.scraper = MarketChameleonScraper()
    
    def enhance_screening_results(self, our_results: List, use_mc_data: bool = True) -> List:
        """
        Améliore nos résultats avec les données Market Chameleon
        
        Args:
            our_results: Résultats de notre screener
            use_mc_data: Utiliser les données Market Chameleon pour validation
            
        Returns:
            Résultats enrichis avec données Market Chameleon
        """
        if not use_mc_data or not our_results:
            return our_results
        
        try:
            # Extraire les symboles uniques de nos résultats
            our_symbols = list(set(result.symbol for result in our_results))
            
            # Récupérer les données Market Chameleon pour ces symboles
            mc_data = self.scraper.get_unusual_options_for_symbols(our_symbols, min_volume_ratio=1.5)
            
            if not mc_data:
                print("⚠️ Aucune donnée Market Chameleon récupérée")
                return our_results
            
            # Créer un mapping pour comparaison rapide
            mc_lookup = {}
            for mc_item in mc_data:
                key = f"{mc_item.symbol}_{mc_item.option_type}_{mc_item.strike}_{mc_item.expiration}"
                mc_lookup[key] = mc_item
            
            # Enrichir nos résultats
            enhanced_results = []
            for result in our_results:
                # Créer la clé de recherche
                result_key = f"{result.symbol}_{result.side}_{result.strike}_{result.expiration}"
                
                # Chercher la correspondance dans Market Chameleon
                mc_match = mc_lookup.get(result_key)
                
                if mc_match:
                    # Ajouter des propriétés Market Chameleon à notre résultat
                    result.mc_volume_ratio = mc_match.volume_ratio
                    result.mc_avg_volume = mc_match.avg_volume
                    result.mc_confirmed = True
                    result.whale_score += 10  # Bonus pour confirmation Market Chameleon
                    
                    print(f"✅ {result.symbol} confirmé par Market Chameleon (ratio: {mc_match.volume_ratio:.1f})")
                else:
                    result.mc_confirmed = False
                    result.mc_volume_ratio = 0.0
                    result.mc_avg_volume = 0
                
                enhanced_results.append(result)
            
            # Ajouter les options Market Chameleon que nous avons ratées
            mc_only_results = []
            for mc_item in mc_data:
                # Vérifier si cette option est déjà dans nos résultats
                found = any(
                    r.symbol == mc_item.symbol and 
                    r.side == mc_item.option_type and
                    abs(r.strike - mc_item.strike) < 0.01
                    for r in our_results
                )
                
                if not found and mc_item.volume_ratio >= 3.0:  # Seuil élevé pour les nouvelles détections
                    # Créer un résultat basé sur Market Chameleon
                    from models.option_model import OptionScreenerResult
                    
                    mc_result = OptionScreenerResult(
                        symbol=mc_item.symbol,
                        option_symbol=mc_item.option_symbol,
                        expiration=mc_item.expiration,
                        strike=mc_item.strike,
                        side=mc_item.option_type,
                        delta=mc_item.delta,
                        volume_1d=mc_item.volume,
                        volume_7d=mc_item.volume * 7,  # Estimation
                        open_interest=mc_item.open_interest,
                        last_price=mc_item.last_price,
                        bid=mc_item.bid,
                        ask=mc_item.ask,
                        implied_volatility=mc_item.implied_volatility,
                        whale_score=min(95, 50 + mc_item.volume_ratio * 10),  # Score basé sur ratio MC
                        dte=mc_item.dte
                    )
                    
                    # Marquer comme provenant de Market Chameleon
                    mc_result.mc_confirmed = True
                    mc_result.mc_volume_ratio = mc_item.volume_ratio
                    mc_result.mc_avg_volume = mc_item.avg_volume
                    mc_result.mc_source = True
                    
                    mc_only_results.append(mc_result)
                    
                    print(f"🆕 Nouvelle détection Market Chameleon: {mc_item.symbol} (ratio: {mc_item.volume_ratio:.1f})")
            
            # Combiner tous les résultats et trier
            all_results = enhanced_results + mc_only_results
            all_results.sort(key=lambda x: x.whale_score, reverse=True)
            
            print(f"📊 Résultats enrichis: {len(enhanced_results)} existants + {len(mc_only_results)} nouveaux MC")
            
            return all_results
            
        except Exception as e:
            print(f"❌ Erreur enrichissement Market Chameleon: {e}")
            return our_results

# Fonction utilitaire pour tester le scraper
def test_market_chameleon_scraper():
    """Test du scraper Market Chameleon"""
    scraper = MarketChameleonScraper()
    
    print("🧪 Test du scraper Market Chameleon...")
    
    # Test avec quelques symboles liquides
    test_symbols = ['SPY', 'QQQ', 'TSLA', 'NVDA', 'AAPL']
    
    try:
        results = scraper.get_unusual_options_for_symbols(test_symbols, min_volume_ratio=1.5)
        
        if results:
            print(f"✅ {len(results)} options inhabituelles trouvées:")
            
            for i, result in enumerate(results[:5], 1):
                print(f"  {i}. {result.symbol} {result.option_type.upper()} ${result.strike} "
                      f"Vol: {result.volume:,} (Ratio: {result.volume_ratio:.1f}x)")
        else:
            print("⚠️ Aucun résultat trouvé (site peut nécessiter authentification)")
            
    except Exception as e:
        print(f"❌ Erreur test: {e}")

if __name__ == "__main__":
    test_market_chameleon_scraper()