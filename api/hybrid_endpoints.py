#!/usr/bin/env python3
"""
Endpoints API FastAPI pour l'architecture hybride Tradier + Polygon.io

Nouveaux endpoints spécialisés pour exploiter l'architecture hybride
et les données enrichies Tradier (temps réel) + Polygon.io (historique)
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from datetime import datetime
import logging
import math

from services.hybrid_screening_service import HybridScreeningService

logger = logging.getLogger(__name__)


def sanitize_floats(obj: Any) -> Any:
    """
    Récursivement sanitize les valeurs float inf/nan
    pour éviter les erreurs JSON
    """
    if isinstance(obj, dict):
        return {k: sanitize_floats(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_floats(item) for item in obj]
    elif isinstance(obj, float):
        # Remplacer inf et nan par None
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    return obj


# Router pour les endpoints hybrides
hybrid_router = APIRouter(prefix="/api/hybrid", tags=["Hybrid Analytics"])

# Service hybride (singleton)
hybrid_service = HybridScreeningService()


# Pydantic models for request validation
class HybridScreeningRequest(BaseModel):
    symbols: List[str]
    option_type: str = "both"
    max_dte: int = 30
    min_volume: int = 100
    min_oi: int = 50
    min_whale_score: float = 60.0
    enable_ai: bool = False


@hybrid_router.get("/status")
async def get_hybrid_status():
    """
    Statut complet de l'architecture hybride

    Returns:
        Informations sur les services Tradier, Polygon.io, bases de données, etc.
    """
    try:
        status = await hybrid_service.get_hybrid_service_status()
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "status": status,
        }
    except Exception as e:
        logger.error(f"Erreur statut hybride: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@hybrid_router.post("/screen")
async def screen_options_hybrid(request: HybridScreeningRequest):
    """
    Screening d'options avec architecture hybride Tradier + Polygon.io

    Args:
        request: Requête de screening contenant:
            - symbols: Liste des symboles à analyser
            - option_type: Type d'options ("call", "put", "both")
            - max_dte: Durée maximum avant expiration
            - min_volume: Volume minimum
            - min_oi: Open Interest minimum
            - min_whale_score: Score whale minimum (hybride)
            - enable_ai: Activer l'analyse IA (expérimental)

    Returns:
        Opportunités enrichies avec métriques hybrides
    """
    try:
        if not request.symbols:
            raise HTTPException(status_code=400, detail="Liste de symboles requise")

        logger.info(f"🔍 Screening hybride demandé: {len(request.symbols)} symboles")

        # Exécution du screening hybride
        opportunities = await hybrid_service.screen_options_hybrid(
            symbols=request.symbols,
            option_type=request.option_type,
            max_dte=request.max_dte,
            min_volume=request.min_volume,
            min_oi=request.min_oi,
            min_whale_score=request.min_whale_score,
            enable_ai=request.enable_ai,
        )

        # Enrichissement de la réponse avec métadonnées
        response = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "screening_params": {
                "symbols_count": len(request.symbols),
                "option_type": request.option_type,
                "max_dte": request.max_dte,
                "min_volume": request.min_volume,
                "min_oi": request.min_oi,
                "min_whale_score": request.min_whale_score,
                "ai_enabled": request.enable_ai,
            },
            "results": {
                "opportunities": opportunities,
                "count": len(opportunities),
                "data_sources": {
                    "tradier": True,
                    "polygon": hybrid_service.hybrid_service.polygon_enabled,
                    "unusual_whales": True,
                    "historical_database": True,
                },
            },
            "analysis_type": "hybrid",
        }

        logger.info(f"✅ Screening hybride terminé: {len(opportunities)} résultats")

        # Sanitize all float values before returning
        response = sanitize_floats(response)

        return response

    except Exception as e:
        logger.error(f"❌ Erreur screening hybride: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@hybrid_router.post("/screen/background")
async def screen_options_hybrid_background(
    background_tasks: BackgroundTasks, request: HybridScreeningRequest
):
    """
    Screening hybride en arrière-plan avec WebSocket updates

    Similaire au screening classique mais avec enrichissement hybride
    """
    try:
        if not request.symbols:
            raise HTTPException(status_code=400, detail="Liste de symboles requise")

        # Générer un ID de session unique
        session_id = f"hybrid_screening_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Démarrer le screening en arrière-plan
        background_tasks.add_task(
            run_hybrid_screening_task,
            session_id=session_id,
            symbols=request.symbols,
            option_type=request.option_type,
            max_dte=request.max_dte,
            min_volume=request.min_volume,
            min_oi=request.min_oi,
            min_whale_score=request.min_whale_score,
            enable_ai=request.enable_ai,
        )

        return {
            "success": True,
            "session_id": session_id,
            "message": f"Screening hybride démarré pour {len(request.symbols)} symboles",
            "analysis_type": "hybrid_background",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Erreur screening hybride background: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ScanAllRequest(BaseModel):
    symbols: Optional[List[str]] = None
    max_dte: int = 30
    min_volume: int = 50
    min_oi: int = 25
    min_whale_score: float = 50.0


@hybrid_router.post("/scan-all")
async def scan_all_options(request: ScanAllRequest = None):
    """
    Scanning complet de TOUS les types d'options (Call ET Put) pour tous les symboles

    Cette fonction garantit un scan exhaustif de toutes les opportunités disponibles,
    avec statistiques détaillées par type d'option.

    Args:
        request: Paramètres de la requête (symbols, max_dte, min_volume, etc.)

    Returns:
        Toutes les opportunités Call + Put avec statistiques détaillées
    """
    try:
        # Utiliser les paramètres de la requête ou des valeurs par défaut
        if request is None:
            request = ScanAllRequest()

        # Si aucun symbole fourni, utiliser une liste par défaut
        symbols = request.symbols or ["AAPL", "TSLA", "NVDA", "SPY", "MSFT"]
        max_dte = request.max_dte
        min_volume = request.min_volume
        min_oi = request.min_oi
        min_whale_score = request.min_whale_score

        logger.info(f"🔍 Scan COMPLET Call+Put demandé: {len(symbols)} symboles")

        # Force option_type="both" pour garantir scan complet
        opportunities = await hybrid_service.screen_options_hybrid(
            symbols=symbols,
            option_type="both",  # Force scan des deux types
            max_dte=max_dte,
            min_volume=min_volume,
            min_oi=min_oi,
            min_whale_score=min_whale_score,
            enable_ai=False,  # Plus rapide sans IA
        )

        # Statistiques par type d'option
        call_opportunities = [
            opp for opp in opportunities if opp.get("option_type") == "CALL"
        ]
        put_opportunities = [
            opp for opp in opportunities if opp.get("option_type") == "PUT"
        ]

        # Calcul de métriques par type
        def calculate_type_stats(type_opportunities):
            if not type_opportunities:
                return {
                    "count": 0,
                    "avg_hybrid_score": 0,
                    "avg_volume": 0,
                    "avg_oi": 0,
                    "best_opportunity": None,
                }

            return {
                "count": len(type_opportunities),
                "avg_hybrid_score": sum(
                    o.get("hybrid_score", 0) for o in type_opportunities
                )
                / len(type_opportunities),
                "avg_volume": sum(o.get("volume", 0) for o in type_opportunities)
                / len(type_opportunities),
                "avg_oi": sum(o.get("open_interest", 0) for o in type_opportunities)
                / len(type_opportunities),
                "best_opportunity": max(
                    type_opportunities, key=lambda x: x.get("hybrid_score", 0)
                ),
            }

        call_stats = calculate_type_stats(call_opportunities)
        put_stats = calculate_type_stats(put_opportunities)

        # Réponse dans le format attendu par l'interface JavaScript
        response = {
            "opportunities": opportunities,  # Format attendu par l'interface
            "total_count": len(opportunities),
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "scan_type": "COMPLETE_CALL_PUT",
            "screening_params": {
                "symbols_count": len(symbols),
                "symbols": symbols,
                "option_type": "both",  # Confirmé
                "max_dte": max_dte,
                "min_volume": min_volume,
                "min_oi": min_oi,
                "min_whale_score": min_whale_score,
            },
            "detailed_results": {
                "all_opportunities": opportunities,
                "total_count": len(opportunities),
                # Séparation Call vs Put
                "call_opportunities": call_opportunities,
                "put_opportunities": put_opportunities,
                # Statistiques comparatives
                "statistics": {
                    "calls": call_stats,
                    "puts": put_stats,
                    "call_put_ratio": (
                        len(call_opportunities) / len(put_opportunities)
                        if len(put_opportunities) > 0
                        else None
                    ),
                    "best_overall": (
                        max(opportunities, key=lambda x: x.get("hybrid_score", 0))
                        if opportunities
                        else None
                    ),
                },
                # Distribution par symbole
                "by_symbol": {},
            },
            "data_sources": {
                "tradier": True,
                "polygon": hybrid_service.hybrid_service.polygon_enabled,
                "unusual_whales": True,
                "historical_database": True,
            },
        }

        # Ajout statistiques par symbole
        for symbol in symbols:
            symbol_ops = [
                opp for opp in opportunities if opp.get("underlying_symbol") == symbol
            ]
            symbol_calls = [
                opp for opp in symbol_ops if opp.get("option_type") == "CALL"
            ]
            symbol_puts = [opp for opp in symbol_ops if opp.get("option_type") == "PUT"]

            response["detailed_results"]["by_symbol"][symbol] = {
                "total": len(symbol_ops),
                "calls": len(symbol_calls),
                "puts": len(symbol_puts),
                "best_call": (
                    max(symbol_calls, key=lambda x: x.get("hybrid_score", 0))
                    if symbol_calls
                    else None
                ),
                "best_put": (
                    max(symbol_puts, key=lambda x: x.get("hybrid_score", 0))
                    if symbol_puts
                    else None
                ),
            }

        logger.info(
            f"✅ Scan complet terminé: {len(opportunities)} résultats ({len(call_opportunities)} CALLS, {len(put_opportunities)} PUTS)"
        )

        # Sanitize all float values before returning
        response = sanitize_floats(response)

        return response

    except Exception as e:
        logger.error(f"❌ Erreur scan complet Call+Put: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@hybrid_router.get("/recommendations")
async def get_hybrid_recommendations(
    max_results: int = Query(default=10, ge=1, le=50),
    symbols: Optional[List[str]] = Query(default=None),
):
    """
    Recommandations de trading basées sur l'analyse hybride

    Args:
        max_results: Nombre maximum de recommandations (1-50)
        symbols: Liste optionnelle de symboles (auto-détection si omis)

    Returns:
        Recommandations enrichies avec scores de confiance, niveaux de risque, etc.
    """
    try:
        logger.info(f"🤖 Génération de {max_results} recommandations hybrides")

        recommendations = await hybrid_service.get_hybrid_recommendations(
            symbols=symbols, max_results=max_results
        )

        # Calcul de statistiques sur les recommandations
        if recommendations:
            confidence_scores = [r.get("confidence_score", 0) for r in recommendations]
            avg_confidence = sum(confidence_scores) / len(confidence_scores)

            recommendation_types = {}
            for r in recommendations:
                rec_type = r.get("recommendation_type", "UNKNOWN")
                recommendation_types[rec_type] = (
                    recommendation_types.get(rec_type, 0) + 1
                )
        else:
            avg_confidence = 0
            recommendation_types = {}

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "recommendations": recommendations,
            "count": len(recommendations),
            "statistics": {
                "average_confidence": round(avg_confidence, 2),
                "recommendation_types": recommendation_types,
                "data_sources_active": {
                    "tradier": True,
                    "polygon": hybrid_service.hybrid_service.polygon_enabled,
                    "unusual_whales": True,
                    "historical_database": True,
                },
            },
            "analysis_type": "hybrid_recommendations",
        }

    except Exception as e:
        logger.error(f"❌ Erreur recommandations hybrides: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@hybrid_router.get("/data-sources")
async def get_data_sources_info():
    """
    Informations détaillées sur les sources de données hybrides
    """
    try:
        status = await hybrid_service.get_hybrid_service_status()

        # Test de connectivité des sources
        sources_info = {
            "tradier": {
                "status": status.get("tradier_client", "unknown"),
                "type": "realtime",
                "description": "Données options temps réel, Greeks, Open Interest",
                "rate_limit": "Pas de limite stricte",
                "cost": "Gratuit",
            },
            "polygon": {
                "status": status.get("polygon_client", "unknown"),
                "enabled": status.get("polygon_enabled", False),
                "type": "historical",
                "description": "Données historiques, tendances, backtesting",
                "rate_limit": "5 requêtes/min (gratuit)",
                "cost": "Gratuit/Payant",
            },
            "unusual_whales": {
                "status": "active",
                "type": "analysis",
                "description": "Algorithmes de détection d'anomalies",
                "rate_limit": "Aucune (local)",
                "cost": "Gratuit",
            },
            "historical_database": {
                "status": "active",
                "type": "storage",
                "description": "Base SQLite pour historique et tendances",
                "rate_limit": "Aucune (local)",
                "cost": "Gratuit",
            },
        }

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "data_sources": sources_info,
            "cache_stats": {"entries": status.get("cache_entries", 0)},
            "architecture": status.get("architecture", "Hybrid"),
        }

    except Exception as e:
        logger.error(f"❌ Erreur info sources de données: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@hybrid_router.get("/historical/{symbol}")
async def get_symbol_historical_analysis(
    symbol: str, days: int = Query(default=30, ge=1, le=90)
):
    """
    Analyse historique détaillée d'un symbole via Polygon.io

    Args:
        symbol: Symbole du titre
        days: Nombre de jours d'historique (1-90)

    Returns:
        Analyse historique détaillée si Polygon.io est disponible
    """
    try:
        if not hybrid_service.hybrid_service.polygon_enabled:
            raise HTTPException(
                status_code=503,
                detail="Polygon.io non disponible - service historique indisponible",
            )

        logger.info(f"📊 Analyse historique demandée: {symbol} ({days} jours)")

        # Récupération des données historiques
        historical_data = (
            await hybrid_service.hybrid_service.get_historical_volume_data(
                symbol=symbol.upper(), days=days
            )
        )

        if not historical_data:
            raise HTTPException(
                status_code=404,
                detail=f"Données historiques non disponibles pour {symbol}",
            )

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol.upper(),
            "period_days": days,
            "historical_analysis": historical_data,
            "data_source": "polygon.io",
            "cache_used": True,  # Données peuvent venir du cache
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur analyse historique {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@hybrid_router.get("/underlying-price/{symbol}")
async def get_underlying_price(symbol: str):
    """
    Récupère le prix actuel du sous-jacent via Tradier

    Args:
        symbol: Symbole du titre sous-jacent

    Returns:
        Prix actuel et informations du sous-jacent
    """
    try:
        # Utiliser le client Tradier pour récupérer le prix actuel
        from data.enhanced_tradier_client import EnhancedTradierClient

        tradier_client = EnhancedTradierClient(api_token="", sandbox=None)

        # Récupération du quote du sous-jacent
        quote_data = tradier_client.get_quote(symbol.upper())

        if not quote_data:
            raise HTTPException(
                status_code=404, detail=f"Prix non disponible pour {symbol}"
            )

        # Formatage de la réponse
        return {
            "success": True,
            "symbol": symbol.upper(),
            "price": quote_data.get("last", 0),
            "bid": quote_data.get("bid", 0),
            "ask": quote_data.get("ask", 0),
            "change": quote_data.get("change", 0),
            "change_percent": quote_data.get("change_percentage", 0),
            "volume": quote_data.get("volume", 0),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Erreur prix sous-jacent {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Tâche de screening hybride en arrière-plan
async def run_hybrid_screening_task(
    session_id: str,
    symbols: List[str],
    option_type: str = "both",
    max_dte: int = 30,
    min_volume: int = 100,
    min_oi: int = 50,
    min_whale_score: float = 60.0,
    enable_ai: bool = False,
):
    """
    Tâche de screening hybride en arrière-plan

    Note: Cette fonction devrait idéalement intégrer les WebSocket updates
    comme dans l'app.py principal, mais pour l'instant elle fait le traitement
    """

    try:
        logger.info(f"🚀 Démarrage tâche hybride {session_id}")

        # Callback de progression (pour l'instant juste logging)
        async def progress_callback(
            current: int, total: int, symbol: str, details: str
        ):
            progress_pct = (current / total) * 100 if total > 0 else 0
            logger.info(f"📈 {session_id}: {progress_pct:.1f}% - {symbol} - {details}")

        # Exécution du screening hybride
        results = await hybrid_service.screen_options_hybrid(
            symbols=symbols,
            option_type=option_type,
            max_dte=max_dte,
            min_volume=min_volume,
            min_oi=min_oi,
            min_whale_score=min_whale_score,
            enable_ai=enable_ai,
            progress_callback=progress_callback,
        )

        # Pour l'instant, juste logging des résultats
        # Dans une implémentation complète, on enverrait via WebSocket
        logger.info(f"✅ Tâche hybride {session_id} terminée: {len(results)} résultats")

        # TODO: Intégrer WebSocket broadcasting comme dans app.py
        # await manager.broadcast({
        #     "type": "hybrid_screening_completed",
        #     "session_id": session_id,
        #     "results": results,
        #     "count": len(results)
        # })

    except Exception as e:
        logger.error(f"❌ Erreur tâche hybride {session_id}: {e}")
        # TODO: Envoyer erreur via WebSocket
        # await manager.broadcast({
        #     "type": "hybrid_screening_error",
        #     "session_id": session_id,
        #     "error": str(e)
        # })
