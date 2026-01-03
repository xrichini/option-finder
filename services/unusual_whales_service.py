#!/usr/bin/env python3
"""
Service Unusual Whales - Intégration de la méthodologie Unusual Whales
Basé sur la version Streamlit avec analyse historique
"""

from typing import List, Dict, Any, Tuple
import logging
from data.historical_data_manager import HistoricalDataManager
from models.api_models import OptionsOpportunity

logger = logging.getLogger(__name__)

class UnusualWhalesService:
    """Service implémentant la méthodologie Unusual Whales"""
    
    def __init__(self, enable_historical: bool = True):
        self.historical_manager = HistoricalDataManager() if enable_historical else None
        self.enable_historical = enable_historical
        
    def calculate_vol_oi_score(self, volume: int, open_interest: int) -> float:
        """Calculate Volume/Open Interest score based on Unusual Whales methodology"""
        if open_interest == 0:
            return 95.0  # Brand new contracts, very high score
        
        ratio = volume / open_interest
        
        # Scoring based on Unusual Whales examples
        if ratio >= 10.0:  # Like NVDA example (11.55 ratio)
            return 95.0
        elif ratio >= 5.0:
            return 85.0
        elif ratio >= 2.0:
            return 75.0
        elif ratio >= 1.0:  # Volume > OI threshold
            return 65.0
        else:
            return max(10.0, ratio * 50)  # Proportional score
    
    def calculate_large_block_score(self, volume: int, whale_threshold: int = 5000) -> float:
        """Detect large institutional blocks based on Unusual Whales methodology"""
        if volume >= 10000:  # Like MSFT examples
            return 95.0
        elif volume >= whale_threshold:
            # Progressive scoring for large blocks
            return min(95.0, 80.0 + (volume - whale_threshold) / 1000 * 3)
        else:
            return max(0, (volume / whale_threshold) * 50)
    
    def calculate_whale_score(
        self,
        volume_1d: int,
        open_interest: int,
        delta: float = 0.5,  # Default pour options ATM
        iv: float = 0.3      # Default IV
    ) -> float:
        """Enhanced whale score using Unusual Whales methodology"""
        # Calculate individual component scores
        vol_oi_score = self.calculate_vol_oi_score(volume_1d, open_interest)
        block_score = self.calculate_large_block_score(volume_1d)
        
        # Legacy scoring components (preserved for continuity)
        legacy_score = 0
        
        # Volume 1 jour score (0-25 points)
        if volume_1d > 5000:
            legacy_score += 25
        elif volume_1d > 2000:
            legacy_score += 20
        elif volume_1d > 1000:
            legacy_score += 15
        elif volume_1d > 500:
            legacy_score += 10
        
        # Delta score pour calls ITM/ATM (0-15 points)
        if delta > 0.4:
            legacy_score += 15
        elif delta > 0.3:
            legacy_score += 10
        elif delta > 0.2:
            legacy_score += 5
        
        # Implied Volatility score (0-10 points)
        if iv > 0.8:
            legacy_score += 10
        elif iv > 0.5:
            legacy_score += 7
        elif iv > 0.3:
            legacy_score += 5
        
        # Composite score with Unusual Whales weighting
        composite_score = (
            legacy_score * 0.4 +      # Legacy logic (40%)
            vol_oi_score * 0.35 +     # Vol/OI ratio (35%) - very important per UW
            block_score * 0.25        # Large blocks (25%) - institutional detection
        )
        
        return min(100.0, composite_score)
    
    def calculate_whale_score_v3(
        self,
        volume_1d: int,
        open_interest: int,
        option_symbol: str,
        delta: float = 0.5,
        iv: float = 0.3
    ) -> Tuple[float, Dict[str, Any]]:
        """Enhanced whale score v3 with historical anomaly detection"""
        # Get base scores from v2
        base_score = self.calculate_whale_score(
            volume_1d, open_interest, delta, iv
        )
        
        # Historical anomaly scores
        volume_anomaly = 0.0
        oi_anomaly = 0.0
        historical_stats = {}
        
        if self.historical_manager:
            try:
                # Calculate volume anomaly vs historical average
                volume_anomaly, vol_stats = self.historical_manager.calculate_volume_anomaly(
                    current_volume=volume_1d,
                    option_symbol=option_symbol,
                    lookback_days=10
                )
                
                # Calculate OI anomaly vs historical average  
                oi_anomaly, oi_stats = self.historical_manager.calculate_oi_anomaly(
                    current_oi=open_interest,
                    option_symbol=option_symbol,
                    lookback_days=10
                )
                
                historical_stats = {
                    "volume_stats": vol_stats,
                    "oi_stats": oi_stats
                }
                
            except Exception as e:
                logger.error(f"Historical analysis error for {option_symbol}: {e}")
        
        # Composite score v3 with historical weighting
        if volume_anomaly > 0 or oi_anomaly > 0:
            # Historical data available - use enhanced scoring
            enhanced_score = (
                base_score * 0.50 +         # Base UW logic (50%)
                volume_anomaly * 0.35 +     # Volume vs history (35%)
                oi_anomaly * 0.15           # OI vs history (15%)
            )
        else:
            # No historical data - fallback to base score
            enhanced_score = base_score
        
        scoring_details = {
            "base_score": base_score,
            "volume_anomaly": volume_anomaly,
            "oi_anomaly": oi_anomaly,
            "enhanced_score": enhanced_score,
            "has_historical_data": (volume_anomaly > 0 or oi_anomaly > 0),
            "historical_stats": historical_stats
        }
        
        return min(100.0, enhanced_score), scoring_details
    
    def get_vol_oi_ratio(self, volume: int, open_interest: int) -> float:
        """Calculate Volume/Open Interest ratio"""
        return volume / open_interest if open_interest > 0 else float('inf')
    
    def categorize_block_size(self, volume: int) -> str:
        """Categorize option volume into block sizes"""
        if volume >= 10000:
            return "🐋 Whale"
        elif volume >= 5000:
            return "🦑 Large"
        elif volume >= 2000:
            return "🐟 Medium"
        else:
            return "🦐 Small"
    
    def is_unusual_activity(self, vol_oi_ratio: float, volume: int) -> bool:
        """Determine if activity is unusual based on UW criteria"""
        return vol_oi_ratio >= 1.0 or volume >= 5000
    
    def analyze_opportunity(self, opp: OptionsOpportunity) -> Dict[str, Any]:
        """
        Analyse complète d'une opportunité avec méthodologie Unusual Whales
        
        Args:
            opp: Opportunité à analyser
            
        Returns:
            Dictionnaire avec analyse complète UW
        """
        
        try:
            # Calcul du score Whale v3 avec historique
            whale_score_v3, scoring_details = self.calculate_whale_score_v3(
                volume_1d=opp.volume,
                open_interest=opp.open_interest,
                option_symbol=opp.option_symbol
            )
            
            # Ratio Volume/OI
            vol_oi_ratio = self.get_vol_oi_ratio(opp.volume, opp.open_interest)
            
            # Catégorisation des blocs
            block_category = self.categorize_block_size(opp.volume)
            
            # Détection d'activité inhabituelle
            unusual_activity = self.is_unusual_activity(vol_oi_ratio, opp.volume)
            
            # Indicateur de nouvelle position
            new_position = opp.open_interest == 0 or vol_oi_ratio >= 1.0
            
            analysis = {
                "whale_score_v3": whale_score_v3,
                "vol_oi_ratio": vol_oi_ratio,
                "block_category": block_category,
                "unusual_activity": unusual_activity,
                "new_position": new_position,
                "scoring_details": scoring_details,
                
                # Métriques supplémentaires
                "volume_anomaly_level": self._get_anomaly_level(scoring_details.get("volume_anomaly", 0)),
                "oi_anomaly_level": self._get_anomaly_level(scoring_details.get("oi_anomaly", 0)),
                "institutional_signal": opp.volume >= 10000,
                "fresh_contract": opp.open_interest == 0,
                
                # Flags pour affichage
                "show_infinity": opp.open_interest == 0,
                "hot_volume": scoring_details.get("volume_anomaly", 0) >= 70,  # 300%+ above average
                "anomaly_badge": "🚨" if scoring_details.get("volume_anomaly", 0) >= 85 else None
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Erreur analyse UW pour {opp.option_symbol}: {e}")
            return {
                "whale_score_v3": opp.whale_score,  # Fallback
                "vol_oi_ratio": self.get_vol_oi_ratio(opp.volume, opp.open_interest),
                "block_category": self.categorize_block_size(opp.volume),
                "unusual_activity": False,
                "new_position": False,
                "error": str(e)
            }
    
    def _get_anomaly_level(self, anomaly_score: float) -> str:
        """Détermine le niveau d'anomalie"""
        if anomaly_score >= 85:
            return "🚨 Extrême"
        elif anomaly_score >= 70:
            return "🔥 Élevé"
        elif anomaly_score >= 50:
            return "⚡ Modéré"
        elif anomaly_score > 0:
            return "📈 Faible"
        else:
            return "Normal"
    
    def save_scan_results(self, opportunities: List[OptionsOpportunity]) -> int:
        """
        Sauvegarde les résultats de scan pour l'historique
        
        Args:
            opportunities: Liste des opportunités détectées
            
        Returns:
            Nombre d'enregistrements sauvegardés
        """
        
        if not self.historical_manager:
            logger.warning("Gestionnaire historique non disponible")
            return 0
        
        try:
            # Convertir les OptionsOpportunity en format compatible
            scan_results = []
            for opp in opportunities:
                # Créer un objet compatible avec le format attendu par historical_data_manager
                result_obj = type('OptionScreenerResult', (), {
                    'option_symbol': opp.option_symbol,
                    'symbol': opp.underlying_symbol,
                    'volume_1d': opp.volume,
                    'open_interest': opp.open_interest,
                    'last_price': opp.last,
                    'whale_score': opp.whale_score,
                    'vol_oi_ratio': self.get_vol_oi_ratio(opp.volume, opp.open_interest)
                })
                scan_results.append(result_obj)
            
            saved_count = self.historical_manager.save_scan_results(scan_results)
            logger.info(f"💾 Sauvegardé {saved_count} résultats dans l'historique")
            
            return saved_count
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde historique: {e}")
            return 0
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Récupère les statistiques de la base historique"""
        if not self.historical_manager:
            return {"error": "Gestionnaire historique non disponible"}
        
        try:
            return self.historical_manager.get_database_stats()
        except Exception as e:
            logger.error(f"Erreur récupération stats DB: {e}")
            return {"error": str(e)}