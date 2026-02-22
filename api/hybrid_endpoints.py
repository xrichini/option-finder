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
import asyncio
import threading

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

# Progress state (updated by scan callback, polled by UI)
_scan_progress: dict = {
    "active": False,
    "current": 0,
    "total": 0,
    "symbol": "",
    "phase": "idle",
    "percent": 0,
    "complete": False,
}

# Scan result storage (populated when background scan completes)
_scan_result: dict = {"ready": False, "data": None, "error": None}


@hybrid_router.get("/scan-progress")
async def get_scan_progress():
    """Retourne l'avancement du scan en cours (pour polling UI)."""
    return _scan_progress


@hybrid_router.get("/scan-result")
async def get_scan_result():
    """Retourne le résultat du dernier scan background (prêt quand ready=True)."""
    return _scan_result


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
    max_dte: int = 7
    min_volume: int = 500
    min_oi: int = 100
    min_whale_score: float = 30.0


async def _do_scan_async(symbols, max_dte, min_volume, min_oi, min_whale_score):
    """
    Logique de scan complète (async).  Appelée depuis _run_scan_thread dans son
    propre event-loop afin de ne PAS bloquer l'event-loop principal FastAPI.
    Met à jour _scan_progress au fil du scan et stocke le résultat dans _scan_result.
    """

    async def _progress(current: int, total: int, symbol: str, details: str):
        pct = int(current / total * 100) if total else 0
        _scan_progress.update(
            {
                "active": True,
                "current": current,
                "total": total,
                "symbol": symbol,
                "phase": details,
                "percent": pct,
                "complete": False,
            }
        )
        if total > 0 and current % 10 == 0 and current > 0:
            logger.info(f"\u23f3 Scan: {current}/{total} ({pct}%)")

    try:
        opportunities = await hybrid_service.screen_options_hybrid(
            symbols=symbols,
            option_type="both",
            max_dte=max_dte,
            min_volume=min_volume,
            min_oi=min_oi,
            min_whale_score=min_whale_score,
            enable_ai=False,
            progress_callback=_progress,
        )
    except Exception as exc:
        logger.error(f"❌ Scan background échoué: {exc}")
        _scan_progress.update(
            {"active": False, "complete": True, "phase": "error", "percent": 0}
        )
        _scan_result.update({"ready": False, "data": None, "error": str(exc)})
        return

    # ── Build response ──────────────────────────────────────────────────────
    call_opportunities = [o for o in opportunities if o.get("option_type") == "CALL"]
    put_opportunities = [o for o in opportunities if o.get("option_type") == "PUT"]

    def _type_stats(ops):
        if not ops:
            return {
                "count": 0,
                "avg_hybrid_score": 0,
                "avg_volume": 0,
                "avg_oi": 0,
                "best_opportunity": None,
            }
        return {
            "count": len(ops),
            "avg_hybrid_score": sum(o.get("hybrid_score", 0) for o in ops) / len(ops),
            "avg_volume": sum(o.get("volume", 0) for o in ops) / len(ops),
            "avg_oi": sum(o.get("open_interest", 0) for o in ops) / len(ops),
            "best_opportunity": max(ops, key=lambda x: x.get("hybrid_score", 0)),
        }

    call_stats = _type_stats(call_opportunities)
    put_stats = _type_stats(put_opportunities)

    response = {
        "opportunities": opportunities,
        "total_count": len(opportunities),
        "success": True,
        "timestamp": datetime.now().isoformat(),
        "scan_type": "COMPLETE_CALL_PUT",
        "screening_params": {
            "symbols_count": len(symbols),
            "symbols": symbols,
            "option_type": "both",
            "max_dte": max_dte,
            "min_volume": min_volume,
            "min_oi": min_oi,
            "min_whale_score": min_whale_score,
        },
        "detailed_results": {
            "all_opportunities": opportunities,
            "total_count": len(opportunities),
            "call_opportunities": call_opportunities,
            "put_opportunities": put_opportunities,
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
            "by_symbol": {},
        },
        "data_sources": {
            "tradier": True,
            "polygon": hybrid_service.hybrid_service.polygon_enabled,
            "unusual_whales": True,
            "historical_database": True,
        },
    }

    for symbol in symbols:
        sym_ops = [o for o in opportunities if o.get("underlying_symbol") == symbol]
        sym_calls = [o for o in sym_ops if o.get("option_type") == "CALL"]
        sym_puts = [o for o in sym_ops if o.get("option_type") == "PUT"]
        response["detailed_results"]["by_symbol"][symbol] = {
            "total": len(sym_ops),
            "calls": len(sym_calls),
            "puts": len(sym_puts),
            "best_call": (
                max(sym_calls, key=lambda x: x.get("hybrid_score", 0))
                if sym_calls
                else None
            ),
            "best_put": (
                max(sym_puts, key=lambda x: x.get("hybrid_score", 0))
                if sym_puts
                else None
            ),
        }

    logger.info(
        f"✅ Scan complet terminé: {len(opportunities)} résultats "
        f"({len(call_opportunities)} CALLS, {len(put_opportunities)} PUTS)"
    )

    response = sanitize_floats(response)

    # ── Store result + mark complete ─────────────────────────────────────────
    _scan_result.update({"ready": True, "data": response, "error": None})
    _scan_progress.update(
        {
            "active": False,
            "current": len(symbols),
            "total": len(symbols),
            "symbol": "",
            "phase": "done",
            "percent": 100,
            "complete": True,
        }
    )


def _run_scan_thread(symbols, max_dte, min_volume, min_oi, min_whale_score):
    """
    Wrapper synchrone exécuté dans un thread séparé (BackgroundTasks).
    Crée son propre event-loop pour lancer _do_scan_async sans bloquer
    l'event-loop principal de FastAPI — ce qui permet au polling /scan-progress
    de répondre pendant le scan.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            _do_scan_async(symbols, max_dte, min_volume, min_oi, min_whale_score)
        )
    finally:
        loop.close()


@hybrid_router.post("/scan-all")
async def scan_all_options(
    background_tasks: BackgroundTasks, request: ScanAllRequest = None
):
    """
    Lance un scan complet Call+Put en tâche de fond et retourne immédiatement.
    L'UI doit:
      1. Démarrer en polling GET /api/hybrid/scan-progress jusqu'à complete=true
      2. Récupérer le résultat via GET /api/hybrid/scan-result
    """
    if request is None:
        request = ScanAllRequest()

    symbols = request.symbols or ["AAPL", "TSLA", "NVDA", "SPY", "MSFT"]
    max_dte = request.max_dte
    min_volume = request.min_volume
    min_oi = request.min_oi
    min_whale_score = request.min_whale_score

    logger.info(
        f"🔍 Scan COMPLET Call+Put demandé: {len(symbols)} symboles — lancement background"
    )

    # Réinitialiser l'état avant de lancer
    _scan_result.update({"ready": False, "data": None, "error": None})
    _scan_progress.update(
        {
            "active": True,
            "current": 0,
            "total": len(symbols),
            "symbol": "",
            "phase": "init",
            "percent": 0,
            "complete": False,
        }
    )

    # Lancer le scan dans un thread séparé (ne bloque pas l'event-loop)
    background_tasks.add_task(
        _run_scan_thread, symbols, max_dte, min_volume, min_oi, min_whale_score
    )

    return {"status": "started", "total_symbols": len(symbols)}


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
