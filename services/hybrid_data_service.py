#!/usr/bin/env python3
"""
Service hybride Tradier + Polygon.io
Architecture hybride optimale selon WARP.md

🚀 Tradier comme source principale (temps réel)
- Données options temps réel gratuites
- Greeks disponibles (delta, gamma, theta, vega)
- Pas de limite stricte de requêtes
- Open Interest en temps réel

📊 Polygon.io comme complément (historique)
- Données historiques pour calculs de moyennes
- Tendances long terme pour contexte
- Backtesting de vos stratégies
"""

from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass

from data.enhanced_tradier_client import EnhancedTradierClient
from data.polygon_client import PolygonClient
from models.api_models import OptionsOpportunity
from utils.config import Config

logger = logging.getLogger(__name__)


@dataclass
class HybridMetrics:
    """Métriques enrichies par l'architecture hybride"""

    # Données temps réel (Tradier)
    current_volume: int
    current_oi: int
    current_price: float
    greeks_quality: str  # "excellent", "good", "poor"

    # Greeks temps réel (Tradier)
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    rho: Optional[float] = None
    implied_volatility: Optional[float] = None

    # Données historiques (Polygon.io)
    avg_volume_30d: Optional[float] = None
    volume_anomaly_ratio: Optional[float] = None  # volume_current / avg_volume_30d
    price_trend_30d: Optional[str] = None  # "bullish", "bearish", "neutral"
    volatility_regime: Optional[str] = None  # "low", "normal", "high"

    # Prix sous-jacent pour calcul de moneyness
    underlying_price: Optional[float] = None

    # Scores composites
    realtime_score: float = 0.0
    historical_score: float = 0.0
    hybrid_score: float = 0.0

    # Métadonnées
    data_freshness: str = "unknown"  # "fresh", "stale", "partial"
    polygon_available: bool = False


