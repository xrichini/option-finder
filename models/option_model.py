# option_model.py
from dataclasses import dataclass
from typing import Dict


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
    
    @property
    def vol_oi_ratio(self) -> float:
        """Volume/Open Interest ratio (Unusual Whales key metric)"""
        return self.volume_1d / self.open_interest if self.open_interest > 0 else float('inf')
    
    @property
    def block_size_category(self) -> str:
        """Categorize block size for institutional detection"""
        if self.volume_1d >= 10000:
            return "🐋 Whale"
        elif self.volume_1d >= 5000:
            return "🦑 Large"
        elif self.volume_1d >= 2000:
            return "🐟 Medium"
        else:
            return "🦐 Small"
    
    @property
    def is_unusual_activity(self) -> bool:
        """Check if activity meets Unusual Whales criteria"""
        return self.vol_oi_ratio >= 1.0 or self.volume_1d >= 5000
    
    @property
    def is_new_position(self) -> bool:
        """Likely new position based on high Vol/OI ratio"""
        return self.vol_oi_ratio >= 1.0
    
    @property
    def volume_vs_average_display(self) -> str:
        """Display volume compared to historical average (if available)"""
        # This will be populated by the screener if historical data exists
        return getattr(self, '_volume_vs_avg', "N/A")
    
    @property 
    def oi_trend_display(self) -> str:
        """Display OI trend compared to historical average (if available)"""
        # This will be populated by the screener if historical data exists
        return getattr(self, '_oi_trend', "N/A")
    
    @property
    def anomaly_badge(self) -> str:
        """Badge indicating if this is an anomalous activity"""
        # This will be set by the screener based on historical analysis
        return getattr(self, '_anomaly_badge', "")
    
    def set_historical_context(self, volume_ratio: float = None, oi_ratio: float = None):
        """Set historical context for display purposes"""
        if volume_ratio is not None:
            if volume_ratio >= 3.0:
                self._volume_vs_avg = f"↗️ {volume_ratio*100:.0f}%"
                self._anomaly_badge = "🚨 Hot"
            elif volume_ratio >= 1.5:
                self._volume_vs_avg = f"↗️ {volume_ratio*100:.0f}%"
            elif volume_ratio <= 0.7:
                self._volume_vs_avg = f"↘️ {volume_ratio*100:.0f}%"
            else:
                self._volume_vs_avg = f"➡️ {volume_ratio*100:.0f}%"
        
        if oi_ratio is not None:
            if oi_ratio >= 2.0:
                self._oi_trend = f"🔺 +{(oi_ratio-1)*100:.0f}%"
            elif oi_ratio <= 0.8:
                self._oi_trend = f"🔻 {(1-oi_ratio)*100:.0f}%"
            else:
                self._oi_trend = f"➡️ {(oi_ratio-1)*100:.0f}%"
    
    def set_ai_analysis(self, ai_results: Dict = None):
        """Set AI analysis results for display purposes"""
        if ai_results:
            self._ai_analysis = ai_results
            
            # Set AI-enhanced badge based on analysis
            if ai_results.get('fundamental', {}).get('confidence_score', 0) > 80:
                self._ai_badge = "🧠 AI: Strong"
            elif ai_results.get('sentiment', {}).get('confidence_score', 0) > 75:
                self._ai_badge = "🧠 AI: Bullish" if ai_results['sentiment'].detailed_analysis.get('sentiment_score', 50) > 60 else "🧠 AI: Bearish"
            elif ai_results.get('catalysts'):
                self._ai_badge = "🧠 AI: Catalyst"
    
    @property
    def ai_summary_display(self) -> str:
        """Display AI analysis summary (if available)"""
        ai_analysis = getattr(self, '_ai_analysis', None)
        if not ai_analysis:
            return "N/A"
        
        summaries = []
        if 'fundamental' in ai_analysis:
            summaries.append(f"Fund: {ai_analysis['fundamental'].summary[:50]}...")
        if 'sentiment' in ai_analysis:
            score = ai_analysis['sentiment'].detailed_analysis.get('sentiment_score', 50)
            summaries.append(f"Sentiment: {score}/100")
        if 'catalysts' in ai_analysis:
            summaries.append(f"Catalysts: {len(ai_analysis['catalysts'].detailed_analysis.get('catalysts', []))}")
        
        return " | ".join(summaries) if summaries else "N/A"
    
    @property
    def ai_badge(self) -> str:
        """Badge indicating AI analysis result"""
        return getattr(self, '_ai_badge', "")
