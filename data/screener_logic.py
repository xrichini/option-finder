# screener_logic.py
from typing import List
from datetime import datetime
from models.option_model import OptionScreenerResult
from data.tradier_client import TradierClient
from utils.config import Config


class OptionsScreener:
    def __init__(self):
        self.config = Config()
        self.client = TradierClient()

    def calculate_whale_score(
        self,
        volume_1d: int,
        volume_7d: int,
        open_interest: int,
        delta: float,
        iv: float,
    ) -> float:
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

    def _screen_options(
        self,
        symbols: List[str],
        option_type: str,
        max_dte: int = 7,
        min_volume: int = 1000,
        min_oi: int = 500,
        min_whale_score: float = 70,
    ) -> List[OptionScreenerResult]:
        """
        Screen générique pour détecter les big options buying

        Args:
            symbols: Liste des symboles à analyser
            option_type: 'call' ou 'put'
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

            # 2. Filtrer les expirations par DTE
            # Filtrer les expirations par DTE
            filtered_exps = self.client.filter_expirations_by_dte(expirations, max_dte)
            if not filtered_exps:
                print(f"❌ Pas d'expirations < {max_dte} DTE pour {symbol}")
                continue

            # 3. Pour chaque expiration, analyser les options
            print(f"📅 Analyse de {len(filtered_exps)} expirations...")

            for expiration in filtered_exps:
                try:
                    # Récupérer les chaînes d'options
                    chain_data = self.client.get_option_chains(symbol, expiration)
                    if not chain_data:
                        continue

                    # Filtrer par type d'option (call/put)
                    options = [
                        opt
                        for opt in chain_data
                        if (
                            opt["option_type"].lower() == option_type
                            and opt["volume"] >= min_volume
                            and opt["open_interest"] >= min_oi
                        )
                    ]

                except Exception as e:
                    print(f"❌ Erreur: {symbol} exp. {expiration} - {str(e)}")
                    continue

                # 4. Analyser chaque option
                for opt in options:
                    try:
                        # Vérifier données requises
                        required_fields = [
                            "volume",
                            "open_interest",
                            "symbol",
                            "expiration_date",
                            "strike",
                        ]
                        if not all(field in opt for field in required_fields):
                            symbol_str = opt.get("symbol", "?")
                            print(f"❌ Données manquantes: {symbol_str}")
                            continue

                        # Extraire métriques avec validation
                        volume_1d = int(opt["volume"])
                        open_interest = int(opt["open_interest"])
                        volume_7d = volume_1d * 7  # TODO: Vraie donnée 7j
                        strike = float(opt["strike"])

                        # Traiter les Greeks avec précaution
                        greeks = opt.get("greeks", {}) or {}
                        try:
                            delta = float(greeks.get("delta", 0.3))
                            iv = float(greeks.get("mid_iv", 0.4))
                        except (ValueError, TypeError):
                            delta = 0.3
                            iv = 0.4

                        # Calculer whale score
                        whale_score = self.calculate_whale_score(
                            volume_1d=volume_1d,
                            volume_7d=volume_7d,
                            open_interest=open_interest,
                            delta=abs(delta),  # Valeur absolue pour les puts
                            iv=iv,
                        )

                        # Vérifier si au-dessus du seuil
                        if whale_score >= min_whale_score:
                            result = OptionScreenerResult(
                                symbol=symbol,
                                option_symbol=opt["symbol"],
                                expiration=opt["expiration_date"],
                                strike=strike,
                                side=option_type,
                                delta=delta,
                                volume_1d=volume_1d,
                                volume_7d=volume_7d,
                                open_interest=open_interest,
                                last_price=float(opt.get("last", 0.0)),
                                bid=float(opt.get("bid", 0.0)),
                                ask=float(opt.get("ask", 0.0)),
                                implied_volatility=iv,
                                whale_score=whale_score,
                                dte=int(
                                    (
                                        datetime.strptime(
                                            opt["expiration_date"], "%Y-%m-%d"
                                        )
                                        - datetime.now()
                                    ).days
                                ),
                            )
                            results.append(result)
                            score_msg = (
                                f"✅ {result.option_symbol} "
                                f"Score: {whale_score:.0f}"
                            )
                            print(score_msg)

                    except Exception as e:
                        option_info = {
                            "symbol": opt.get("symbol", "N/A"),
                            "type": opt.get("option_type", "N/A"),
                            "data": opt,
                        }
                        print(f"❌ Erreur traitement option: {str(e)}")
                        print(f"🔍 Détails option en erreur: {option_info}")
                        continue

        return results

    def screen_big_calls(
        self,
        symbols: List[str],
        max_dte: int = 7,
        min_volume: int = 1000,
        min_oi: int = 500,
        min_whale_score: float = 70,
    ) -> List[OptionScreenerResult]:
        """Screen principal pour détecter les big call buying"""
        return self._screen_options(
            symbols=symbols,
            option_type="call",
            max_dte=max_dte,
            min_volume=min_volume,
            min_oi=min_oi,
            min_whale_score=min_whale_score,
        )

    def screen_big_puts(
        self,
        symbols: List[str],
        max_dte: int = 7,
        min_volume: int = 1000,
        min_oi: int = 500,
        min_whale_score: float = 70,
    ) -> List[OptionScreenerResult]:
        """Screen principal pour détecter les big put buying"""
        return self._screen_options(
            symbols=symbols,
            option_type="put",
            max_dte=max_dte,
            min_volume=min_volume,
            min_oi=min_oi,
            min_whale_score=min_whale_score,
        )
