# option_model.py
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class OptionScreenerResult:
    """Modèle pour les résultats du screener d'options"""
    symbol: str                    # Symbole underlying
    side: str                     # 'call' pour le moment
    strike: float                 # Prix d'exercice
    expiration: str               # Date d'expiration YYYY-MM-DD
    delta: float                  # Delta de l'option
    volume_1d: int               # Volume du jour
    volume_7d: int               # Volume 7 jours
    open_interest: int           # Open Interest

    # Métadonnées supplémentaires
    option_symbol: str           # Symbole OCC complet
    last_price: float            # Dernier prix
    bid: float                   # Prix bid
    ask: float                   # Prix ask
    implied_volatility: float    # IV
    whale_score: float           # Score de détection "baleine"
    dte: int                    # Days to expiration

    @property
    def volume_oi_ratio_1d(self) -> float:
        """Ratio Volume 1J/Open Interest"""
        return self.volume_1d / self.open_interest if self.open_interest > 0 else 0

    @property
    def volume_oi_ratio_7d(self) -> float:
        """Ratio Volume 7J/Open Interest"""
        return self.volume_7d / self.open_interest if self.open_interest > 0 else 0

    @property
    def midpoint(self) -> float:
        """Prix milieu bid-ask"""
        return (self.bid + self.ask) / 2 if (self.bid and self.ask) else self.last_price
