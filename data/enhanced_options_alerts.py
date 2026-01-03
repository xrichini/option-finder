#!/usr/bin/env python3
"""
Enhanced Options Alerts System
Système d'alertes avancé pour les options avec recommandations automatiques
Intégré avec l'architecture hybride Tradier/Polygon.io
"""

from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import logging
import numpy as np
from enum import Enum

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlertType(Enum):
    """Types d'alertes d'options"""
    UNUSUAL_CALL_VOLUME = "UNUSUAL_CALL_VOLUME"
    UNUSUAL_PUT_VOLUME = "UNUSUAL_PUT_VOLUME" 
    SIGNIFICANT_PRICE_MOVEMENT = "SIGNIFICANT_PRICE_MOVEMENT"
    HIGH_OI_ACTIVITY = "HIGH_OI_ACTIVITY"
    VOLUME_PRICE_DIVERGENCE = "VOLUME_PRICE_DIVERGENCE"
    GAMMA_SQUEEZE_POTENTIAL = "GAMMA_SQUEEZE_POTENTIAL"
    DARK_POOL_ACTIVITY = "DARK_POOL_ACTIVITY"
    EARNINGS_PLAY = "EARNINGS_PLAY"
    ANOMALY_DETECTED = "ANOMALY_DETECTED"

class TradingAction(Enum):
    """Actions de trading recommandées"""
    BUY_CALL = "BUY_CALL"
    BUY_PUT = "BUY_PUT"
    SELL_CALL = "SELL_CALL"
    SELL_PUT = "SELL_PUT"
    STRADDLE = "STRADDLE"
    STRANGLE = "STRANGLE"
    IRON_CONDOR = "IRON_CONDOR"
    MONITOR = "MONITOR"
    AVOID = "AVOID"

class RiskLevel(Enum):
    """Niveaux de risque"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EXTREME = "EXTREME"

@dataclass
class OptionsAlert:
    """Structure avancée pour les alertes d'activité anormale sur options"""
    ticker: str
    contract: str
    alert_type: AlertType
    severity: float  # 0-1
    confidence: float  # 0-1
    volume: int
    avg_volume: float
    open_interest: int
    price_change: float
    unusual_volume_ratio: float
    timestamp: datetime
    description: str
    data_source: str  # 'tradier', 'polygon', 'hybrid'
    
    # Données financières étendues
    bid: float = 0.0
    ask: float = 0.0
    last_price: float = 0.0
    strike: float = 0.0
    expiration: str = ""
    option_type: str = ""  # 'call' ou 'put'
    
    # Greeks et volatilité
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    implied_volatility: Optional[float] = None
    
    # Métriques d'anomalie
    z_score: Optional[float] = None
    percentile_rank: Optional[float] = None
    
    # Contexte de marché
    underlying_price: Optional[float] = None
    underlying_change: Optional[float] = None
    time_to_expiry: Optional[int] = None  # jours
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'alerte en dictionnaire"""
        data = asdict(self)
        data['alert_type'] = self.alert_type.value
        data['timestamp'] = self.timestamp.isoformat()
        return data