class HybridDataService:
    """Service hybride optimisant Tradier (temps réel) + Polygon.io (historique)"""

    def __init__(self, enable_polygon: bool = True):
        # Client Tradier (source principale)
        self.tradier_client = EnhancedTradierClient(api_token="", sandbox=None)

        # Client Polygon.io (source historique optionnelle)
        self.polygon_client = None
        self.polygon_enabled = False
        self.polygon_invalid_key = (
            False  # Flag pour éviter les retries avec clé invalide
        )

        if enable_polygon:
            try:
                polygon_key = Config.get_polygon_api_key()
                if polygon_key and not polygon_key.startswith("your_"):
                    self.polygon_client = PolygonClient(polygon_key)

                    # Valider la clé au démarrage
                    if self.polygon_client.validate_key():
                        self.polygon_enabled = True
                        logger.info(
                            "📊 Polygon.io client activé pour données historiques"
                        )
                    else:
                        logger.warning(
                            "❌ Polygon.io clé invalide - données historiques désactivées"
                        )
                        self.polygon_invalid_key = True
                        self.polygon_client = None
                else:
                    logger.info(
                        "📊 Polygon.io non configuré - utilisation Tradier seul"
                    )
            except Exception as e:
                logger.warning(f"📊 Polygon.io non disponible: {e}")
                self.polygon_invalid_key = True
                self.polygon_client = None

        # Cache pour optimiser les performances
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes

        logger.info("🔄 Service hybride initialisé:")
        logger.info("   Tradier (principal): ✅")
        if self.polygon_enabled:
            logger.info("   Polygon.io (historique): ✅")
        else:
            logger.debug("   Polygon.io (historique): ❌ (non configuré — optionnel)")

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Vérifie si l'entrée de cache est valide"""
        if cache_key not in self.cache:
            return False

        cached_data, timestamp = self.cache[cache_key]
        return (datetime.now() - timestamp).seconds < self.cache_ttl

    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Récupère une donnée du cache si valide"""
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key][0]
        return None

    def _save_to_cache(self, cache_key: str, data: Any) -> None:
        """Sauvegarde une donnée dans le cache"""
        self.cache[cache_key] = (data, datetime.now())

    async def get_historical_volume_data(
        self, symbol: str, days: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        Récupère les données historiques de volume via Polygon.io

        Args:
            symbol: Symbole du titre sous-jacent
            days: Nombre de jours d'historique

        Returns:
            Dictionnaire avec métriques historiques ou None si indisponible
        """

        if not self.polygon_enabled:
            return None

        cache_key = f"historical_volume_{symbol}_{days}"
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data

        # Si Polygon est désactivé ou la clé est invalide, retourner None
        if not self.polygon_enabled or self.polygon_invalid_key:
            return None

        try:
            # Récupération des barres historiques
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            stock_bars = self.polygon_client.get_stock_aggregates(
                ticker=symbol,
                multiplier=1,
                timespan="day",
                from_date=start_date,
                to_date=end_date,
                limit=days,
            )

            if not stock_bars:
                return None

            # Calcul des métriques
            volumes = [bar.volume for bar in stock_bars]
            prices = [bar.close for bar in stock_bars]

            if not volumes or not prices:
                return None

            avg_volume = sum(volumes) / len(volumes)
            max_volume = max(volumes)
            min_volume = min(volumes)

            # Tendance de prix
            price_change = (prices[-1] - prices[0]) / prices[0] * 100
            if price_change > 5:
                price_trend = "bullish"
            elif price_change < -5:
                price_trend = "bearish"
            else:
                price_trend = "neutral"

            # Régime de volatilité (écart-type des rendements quotidiens)
            if len(prices) > 1:
                returns = [
                    (prices[i] - prices[i - 1]) / prices[i - 1]
                    for i in range(1, len(prices))
                ]
                volatility = (sum(r**2 for r in returns) / len(returns)) ** 0.5 * 100

                if volatility > 3:
                    volatility_regime = "high"
                elif volatility > 1.5:
                    volatility_regime = "normal"
                else:
                    volatility_regime = "low"
            else:
                volatility_regime = "unknown"

            historical_data = {
                "avg_volume": avg_volume,
                "max_volume": max_volume,
                "min_volume": min_volume,
                "price_trend": price_trend,
                "price_change_pct": price_change,
                "volatility_regime": volatility_regime,
                "data_points": len(stock_bars),
                "period_days": days,
            }

            self._save_to_cache(cache_key, historical_data)
            logger.debug(
                f"📊 Données historiques Polygon.io pour {symbol}: {len(stock_bars)} jours"
            )

            return historical_data

        except ValueError as e:
            # Erreur d'authentification (401) - désactiver Polygon complètement
            if "Invalid Polygon API key" in str(e) or "forbidden" in str(e).lower():
                logger.error(
                    f"❌ Polygon.io clé API invalide - désactivation complète: {e}"
                )
                self.polygon_enabled = False
                self.polygon_invalid_key = True
                self.polygon_client = None
            else:
                logger.warning(f"❌ Erreur Polygon {symbol}: {e}")
            return None
        except Exception as e:
            logger.warning(f"❌ Erreur récupération données historiques {symbol}: {e}")
            return None

    async def get_multiple_underlying_prices(
        self, symbols: List[str]
    ) -> Dict[str, float]:
        """
        Récupère les prix de plusieurs sous-jacents en un seul appel API

        Args:
            symbols: Liste des symboles de sous-jacents

        Returns:
            Dictionnaire {symbole: prix} pour chaque symbole
        """

        if not symbols:
            return {}

        # Suppression des doublons
        unique_symbols = list(set(s.upper().strip() for s in symbols if s.strip()))

        if not unique_symbols:
            return {}

        # Vérifier le cache pour chaque symbole
        prices_dict = {}
        symbols_to_fetch = []

        for symbol in unique_symbols:
            cache_key = f"underlying_price_{symbol}"
            cached_price = self._get_from_cache(cache_key)
            if cached_price is not None:
                prices_dict[symbol] = cached_price
            else:
                symbols_to_fetch.append(symbol)

        # Si tous les prix sont en cache, retourner directement
        if not symbols_to_fetch:
            logger.debug(f"💾 Tous les prix en cache: {', '.join(unique_symbols)}")
            return prices_dict

        try:
            # Appel API unique pour tous les symboles restants
            logger.info(
                f"📊 Récupération prix multiples: {', '.join(symbols_to_fetch)}"
            )
            quotes_data = self.tradier_client.get_multiple_underlying_quotes(
                symbols_to_fetch
            )

            for symbol, quote_data in quotes_data.items():
                if quote_data and quote_data.get("last", 0) > 0:
                    price = float(quote_data["last"])
                    prices_dict[symbol] = price

                    # Cache individuel pour chaque prix (30 secondes)
                    cache_key = f"underlying_price_{symbol}"
                    self.cache[cache_key] = (price, datetime.now())

            if quotes_data:
                logger.info(
                    f"✅ Récupéré {len(quotes_data)} prix sous-jacents en 1 appel API"
                )

            return prices_dict

        except Exception as e:
            logger.warning(f"⚠️ Erreur récupération prix multiples: {e}")
            return prices_dict  # Retourne au moins les prix en cache

    async def get_underlying_price(self, symbol: str) -> Optional[float]:
        """
        Récupère le prix d'un seul sous-jacent (pour compatibilité)

        Args:
            symbol: Symbole du titre sous-jacent

        Returns:
            Prix actuel ou None si non disponible
        """

        prices = await self.get_multiple_underlying_prices([symbol])
        return prices.get(symbol.upper())

    async def enrich_opportunity_with_hybrid_data(
        self,
        opp: OptionsOpportunity,
        preloaded_underlying_price: Optional[float] = None,
    ) -> HybridMetrics:
        """
        Enrichit une opportunité avec l'analyse hybride Tradier + Polygon.io

        Args:
            opp: Opportunité à enrichir

        Returns:
            Métriques hybrides enrichies
        """

        try:
            # === DONNÉES TEMPS RÉEL (Tradier) ===

            # Récupération du prix sous-jacent (optimisé)
            if preloaded_underlying_price is not None:
                underlying_price = preloaded_underlying_price
                logger.debug(
                    f"💾 Utilisation prix pré-chargé pour {opp.underlying_symbol}: ${underlying_price}"
                )
            else:
                underlying_price = await self.get_underlying_price(
                    opp.underlying_symbol
                )
                logger.debug(
                    f"📊 Récupération prix individuel pour {opp.underlying_symbol}: ${underlying_price}"
                )

            # Récupération des Greeks depuis l'opportunité (via Enhanced Tradier Client)
            # Les Greeks sont récupérés lors du screening classique initial
            delta = getattr(opp, "delta", None)
            gamma = getattr(opp, "gamma", None)
            theta = getattr(opp, "theta", None)
            vega = getattr(opp, "vega", None)
            rho = getattr(opp, "rho", None)
            implied_volatility = getattr(opp, "implied_volatility", None)

            # Évaluation de la qualité des Greeks
            greeks_available = all([opp.bid > 0, opp.ask > 0, opp.last > 0])

            # Vérifier si on a des Greeks valides
            greeks_count = sum(
                1 for g in [delta, gamma, theta, vega] if g is not None and g != 0
            )

            if greeks_available and greeks_count >= 3 and opp.volume >= 100:
                greeks_quality = "excellent"
            elif greeks_available and greeks_count >= 2 and opp.volume >= 20:
                greeks_quality = "good"
            else:
                greeks_quality = "poor"

            # Score temps réel basé sur Tradier
            realtime_score = self._calculate_realtime_score(opp)

            # === DONNÉES HISTORIQUES (Polygon.io) ===

            historical_data = None
            if self.polygon_enabled:
                historical_data = await self.get_historical_volume_data(
                    opp.underlying_symbol, 30
                )

            # Calcul des métriques historiques
            avg_volume_30d = None
            volume_anomaly_ratio = None
            price_trend_30d = None
            volatility_regime = None
            historical_score = 0.0

            if historical_data:
                avg_volume_30d = historical_data.get("avg_volume")
                price_trend_30d = historical_data.get("price_trend")
                volatility_regime = historical_data.get("volatility_regime")

                # Ratio d'anomalie de volume
                # Note: On compare le volume de l'option au volume moyen de l'underlying
                # Ce n'est pas parfait mais donne une indication de l'activité générale
                if avg_volume_30d and avg_volume_30d > 0:
                    # Approximation: volume option / (volume underlying moyen * 0.01)
                    # Le facteur 0.01 est une heuristique pour normaliser
                    denominator = avg_volume_30d * 0.01
                    if denominator > 0:
                        ratio = opp.volume / denominator
                        # Sanitize infinity/NaN values
                        if not (
                            ratio == float("inf")
                            or ratio == float("-inf")
                            or ratio != ratio
                        ):
                            volume_anomaly_ratio = ratio
                        else:
                            volume_anomaly_ratio = None

                historical_score = self._calculate_historical_score(
                    historical_data, opp
                )

            # === SCORE HYBRIDE COMPOSITE ===

            if historical_data:
                # Pondération hybride: 60% temps réel + 40% historique
                hybrid_score = (realtime_score * 0.6) + (historical_score * 0.4)
                data_freshness = "fresh"
            else:
                # Fallback sur données temps réel seulement
                hybrid_score = realtime_score
                data_freshness = "partial"

            # Construction des métriques
            metrics = HybridMetrics(
                # Temps réel
                current_volume=opp.volume,
                current_oi=opp.open_interest,
                current_price=opp.last,
                greeks_quality=greeks_quality,
                # Greeks temps réel
                delta=delta,
                gamma=gamma,
                theta=theta,
                vega=vega,
                rho=rho,
                implied_volatility=implied_volatility,
                # Historique
                avg_volume_30d=avg_volume_30d,
                volume_anomaly_ratio=volume_anomaly_ratio,
                price_trend_30d=price_trend_30d,
                volatility_regime=volatility_regime,
                # Prix sous-jacent
                underlying_price=underlying_price,
                # Scores
                realtime_score=realtime_score,
                historical_score=historical_score,
                hybrid_score=hybrid_score,
                # Métadonnées
                data_freshness=data_freshness,
                polygon_available=self.polygon_enabled,
            )

            logger.debug(
                f"🔄 Analyse hybride {opp.option_symbol}: score={hybrid_score:.1f}"
            )
            return metrics

        except Exception as e:
            logger.error(f"❌ Erreur enrichissement hybride {opp.option_symbol}: {e}")

            # Fallback sur données Tradier seulement
            return HybridMetrics(
                current_volume=opp.volume,
                current_oi=opp.open_interest,
                current_price=opp.last,
                greeks_quality="poor",
                hybrid_score=self._calculate_realtime_score(opp),
                data_freshness="stale",
            )

    def _calculate_realtime_score(self, opp: OptionsOpportunity) -> float:
        """Calcule le score basé sur les données temps réel Tradier"""
        score = 0.0

        # Volume (0-40 points)
        if opp.volume >= 5000:
            score += 40
        elif opp.volume >= 1000:
            score += 30
        elif opp.volume >= 500:
            score += 20
        elif opp.volume >= 100:
            score += 10

        # Open Interest (0-30 points)
        if opp.open_interest >= 1000:
            score += 30
        elif opp.open_interest >= 500:
            score += 20
        elif opp.open_interest >= 100:
            score += 10

        # Ratio Volume/OI (0-20 points)
        if opp.open_interest > 0:
            vol_oi_ratio = opp.volume / opp.open_interest
            if vol_oi_ratio >= 5:
                score += 20
            elif vol_oi_ratio >= 2:
                score += 15
            elif vol_oi_ratio >= 1:
                score += 10

        # DTE (0-10 points)
        if 3 <= opp.dte <= 14:
            score += 10
        elif 1 <= opp.dte <= 21:
            score += 5

        return min(score, 100.0)

    def _calculate_historical_score(
        self, historical_data: Dict[str, Any], opp: OptionsOpportunity
    ) -> float:
        """Calcule le score basé sur les données historiques Polygon.io"""
        score = 0.0

        # Anomalie de volume underlying (0-40 points)
        avg_volume = historical_data.get("avg_volume", 0)
        if avg_volume > 0:
            # Si le volume underlying est élevé, c'est bon signe pour les options
            volume_ratio = historical_data.get("max_volume", 0) / avg_volume
            if volume_ratio >= 3:
                score += 40
            elif volume_ratio >= 2:
                score += 30
            elif volume_ratio >= 1.5:
                score += 20

        # Tendance de prix (0-30 points)
        price_trend = historical_data.get("price_trend", "neutral")
        if price_trend == "bullish" and opp.option_type.lower() == "call":
            score += 30
        elif price_trend == "bearish" and opp.option_type.lower() == "put":
            score += 30
        elif price_trend != "neutral":
            score += 15  # Tendance contre le type d'option

        # Régime de volatilité (0-30 points)
        volatility_regime = historical_data.get("volatility_regime", "normal")
        if volatility_regime == "high":
            score += 30  # Haute volatilité = opportunités options
        elif volatility_regime == "normal":
            score += 20
        else:
            score += 10

        return min(score, 100.0)

    def get_service_status(self) -> Dict[str, Any]:
        """Retourne le statut du service hybride"""

        # Test de connectivité Polygon.io si disponible
        polygon_status = "disabled"
        if self.polygon_enabled:
            try:
                if hasattr(self.polygon_client, "get_market_status"):
                    market_status = self.polygon_client.get_market_status()
                    polygon_status = "active" if market_status else "error"
                else:
                    polygon_status = "active"
            except Exception as e:
                polygon_status = f"error: {str(e)[:50]}"

        return {
            "hybrid_service": "active",
            "tradier_client": "active",  # Toujours actif via EnhancedTradierClient
            "polygon_client": polygon_status,
            "cache_entries": len(self.cache),
            "polygon_enabled": self.polygon_enabled,
            "architecture": "Tradier (realtime) + Polygon.io (historical)",
        }
