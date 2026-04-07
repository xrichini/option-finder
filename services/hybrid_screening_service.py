#!/usr/bin/env python3
"""
Service de screening hybride intégrant Tradier + Polygon.io

Extension du ScreeningService existant pour utiliser l'architecture hybride
recommandée dans WARP.md
"""

from typing import List, Dict, Any, Optional, Callable
import logging
from datetime import datetime

import asyncio
from services.screening_service import ScreeningService
from services.hybrid_data_service import HybridDataService

logger = logging.getLogger(__name__)


class HybridScreeningService(ScreeningService):
    """Service de screening enrichi avec données hybrides Tradier + Polygon.io"""

    def __init__(self):
        super().__init__()
        self.hybrid_service = HybridDataService(enable_polygon=True)
        logger.info("🔄 Service de screening hybride initialisé")

    async def screen_options_hybrid(
        self,
        symbols: List[str],
        option_type: str = "both",
        max_dte: int = 30,
        min_volume: int = 100,
        min_oi: int = 50,
        min_whale_score: float = 60.0,
        enable_ai: bool = False,
        progress_callback: Optional[Callable[[int, int, str, str], None]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Screening hybride avec enrichissement Tradier + Polygon.io

        Args:
            symbols: Liste des symboles à analyser
            option_type: Type d'options ("call", "put", "both")
            max_dte: Durée max avant expiration
            min_volume: Volume minimum
            min_oi: Open Interest minimum
            min_whale_score: Score whale minimum
            enable_ai: Activer l'analyse IA
            progress_callback: Callback de progression (current, total, symbol, details)

        Returns:
            Liste des opportunités enrichies avec métriques hybrides
        """

        try:
            # Phase 1: Screening classique pour obtenir les opportunités de base
            logger.info(f"🔍 Démarrage screening hybride sur {len(symbols)} symboles")

            if progress_callback:
                await progress_callback(
                    0, len(symbols), "INIT", "Initialisation du screening hybride..."
                )

            # Mettre à jour les paramètres du service de base
            # Note: ConfigService n'a pas update_screening_params, on passe directement les paramètres

            # Screening de base avec callback adapté
            async def base_progress_callback(current: int, total: int, message: str):
                if progress_callback:
                    symbol = (
                        message.split()[-1].replace("...", "")
                        if "Analyse" in message
                        else "N/A"
                    )
                    await progress_callback(
                        current, total, symbol, f"Screening base: {message}"
                    )

            base_opportunities = await self.screen_options_classic(
                symbols, base_progress_callback
            )

            if not base_opportunities:
                logger.info("Aucune opportunité trouvée lors du screening de base")
                return []

            logger.info(f"📊 {len(base_opportunities)} opportunités de base trouvées")

            # Phase 2: Préparation de l'enrichissement hybride optimisé
            if progress_callback:
                await progress_callback(
                    len(base_opportunities),
                    len(base_opportunities),
                    "PREP",
                    "Préparation enrichissement hybride optimisé...",
                )

            # Récupération optimisée de TOUS les prix sous-jacents en 1 seul appel API
            underlying_symbols = list(
                set(opp.underlying_symbol for opp in base_opportunities)
            )
            logger.info(
                f"🚀 Optimisation: Récupération de {len(underlying_symbols)} prix sous-jacents en 1 appel"
            )

            underlying_prices = (
                await self.hybrid_service.get_multiple_underlying_prices(
                    underlying_symbols
                )
            )
            logger.info(f"✅ Prix récupérés pour {len(underlying_prices)} symboles")

            # ── Quota guard: enrich FMP only for top-N unique symbols ──────────
            # (FMP free tier = 250 req/day; profile+metrics = 2 calls/symbol)
            _FMP_ENRICH_LIMIT = 50
            _sorted_for_fmp = sorted(
                base_opportunities, key=lambda o: o.whale_score, reverse=True
            )
            fmp_symbols: list[str] = []
            _seen_fmp: set[str] = set()
            for _o in _sorted_for_fmp:
                _sym = _o.underlying_symbol.upper()
                if _sym not in _seen_fmp:
                    _seen_fmp.add(_sym)
                    fmp_symbols.append(_sym)
                if len(fmp_symbols) >= _FMP_ENRICH_LIMIT:
                    break
            logger.info(
                f"💰 FMP quota guard: enriching {len(fmp_symbols)}/{len(underlying_symbols)} "
                f"unique symbols (top-{_FMP_ENRICH_LIMIT} by whale_score)"
            )

            # Pre-fetch FMP data concurrently (non-bloquant — dict vide si indisponible)
            # Lazy import to avoid circular dependencies
            from api.earnings_utils import get_earnings_map
            from api.fmp_enrichment import (
                get_profiles,
                get_key_metrics,
                get_insider_activity,
            )

            (
                earnings_map,
                profile_map,
                metrics_map,
                insider_map,
            ) = await asyncio.gather(
                get_earnings_map(days=7),
                get_profiles(fmp_symbols),
                get_key_metrics(fmp_symbols),
                get_insider_activity(fmp_symbols),
            )
            logger.info(
                f"📅 Earnings: {len(earnings_map)} | "
                f"📊 Profiles: {len(profile_map)} | "
                f"📈 Metrics: {len(metrics_map)} | "
                f"👤 Insider: {len(insider_map)}"
            )

            # Phase 3: Enrichissement hybride avec prix pré-chargés
            enriched_opportunities = []

            for i, opp in enumerate(base_opportunities):
                if progress_callback:
                    await progress_callback(
                        i,
                        len(base_opportunities),
                        opp.underlying_symbol,
                        f"Enrichissement hybride {opp.option_symbol}",
                    )

                try:
                    # Récupération du prix pré-chargé
                    underlying_price = underlying_prices.get(
                        opp.underlying_symbol.upper()
                    )

                    # Enrichissement avec données hybrides (prix déjà disponible)
                    hybrid_metrics = (
                        await self.hybrid_service.enrich_opportunity_with_hybrid_data(
                            opp, preloaded_underlying_price=underlying_price
                        )
                    )

                    # Création de l'opportunité enrichie avec affichage Call/Put amélioré
                    option_type_display = (
                        opp.option_type.upper() if opp.option_type else "UNKNOWN"
                    )

                    enriched_opp = {
                        # Données de base avec affichage amélioré
                        "option_symbol": opp.option_symbol,
                        "underlying_symbol": opp.underlying_symbol,
                        "option_type": option_type_display,  # CALL ou PUT en majuscules
                        "option_type_emoji": (
                            "📈" if option_type_display == "CALL" else "📉"
                        ),  # Emoji visuel
                        "strike": opp.strike,
                        "expiration": getattr(opp, "expiration", None)
                        or getattr(opp, "expiration_date", None),
                        "dte": opp.dte,
                        # Prix et volumes de base
                        "last": opp.last,
                        "bid": opp.bid,
                        "ask": opp.ask,
                        "volume": opp.volume,
                        "open_interest": opp.open_interest,
                        # Scores originaux
                        "whale_score": opp.whale_score,
                        "ai_recommendation": getattr(opp, "ai_recommendation", None),
                        # === ENRICHISSEMENT HYBRIDE ===
                        # Métriques temps réel (Tradier)
                        "realtime_score": hybrid_metrics.realtime_score,
                        "greeks_quality": hybrid_metrics.greeks_quality,
                        # Greeks temps réel (Tradier)
                        "delta": hybrid_metrics.delta,
                        "gamma": hybrid_metrics.gamma,
                        "theta": hybrid_metrics.theta,
                        "vega": hybrid_metrics.vega,
                        "rho": hybrid_metrics.rho,
                        "implied_volatility": hybrid_metrics.implied_volatility,
                        # Métriques historiques (Polygon.io)
                        "historical_score": hybrid_metrics.historical_score,
                        "avg_volume_30d": hybrid_metrics.avg_volume_30d,
                        "volume_anomaly_ratio": hybrid_metrics.volume_anomaly_ratio,
                        "price_trend_30d": hybrid_metrics.price_trend_30d,
                        "volatility_regime": hybrid_metrics.volatility_regime,
                        # Prix sous-jacent pour moneyness
                        "underlying_price": hybrid_metrics.underlying_price,
                        # Score composite final
                        "hybrid_score": hybrid_metrics.hybrid_score,
                        "data_freshness": hybrid_metrics.data_freshness,
                        "polygon_available": hybrid_metrics.polygon_available,
                        # Métadonnées d'analyse
                        "analysis_type": "hybrid",
                        "timestamp": datetime.now().isoformat(),
                        "analysis_timestamp": datetime.now().isoformat(),
                        "tradier_enabled": True,
                        "polygon_enabled": self.hybrid_service.polygon_enabled,
                        # Champs enrichis repropagés depuis l'opportunité de base
                        "expiration_date": getattr(opp, "expiration_date", None)
                        or getattr(opp, "expiration", None),
                        "vol_oi_ratio": getattr(opp, "vol_oi_ratio", 0),
                        "change_pct": getattr(opp, "change_pct", 0),
                        "stock_volume": getattr(opp, "stock_volume", 0),
                        "sector": (
                            profile_map.get(opp.underlying_symbol.upper(), {}).get(
                                "sector"
                            )
                            or getattr(opp, "sector", "")
                        ),
                        "industry": profile_map.get(
                            opp.underlying_symbol.upper(), {}
                        ).get("industry", ""),
                        "beta": profile_map.get(opp.underlying_symbol.upper(), {}).get(
                            "beta"
                        ),
                        "cap_label": profile_map.get(
                            opp.underlying_symbol.upper(), {}
                        ).get("cap_label", ""),
                        "pe_ratio": metrics_map.get(
                            opp.underlying_symbol.upper(), {}
                        ).get("pe_ratio"),
                        "insider_signal": insider_map.get(
                            opp.underlying_symbol.upper(), {}
                        ).get("signal", "neutral"),
                        "insider_icon": insider_map.get(
                            opp.underlying_symbol.upper(), {}
                        ).get("icon", "⚪"),
                        "insider_buys": insider_map.get(
                            opp.underlying_symbol.upper(), {}
                        ).get("buys", 0),
                        "insider_sells": insider_map.get(
                            opp.underlying_symbol.upper(), {}
                        ).get("sells", 0),
                        "moneyness": getattr(opp, "moneyness", ""),
                        "moneyness_pct": getattr(opp, "moneyness_pct", 0),
                        # Earnings calendar
                        "earnings_soon": opp.underlying_symbol.upper() in earnings_map,
                        "earnings_date": earnings_map.get(
                            opp.underlying_symbol.upper(), {}
                        ).get("date"),
                        "earnings_timing": earnings_map.get(
                            opp.underlying_symbol.upper(), {}
                        ).get("timing", "--"),
                        "earnings_flag": (
                            "⚡"
                            if opp.underlying_symbol.upper() in earnings_map
                            else ""
                        ),
                    }

                    enriched_opportunities.append(enriched_opp)

                except Exception as e:
                    logger.warning(f"❌ Erreur enrichissement {opp.option_symbol}: {e}")

                    # Fallback: opportunité de base sans enrichissement avec affichage amélioré
                    option_type_display = (
                        opp.option_type.upper() if opp.option_type else "UNKNOWN"
                    )

                    fallback_opp = {
                        "option_symbol": opp.option_symbol,
                        "underlying_symbol": opp.underlying_symbol,
                        "option_type": option_type_display,  # CALL ou PUT en majuscules
                        "option_type_emoji": (
                            "📈" if option_type_display == "CALL" else "📉"
                        ),  # Emoji visuel
                        "strike": opp.strike,
                        "expiration": getattr(opp, "expiration", None)
                        or getattr(opp, "expiration_date", None),
                        "dte": opp.dte,
                        "last": opp.last,
                        "bid": opp.bid,
                        "ask": opp.ask,
                        "volume": opp.volume,
                        "open_interest": opp.open_interest,
                        "whale_score": opp.whale_score,
                        "hybrid_score": opp.whale_score,  # Fallback au score original
                        # Greeks fallback (depuis l'opportunité de base si disponible)
                        "delta": getattr(opp, "delta", None),
                        "gamma": getattr(opp, "gamma", None),
                        "theta": getattr(opp, "theta", None),
                        "vega": getattr(opp, "vega", None),
                        "rho": getattr(opp, "rho", None),
                        "implied_volatility": getattr(opp, "implied_volatility", None),
                        "data_freshness": "stale",
                        "analysis_type": "fallback",
                        "error": str(e),
                        # Champs enrichis repropagés depuis l'opportunité de base
                        "expiration_date": getattr(opp, "expiration_date", None)
                        or getattr(opp, "expiration", None),
                        "vol_oi_ratio": getattr(opp, "vol_oi_ratio", 0),
                        "change_pct": getattr(opp, "change_pct", 0),
                        "stock_volume": getattr(opp, "stock_volume", 0),
                        "sector": (
                            profile_map.get(opp.underlying_symbol.upper(), {}).get(
                                "sector"
                            )
                            or getattr(opp, "sector", "")
                        ),
                        "industry": profile_map.get(
                            opp.underlying_symbol.upper(), {}
                        ).get("industry", ""),
                        "beta": profile_map.get(opp.underlying_symbol.upper(), {}).get(
                            "beta"
                        ),
                        "cap_label": profile_map.get(
                            opp.underlying_symbol.upper(), {}
                        ).get("cap_label", ""),
                        "pe_ratio": metrics_map.get(
                            opp.underlying_symbol.upper(), {}
                        ).get("pe_ratio"),
                        "insider_signal": insider_map.get(
                            opp.underlying_symbol.upper(), {}
                        ).get("signal", "neutral"),
                        "insider_icon": insider_map.get(
                            opp.underlying_symbol.upper(), {}
                        ).get("icon", "⚪"),
                        "insider_buys": insider_map.get(
                            opp.underlying_symbol.upper(), {}
                        ).get("buys", 0),
                        "insider_sells": insider_map.get(
                            opp.underlying_symbol.upper(), {}
                        ).get("sells", 0),
                        "moneyness": getattr(opp, "moneyness", ""),
                        "moneyness_pct": getattr(opp, "moneyness_pct", 0),
                        # Earnings calendar
                        "earnings_soon": opp.underlying_symbol.upper() in earnings_map,
                        "earnings_date": earnings_map.get(
                            opp.underlying_symbol.upper(), {}
                        ).get("date"),
                        "earnings_timing": earnings_map.get(
                            opp.underlying_symbol.upper(), {}
                        ).get("timing", "--"),
                        "earnings_flag": (
                            "⚡"
                            if opp.underlying_symbol.upper() in earnings_map
                            else ""
                        ),
                    }

                    enriched_opportunities.append(fallback_opp)

            # Phase 4: Tri et filtrage final
            if progress_callback:
                await progress_callback(
                    len(base_opportunities),
                    len(base_opportunities),
                    "FINAL",
                    "Tri et filtrage final...",
                )

            # Filtrage par type d'option
            if option_type != "both":
                enriched_opportunities = [
                    opp
                    for opp in enriched_opportunities
                    if opp["option_type"].lower() == option_type.lower()
                ]

            # Tri par score hybride
            enriched_opportunities.sort(key=lambda x: x["hybrid_score"], reverse=True)

            # Filtrage par score minimum
            filtered_opportunities = [
                opp
                for opp in enriched_opportunities
                if opp["hybrid_score"] >= min_whale_score
            ]

            logger.info("🎯 Screening hybride terminé:")
            logger.info(f"   Opportunités de base: {len(base_opportunities)}")
            logger.info(f"   Opportunités enrichies: {len(enriched_opportunities)}")
            logger.info(f"   Opportunités filtrées: {len(filtered_opportunities)}")
            logger.info(
                f"   Polygon.io actif: {'✅' if self.hybrid_service.polygon_enabled else '❌'}"
            )

            return filtered_opportunities

        except Exception as e:
            logger.error(f"❌ Erreur screening hybride: {e}")
            raise

    async def get_hybrid_service_status(self) -> Dict[str, Any]:
        """Retourne le statut complet du service hybride"""

        base_status = {
            "screening_service": "active",
            "tradier_client": "active",
            "unusual_whales_service": "active",
        }

        hybrid_status = self.hybrid_service.get_service_status()

        return {
            **base_status,
            **hybrid_status,
            "service_type": "hybrid_screening",
            "architecture": "ScreeningService + HybridDataService (Tradier + Polygon.io)",
        }

    async def get_hybrid_recommendations(
        self, symbols: Optional[List[str]] = None, max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Génère des recommandations basées sur l'analyse hybride

        Args:
            symbols: Liste des symboles (optionnel, auto-détection si None)
            max_results: Nombre max de recommandations

        Returns:
            Liste des recommandations enrichies
        """

        try:
            # Auto-détection des symboles si non fournis
            if not symbols:
                symbol_params = self.config_service.get_symbol_loading_params()
                symbols = await self.get_symbol_suggestions(
                    min_market_cap=symbol_params.get("min_market_cap", 1e9),
                    min_volume=symbol_params.get("min_stock_volume", 1e6),
                )[
                    :50
                ]  # Limiter à 50 symboles pour l'analyse

            logger.info(
                f"🤖 Génération de recommandations hybrides sur {len(symbols)} symboles"
            )

            # Screening hybride avec critères optimisés pour les recommandations
            opportunities = await self.screen_options_hybrid(
                symbols=symbols,
                option_type="both",
                max_dte=21,  # Focus sur options courtes
                min_volume=200,  # Volume plus élevé
                min_oi=100,
                min_whale_score=70.0,  # Score plus sélectif
                enable_ai=False,  # Pour l'instant
            )

            if not opportunities:
                return []

            # Enrichissement des recommandations
            recommendations = []
            for opp in opportunities[:max_results]:

                # Calcul du score de confiance basé sur les métriques hybrides
                confidence_score = self._calculate_confidence_score(opp)

                # Génération de la recommandation
                recommendation = {
                    **opp,  # Inclut toutes les données hybrides
                    # Enrichissements pour recommandation
                    "confidence_score": confidence_score,
                    "recommendation_type": self._determine_recommendation_type(opp),
                    "risk_level": self._assess_risk_level(opp),
                    "target_profit": self._estimate_target_profit(opp),
                    "stop_loss": self._suggest_stop_loss(opp),
                    # Contexte historique si disponible
                    "historical_context": self._generate_historical_context(opp),
                    # Métadonnées
                    "recommendation_timestamp": datetime.now().isoformat(),
                    "data_sources": self._get_data_sources_info(opp),
                }

                recommendations.append(recommendation)

            # Tri final par score de confiance
            recommendations.sort(key=lambda x: x["confidence_score"], reverse=True)

            logger.info(f"✅ Généré {len(recommendations)} recommandations hybrides")
            return recommendations

        except Exception as e:
            logger.error(f"❌ Erreur génération recommandations hybrides: {e}")
            return []

    def _calculate_confidence_score(self, opp: Dict[str, Any]) -> float:
        """Calcule un score de confiance basé sur les métriques hybrides"""

        score = 0.0
        max_score = 100.0

        # Score hybride (40% du total)
        score += (opp.get("hybrid_score", 0) / 100) * 40

        # Qualité des données (20% du total)
        data_quality = 0
        if opp.get("data_freshness") == "fresh":
            data_quality += 20
        elif opp.get("data_freshness") == "partial":
            data_quality += 10

        if opp.get("polygon_available"):
            data_quality += 5

        score += min(data_quality, 20)

        # Volume anomaly (20% du total)
        volume_anomaly = opp.get("volume_anomaly_ratio", 0)
        if volume_anomaly and volume_anomaly > 0:
            if volume_anomaly >= 5:
                score += 20
            elif volume_anomaly >= 2:
                score += 15
            elif volume_anomaly >= 1:
                score += 10

        # Alignement tendance/type option (20% du total)
        price_trend = opp.get("price_trend_30d", "neutral")
        option_type = opp.get("option_type", "").lower()

        if (price_trend == "bullish" and option_type == "call") or (
            price_trend == "bearish" and option_type == "put"
        ):
            score += 20
        elif price_trend != "neutral":
            score += 10

        return min(score, max_score)

    def _determine_recommendation_type(self, opp: Dict[str, Any]) -> str:
        """Détermine le type de recommandation"""

        confidence = self._calculate_confidence_score(opp)
        hybrid_score = opp.get("hybrid_score", 0)
        volume_anomaly = opp.get("volume_anomaly_ratio", 0)

        if confidence >= 80 and hybrid_score >= 85:
            return "STRONG_BUY"
        elif confidence >= 70 and hybrid_score >= 75:
            return "BUY"
        elif confidence >= 60 and volume_anomaly and volume_anomaly >= 3:
            return "SPECULATIVE_BUY"
        elif confidence >= 50:
            return "WATCH"
        else:
            return "NEUTRAL"

    def _assess_risk_level(self, opp: Dict[str, Any]) -> str:
        """Évalue le niveau de risque"""

        dte = opp.get("dte", 30)
        volatility_regime = opp.get("volatility_regime", "normal")
        greeks_quality = opp.get("greeks_quality", "poor")

        if dte <= 7 or volatility_regime == "high" or greeks_quality == "poor":
            return "HIGH"
        elif dte <= 14 or volatility_regime == "normal":
            return "MEDIUM"
        else:
            return "LOW"

    def _estimate_target_profit(self, opp: Dict[str, Any]) -> Optional[float]:
        """Estime un objectif de profit (pourcentage)"""

        confidence = self._calculate_confidence_score(opp)
        risk_level = self._assess_risk_level(opp)

        if risk_level == "HIGH":
            return confidence * 2  # Potentiel élevé mais risqué
        elif risk_level == "MEDIUM":
            return confidence * 1.5
        else:
            return confidence * 1.0

    def _suggest_stop_loss(self, opp: Dict[str, Any]) -> Optional[float]:
        """Suggère un stop loss (pourcentage de perte)"""

        risk_level = self._assess_risk_level(opp)

        if risk_level == "HIGH":
            return -50.0  # Stop loss agressif
        elif risk_level == "MEDIUM":
            return -30.0
        else:
            return -20.0

    def _generate_historical_context(self, opp: Dict[str, Any]) -> str:
        """Génère un contexte historique"""

        context_parts = []

        # Tendance de prix
        price_trend = opp.get("price_trend_30d")
        if price_trend:
            context_parts.append(f"Tendance 30j: {price_trend}")

        # Volume anomaly
        volume_anomaly = opp.get("volume_anomaly_ratio")
        if volume_anomaly and volume_anomaly > 1:
            context_parts.append(f"Volume {volume_anomaly:.1f}x la moyenne")

        # Volatilité
        volatility_regime = opp.get("volatility_regime")
        if volatility_regime:
            context_parts.append(f"Volatilité: {volatility_regime}")

        return " | ".join(context_parts) if context_parts else "Contexte limité"

    def _get_data_sources_info(self, opp: Dict[str, Any]) -> Dict[str, bool]:
        """Info sur les sources de données utilisées"""

        return {
            "tradier": True,  # Toujours actif
            "polygon": opp.get("polygon_available", False),
            "unusual_whales": True,  # Analyse UW toujours active
            "historical_database": True,  # Base SQLite
        }