@dataclass 
class TradingRecommendation:
    """Recommandation de trading basée sur une alerte"""
    ticker: str
    contract: str
    action: TradingAction
    confidence: float  # 0-1
    risk_level: RiskLevel
    reasoning: str
    entry_price_range: Tuple[float, float]  # (min, max)
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size: Optional[str] = None  # "1%", "2%", etc.
    time_horizon: str = ""  # "intraday", "swing", "long-term"
    expected_return: Optional[float] = None
    max_risk: Optional[float] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit la recommandation en dictionnaire"""
        data = asdict(self)
        data['action'] = self.action.value
        data['risk_level'] = self.risk_level.value
        data['timestamp'] = self.timestamp.isoformat()
        return data

class VolumeHistoryManager:
    """Gestionnaire de l'historique de volume pour la détection d'anomalies"""
    
    def __init__(self, max_history: int = 30):
        self.max_history = max_history
        self.volume_history: Dict[str, List[int]] = {}
        self.timestamp_history: Dict[str, List[datetime]] = {}
    
    def add_volume(self, contract_symbol: str, volume: int, timestamp: datetime = None):
        """Ajoute un volume à l'historique"""
        if timestamp is None:
            timestamp = datetime.now()
        
        if contract_symbol not in self.volume_history:
            self.volume_history[contract_symbol] = []
            self.timestamp_history[contract_symbol] = []
        
        self.volume_history[contract_symbol].append(volume)
        self.timestamp_history[contract_symbol].append(timestamp)
        
        # Maintient la taille de l'historique
        if len(self.volume_history[contract_symbol]) > self.max_history:
            self.volume_history[contract_symbol].pop(0)
            self.timestamp_history[contract_symbol].pop(0)
    
    def get_volume_ratio(self, contract_symbol: str) -> float:
        """Calcule le ratio volume actuel vs moyenne"""
        if contract_symbol not in self.volume_history:
            return 1.0
        
        history = self.volume_history[contract_symbol]
        if len(history) < 5:
            return 1.0
        
        current_volume = history[-1]
        avg_volume = np.mean(history[:-1])
        
        if avg_volume == 0:
            return 10.0 if current_volume > 0 else 1.0
        
        return current_volume / avg_volume
    
    def get_z_score(self, contract_symbol: str) -> Optional[float]:
        """Calcule le Z-score du volume actuel"""
        if contract_symbol not in self.volume_history:
            return None
        
        history = self.volume_history[contract_symbol]
        if len(history) < 10:
            return None
        
        current_volume = history[-1]
        historical_volumes = history[:-1]
        
        mean = np.mean(historical_volumes)
        std = np.std(historical_volumes)
        
        if std == 0:
            return 0.0
        
        return (current_volume - mean) / std

