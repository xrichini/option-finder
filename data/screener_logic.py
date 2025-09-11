# screener_logic.py
import pandas as pd
import yfinance as yf
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from models.option_model import OptionScreenerResult
from tradier_client import TradierClient
from utils.config import Config


class OptionsScreener:
    def __init__(self):
        self.config = Config()
        self.client = TradierClient()
    
    def calculate_whale_score(self, volume_1d: int, volume_7d: int, open_interest: int, 
                             delta: float, iv: float) -> float:
        """Score de probabilité de 'whale' basé sur plusieurs critères"""
        score = 0
        
        # Volume 1 jour score (0-25 points)
        if volume_1d > 5000:
            score += 25
        elif volume_1d > 2000:
            score += 20
        elif volume_1d > 1000:
            score += 15
        elif volume_1d > 500:
            score += 10
        
        # Volume 7 jours score (0-25 points)
        if volume_7d > 20000:
            score += 25
        elif volume_7d > 10000:
            score += 20
        elif volume_7d > 5000:
            score += 15
        
        # Ratio Volume/OI score (0-25 points)
        vol_oi_ratio = volume_1d / open_interest if open_interest > 0 else 0
        if vol_oi_ratio > 5:
            score += 25
        elif vol_oi_ratio > 3:
            score += 20
        elif vol_oi_ratio > 2:
            score += 15
        elif vol_oi_ratio > 1:
            score += 10
        
        # Delta score pour calls ITM/ATM (0-15 points)
        if delta > 0.4:
            score += 15
        elif delta > 0.3:
            score += 10
        elif delta > 0.2:
            score += 5
        
        # Implied Volatility score (0-10 points)
        if iv > 0.8:
            score += 10
        elif iv > 0.5:
            score += 7
        elif iv > 0.3:
            score += 5
        
        return min(score, 100)  # Cap à 100
    
    def screen_big_calls(self, symbols: List[str], max_dte: int = 7, 
                        min_volume: int = 1000, min_oi: int = 500,
                        min_whale_score: float = 70) -> List[OptionScreenerResult]:
        """
        Screen principal pour détecter les big call buying
        
        Args:
            symbols: Liste des symboles à analyser
            max_dte: DTE maximum (défaut 7)
            min_volume: Volume minimum requis
            min_oi: Open Interest minimum
            min_whale_score: Score minimum pour être considéré comme whale
        """
        results = []
        
        for symbol in symbols:
            print(f"🔍 Analyse {symbol}...")
            
            # 1. Récupérer les expirations disponibles
            expirations = self.client.get_option_expirations(symbol)
            if not expirations:
                print(f"❌ Pas d'expirations pour {symbol}")
                continue
            
            # 2. Filtrer par DTE
            filtered_exps = self.client.filter_expirations_by_dte(expirations, max_dte)
            if not filtered_exps:
                print(f"❌ Pas d'expirations dans la plage DTE pour {symbol}")
                continue
            
            print(f"📅 {len(filtered_exps)} expirations trouvées: {filtered_exps}")
            
            # 3. Analyser chaque expiration
            for expiration in filtered_exps:
                chain_data = self.client.get_option_chains(symbol, expiration)
                
                if not chain_data or 'options' not in chain_data:
                    continue
                
                # Parse les options de la chaîne
                options = chain_data['options'].get('option', [])
                if isinstance(options, dict):  # Si une seule option
                    options = [options]
                
                # 4. Filtrer les calls uniquement
                for option in options:
                    if option.get('option_type') != 'call':
                        continue
                    
                    # Extraire les données
                    volume_1d = int(option.get('volume', 0))
                    open_interest = int(option.get('open_interest', 0))
                    
                    # Filtres de base
                    if volume_1d < min_volume or open_interest < min_oi:
                        continue
                    
                    # Greeks et autres données
                    greeks = option.get('greeks', {})
                    delta = float(greeks.get('delta', 0))
                    iv = float(greeks.get('smv_vol', 0))
                    
                    # Volume 7 jours (estimation pour MVP)
                    volume_7d = volume_1d * 5  # Estimation simplifiée
                    
                    # Calcul du whale score
                    whale_score = self.calculate_whale_score(
                        volume_1d, volume_7d, open_interest, delta, iv
                    )
                    
                    # Filtre par whale score
                    if whale_score < min_whale_score:
                        continue
                    
                    # Calculer DTE
                    exp_date = datetime.strptime(expiration, '%Y-%m-%d').date()
                    dte = (exp_date - datetime.now().date()).days
                    
                    # Créer le résultat
                    result = OptionScreenerResult(
                        symbol=symbol,
                        side='call',
                        strike=float(option.get('strike', 0)),
                        expiration=expiration,
                        delta=delta,
                        volume_1d=volume_1d,
                        volume_7d=volume_7d,
                        open_interest=open_interest,
                        option_symbol=option.get('symbol', ''),
                        last_price=float(option.get('last', 0)),
                        bid=float(option.get('bid', 0)),
                        ask=float(option.get('ask', 0)),
                        implied_volatility=iv,
                        whale_score=whale_score,
                        dte=dte
                    )
                    
                    results.append(result)
                    print(f"✅ Trouvé: {result.option_symbol} - Score: {whale_score:.0f}")
        
        # Tri par whale score décroissant
        return sorted(results, key=lambda x: x.whale_score, reverse=True)
    
    def get_short_interest_data(self, symbols: List[str], 
                               min_short_interest: float = 30.0) -> List[Dict]:
        """
        Récupère les données de short interest pour les symboles
        
        Args:
            symbols: Liste des symboles
            min_short_interest: Short interest minimum en %
        """
        candidates = []
        
        print(f"🔍 Analyse short interest (seuil: {min_short_interest}%)")
        
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                
                short_ratio = info.get('shortRatio', 0)
                short_percent = info.get('shortPercentOfFloat', 0)
                
                if short_percent >= min_short_interest:
                    candidates.append({
                        'symbol': symbol,
                        'short_ratio': short_ratio,
                        'short_percent': short_percent,
                        'market_cap': info.get('marketCap', 0),
                        'float_shares': info.get('floatShares', 0)
                    })
                    print(f"✅ {symbol}: {short_percent:.1f}% short interest")
                else:
                    print(f"❌ {symbol}: {short_percent:.1f}% (< {min_short_interest}%)")
                    
            except Exception as e:
                print(f"❌ Erreur pour {symbol}: {e}")
                continue
        
        return sorted(candidates, key=lambda x: x['short_percent'], reverse=True)