class EnhancedOptionsAnalyzer:
    """Analyseur d'options avancé avec détection d'anomalies multifactorielle"""
    
    def __init__(self):
        self.volume_manager = VolumeHistoryManager()
        
        # Seuils de détection configurables
        self.thresholds = {
            'volume_ratio_min': 3.0,
            'volume_ratio_high': 5.0,
            'price_change_min': 0.10,
            'price_change_high': 0.20,
            'z_score_min': 2.0,
            'z_score_high': 3.0,
            'open_interest_min': 1000,
            'open_interest_high': 5000,
            'severity_min': 0.3,
            'confidence_min': 0.4
        }
    
    def analyze_option_contract(self, contract_data: Dict[str, Any], 
                              underlying_data: Dict[str, Any] = None) -> Optional[OptionsAlert]:
        """Analyse complète d'un contrat d'option"""
        try:
            symbol = contract_data.get('symbol', '')
            ticker = contract_data.get('underlying', '')
            
            # 1. Analyse du volume
            current_volume = int(contract_data.get('volume', 0))
            self.volume_manager.add_volume(symbol, current_volume)
            volume_ratio = self.volume_manager.get_volume_ratio(symbol)
            z_score = self.volume_manager.get_z_score(symbol)
            
            # 2. Analyse des prix
            price_change = self._calculate_price_change(contract_data)
            
            # 3. Analyse de l'open interest
            open_interest = int(contract_data.get('open_interest', 0))
            
            # 4. Calcul des métriques d'anomalie
            severity = self._calculate_severity(volume_ratio, price_change, open_interest, z_score)
            confidence = self._calculate_confidence(contract_data, volume_ratio, z_score)
            
            # 5. Détermine le type d'alerte
            alert_type = self._determine_alert_type(volume_ratio, price_change, 
                                                  open_interest, contract_data)
            
            # 6. Vérifie si l'alerte doit être générée
            if severity >= self.thresholds['severity_min'] and confidence >= self.thresholds['confidence_min']:
                
                return OptionsAlert(
                    ticker=ticker,
                    contract=symbol,
                    alert_type=alert_type,
                    severity=severity,
                    confidence=confidence,
                    volume=current_volume,
                    avg_volume=self._get_avg_volume(symbol),
                    open_interest=open_interest,
                    price_change=price_change,
                    unusual_volume_ratio=volume_ratio,
                    timestamp=datetime.now(),
                    description=self._generate_alert_description(alert_type, contract_data, volume_ratio),
                    data_source='hybrid',
                    
                    # Données financières
                    bid=float(contract_data.get('bid', 0)),
                    ask=float(contract_data.get('ask', 0)),
                    last_price=float(contract_data.get('last', 0)),
                    strike=float(contract_data.get('strike', 0)),
                    expiration=contract_data.get('expiration', ''),
                    option_type=contract_data.get('option_type', ''),
                    
                    # Greeks
                    delta=contract_data.get('delta'),
                    gamma=contract_data.get('gamma'),
                    theta=contract_data.get('theta'),
                    vega=contract_data.get('vega'),
                    implied_volatility=contract_data.get('implied_volatility'),
                    
                    # Métriques
                    z_score=z_score,
                    percentile_rank=self._calculate_percentile_rank(symbol, current_volume),
                    
                    # Contexte
                    underlying_price=underlying_data.get('price') if underlying_data else None,
                    underlying_change=underlying_data.get('change_percent') if underlying_data else None,
                    time_to_expiry=self._calculate_time_to_expiry(contract_data.get('expiration', ''))
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur analyse contrat {contract_data.get('symbol', 'Unknown')}: {e}")
            return None
    
    def _calculate_severity(self, volume_ratio: float, price_change: float, 
                          open_interest: int, z_score: Optional[float]) -> float:
        """Calcule la sévérité d'une alerte (0-1)"""
        # Score de volume (0-0.4)
        volume_score = min(volume_ratio / 10.0, 0.4)
        
        # Score de changement de prix (0-0.3)
        price_score = min(abs(price_change), 0.3)
        
        # Score d'open interest (0-0.2)
        oi_score = min(open_interest / 50000.0, 0.2)
        
        # Score Z-score (0-0.1)
        z_score_bonus = 0.0
        if z_score and abs(z_score) > 2.0:
            z_score_bonus = min(abs(z_score) / 10.0, 0.1)
        
        severity = volume_score + price_score + oi_score + z_score_bonus
        return min(severity, 1.0)
    
    def _calculate_confidence(self, contract_data: Dict[str, Any], 
                            volume_ratio: float, z_score: Optional[float]) -> float:
        """Calcule la confiance dans l'alerte (0-1)"""
        confidence = 0.0
        
        # Confiance basée sur le volume
        if volume_ratio > 2.0:
            confidence += 0.3
        
        # Confiance basée sur le Z-score
        if z_score and abs(z_score) > 1.5:
            confidence += 0.3
        
        # Confiance basée sur la liquidité (bid-ask spread)
        bid = float(contract_data.get('bid', 0))
        ask = float(contract_data.get('ask', 0))
        if bid > 0 and ask > 0:
            spread_ratio = (ask - bid) / bid
            if spread_ratio < 0.1:  # Spread serré = plus liquide
                confidence += 0.2
        
        # Confiance basée sur l'open interest
        oi = int(contract_data.get('open_interest', 0))
        if oi > 1000:
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _determine_alert_type(self, volume_ratio: float, price_change: float,
                            open_interest: int, contract_data: Dict[str, Any]) -> AlertType:
        """Détermine le type d'alerte basé sur les métriques"""
        option_type = contract_data.get('option_type', '').lower()
        
        if volume_ratio >= self.thresholds['volume_ratio_high']:
            return AlertType.UNUSUAL_CALL_VOLUME if option_type == 'call' else AlertType.UNUSUAL_PUT_VOLUME
        
        if abs(price_change) >= self.thresholds['price_change_high']:
            return AlertType.SIGNIFICANT_PRICE_MOVEMENT
        
        if open_interest >= self.thresholds['open_interest_high'] and volume_ratio > 2.0:
            return AlertType.HIGH_OI_ACTIVITY
        
        # Détection de potential gamma squeeze
        if (option_type == 'call' and volume_ratio > 4.0 and 
            contract_data.get('delta', 0) > 0.5):
            return AlertType.GAMMA_SQUEEZE_POTENTIAL
        
        return AlertType.ANOMALY_DETECTED
    
    def _generate_alert_description(self, alert_type: AlertType, 
                                  contract_data: Dict[str, Any], volume_ratio: float) -> str:
        """Génère une description de l'alerte"""
        strike = contract_data.get('strike', 0)
        option_type = contract_data.get('option_type', '').upper()
        expiration = contract_data.get('expiration', '')
        
        descriptions = {
            AlertType.UNUSUAL_CALL_VOLUME: 
                f"Volume inhabituel sur {option_type} ${strike} exp {expiration} ({volume_ratio:.1f}x normal)",
            AlertType.UNUSUAL_PUT_VOLUME: 
                f"Volume inhabituel sur {option_type} ${strike} exp {expiration} ({volume_ratio:.1f}x normal)",
            AlertType.SIGNIFICANT_PRICE_MOVEMENT: 
                f"Mouvement significatif sur {option_type} ${strike}",
            AlertType.HIGH_OI_ACTIVITY: 
                f"Activité élevée sur contrat à fort OI: {contract_data.get('open_interest', 0):,}",
            AlertType.GAMMA_SQUEEZE_POTENTIAL: 
                f"Potentiel gamma squeeze sur {option_type} ${strike}",
            AlertType.ANOMALY_DETECTED: 
                f"Anomalie détectée sur {option_type} ${strike}"
        }
        
        return descriptions.get(alert_type, f"Activité anormale sur {contract_data.get('symbol', '')}")
    
    def _get_avg_volume(self, symbol: str) -> float:
        """Récupère le volume moyen pour un symbole"""
        if symbol not in self.volume_manager.volume_history:
            return 0.0
        
        history = self.volume_manager.volume_history[symbol]
        return np.mean(history[:-1]) if len(history) > 1 else 0.0
    
    def _calculate_price_change(self, contract_data: Dict[str, Any]) -> float:
        """Calcule le changement de prix (placeholder)"""
        # À implémenter avec données historiques
        bid = float(contract_data.get('bid', 0))
        ask = float(contract_data.get('ask', 0))
        
        if bid > 0 and ask > 0:
            spread = (ask - bid) / bid
            return min(spread, 1.0)
        
        return 0.0
    
    def _calculate_percentile_rank(self, symbol: str, current_volume: int) -> Optional[float]:
        """Calcule le rang percentile du volume actuel"""
        if symbol not in self.volume_manager.volume_history:
            return None
        
        history = self.volume_manager.volume_history[symbol]
        if len(history) < 10:
            return None
        
        historical_volumes = history[:-1]
        rank = sum(1 for v in historical_volumes if v <= current_volume)
        return rank / len(historical_volumes)
    
    def _calculate_time_to_expiry(self, expiration_str: str) -> Optional[int]:
        """Calcule les jours jusqu'à l'expiration"""
        try:
            if not expiration_str:
                return None
            
            exp_date = datetime.strptime(expiration_str, '%Y-%m-%d')
            today = datetime.now()
            return (exp_date - today).days
        
        except Exception:
            return None

class TradingRecommendationEngine:
    """Moteur de recommandations de trading basé sur les alertes"""
    
    def __init__(self):
        self.strategies = {
            AlertType.UNUSUAL_CALL_VOLUME: self._recommend_unusual_call_volume,
            AlertType.UNUSUAL_PUT_VOLUME: self._recommend_unusual_put_volume,
            AlertType.GAMMA_SQUEEZE_POTENTIAL: self._recommend_gamma_squeeze,
            AlertType.HIGH_OI_ACTIVITY: self._recommend_high_oi_activity,
            AlertType.SIGNIFICANT_PRICE_MOVEMENT: self._recommend_price_movement
        }
    
    def generate_recommendation(self, alert: OptionsAlert) -> Optional[TradingRecommendation]:
        """Génère une recommandation basée sur l'alerte"""
        try:
            strategy_func = self.strategies.get(alert.alert_type)
            if strategy_func:
                return strategy_func(alert)
            
            # Recommandation par défaut
            return self._default_recommendation(alert)
            
        except Exception as e:
            logger.error(f"Erreur génération recommandation: {e}")
            return None
    
    def _recommend_unusual_call_volume(self, alert: OptionsAlert) -> TradingRecommendation:
        """Recommandation pour volume inhabituel sur calls"""
        if alert.severity >= 0.8:
            action = TradingAction.BUY_CALL
            risk_level = RiskLevel.MEDIUM
            reasoning = f"Volume exceptionnel ({alert.unusual_volume_ratio:.1f}x) suggère mouvement haussier"
        else:
            action = TradingAction.MONITOR
            risk_level = RiskLevel.LOW
            reasoning = "Volume élevé à surveiller, confirmation nécessaire"
        
        return TradingRecommendation(
            ticker=alert.ticker,
            contract=alert.contract,
            action=action,
            confidence=alert.confidence,
            risk_level=risk_level,
            reasoning=reasoning,
            entry_price_range=(alert.bid, alert.ask),
            time_horizon="swing" if alert.time_to_expiry and alert.time_to_expiry > 7 else "intraday"
        )
    
    def _recommend_unusual_put_volume(self, alert: OptionsAlert) -> TradingRecommendation:
        """Recommandation pour volume inhabituel sur puts"""
        if alert.severity >= 0.8:
            action = TradingAction.BUY_PUT
            risk_level = RiskLevel.MEDIUM
            reasoning = f"Volume exceptionnel ({alert.unusual_volume_ratio:.1f}x) suggère mouvement baissier"
        else:
            action = TradingAction.MONITOR
            risk_level = RiskLevel.LOW
            reasoning = "Volume élevé à surveiller, confirmation nécessaire"
        
        return TradingRecommendation(
            ticker=alert.ticker,
            contract=alert.contract,
            action=action,
            confidence=alert.confidence,
            risk_level=risk_level,
            reasoning=reasoning,
            entry_price_range=(alert.bid, alert.ask),
            time_horizon="swing" if alert.time_to_expiry and alert.time_to_expiry > 7 else "intraday"
        )
    
    def _recommend_gamma_squeeze(self, alert: OptionsAlert) -> TradingRecommendation:
        """Recommandation pour potentiel gamma squeeze"""
        return TradingRecommendation(
            ticker=alert.ticker,
            contract=alert.contract,
            action=TradingAction.BUY_CALL,
            confidence=min(alert.confidence + 0.1, 1.0),
            risk_level=RiskLevel.HIGH,
            reasoning="Potentiel gamma squeeze détecté - mouvement explosif possible",
            entry_price_range=(alert.bid, alert.ask),
            time_horizon="intraday"
        )
    
    def _recommend_high_oi_activity(self, alert: OptionsAlert) -> TradingRecommendation:
        """Recommandation pour activité sur contrats à fort OI"""
        return TradingRecommendation(
            ticker=alert.ticker,
            contract=alert.contract,
            action=TradingAction.MONITOR,
            confidence=alert.confidence,
            risk_level=RiskLevel.MEDIUM,
            reasoning=f"Activité sur contrat liquide (OI: {alert.open_interest:,})",
            entry_price_range=(alert.bid, alert.ask),
            time_horizon="swing"
        )
    
    def _recommend_price_movement(self, alert: OptionsAlert) -> TradingRecommendation:
        """Recommandation pour mouvement de prix significatif"""
        action = TradingAction.BUY_CALL if alert.price_change > 0 else TradingAction.BUY_PUT
        
        return TradingRecommendation(
            ticker=alert.ticker,
            contract=alert.contract,
            action=action,
            confidence=alert.confidence,
            risk_level=RiskLevel.MEDIUM,
            reasoning=f"Mouvement de prix significatif ({alert.price_change:.1%})",
            entry_price_range=(alert.bid, alert.ask),
            time_horizon="intraday"
        )
    
    def _default_recommendation(self, alert: OptionsAlert) -> TradingRecommendation:
        """Recommandation par défaut"""
        return TradingRecommendation(
            ticker=alert.ticker,
            contract=alert.contract,
            action=TradingAction.MONITOR,
            confidence=alert.confidence,
            risk_level=RiskLevel.LOW,
            reasoning="Anomalie détectée - surveillance recommandée",
            entry_price_range=(alert.bid, alert.ask),
            time_horizon="monitor"
        )

# Exemple d'utilisation
if __name__ == "__main__":
    # Test du système d'alertes
    analyzer = EnhancedOptionsAnalyzer()
    recommendation_engine = TradingRecommendationEngine()
    
    # Données de test
    test_contract = {
        'symbol': 'AAPL240315C00150000',
        'underlying': 'AAPL',
        'strike': 150.0,
        'option_type': 'call',
        'expiration': '2024-03-15',
        'bid': 2.50,
        'ask': 2.55,
        'last': 2.52,
        'volume': 15000,
        'open_interest': 25000,
        'delta': 0.65
    }
    
    # Analyse du contrat
    alert = analyzer.analyze_option_contract(test_contract)
    
    if alert:
        print("🚨 ALERTE GÉNÉRÉE:")
        print(f"  Ticker: {alert.ticker}")
        print(f"  Type: {alert.alert_type.value}")
        print(f"  Sévérité: {alert.severity:.2f}")
        print(f"  Confiance: {alert.confidence:.2f}")
        print(f"  Description: {alert.description}")
        
        # Génère une recommandation
        recommendation = recommendation_engine.generate_recommendation(alert)
        
        if recommendation:
            print("\n💡 RECOMMANDATION:")
            print(f"  Action: {recommendation.action.value}")
            print(f"  Niveau de risque: {recommendation.risk_level.value}")
            print(f"  Raisonnement: {recommendation.reasoning}")
    else:
        print("Aucune alerte générée pour ce contrat")