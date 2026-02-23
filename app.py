#!/usr/bin/env python3
"""
FastAPI Options Screening Application
Architecture moderne remplaçant Streamlit
"""

# ⚠️ Charger les variables d'environnement EN PREMIER avant tout import métier
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import json
from typing import List
from datetime import datetime
import logging

# Imports de notre logique métier (sans dépendances UI)
from services.screening_service import ScreeningService
from services.config_service import ConfigService
from models.api_models import (
    ScreeningRequest,
    ConfigResponse,
    SymbolRequest,
)

# Import des endpoints hybrides, short interest et filtres avancés
from api.hybrid_endpoints import hybrid_router
from api.short_interest_endpoints import short_interest_router
from api.filtering_endpoints import filtering_router
from api.universe_endpoints import universe_router
from api.earnings_endpoints import earnings_router
from api.fmp_enrichment import fmp_enrichment_router
from api.quotes_refresh import quotes_refresh_router
from api.daemon_endpoints import daemon_router

# Persistence
from services.persistence_service import persistence_service
from services.history_service import history_service

# Sécurité (API Key + Rate Limiting)
from services.security_service import setup_security

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialisation FastAPI
app = FastAPI(
    title="🐋 Options Whale Screener",
    description="Système de détection d'opportunités options avec IA",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS pour développement
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir les fichiers statiques (CSS, JS, images)
try:
    app.mount("/static", StaticFiles(directory="ui/static"), name="static")
    app.mount("/ui", StaticFiles(directory="ui"), name="ui")
except Exception as e:
    logger.warning(f"Could not mount static files: {e}")

# Services
screening_service = ScreeningService()
config_service = ConfigService()

# Inclusion des routers hybrides et short interest
app.include_router(hybrid_router)
app.include_router(short_interest_router)
app.include_router(filtering_router)
app.include_router(universe_router)
app.include_router(earnings_router)
app.include_router(fmp_enrichment_router)
app.include_router(quotes_refresh_router)
app.include_router(daemon_router)

# Appliquer la sécurité (API Key middleware + rate limiting)
setup_security(app)


# Gestionnaire de connections WebSocket
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        # Lock to protect concurrent access to active_connections
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
            total = len(self.active_connections)
        logger.info(f"WebSocket connecté. Total: {total}")

    def disconnect(self, websocket: WebSocket):
        # remove without awaiting lock for simplicity;
        # called from finally blocks
        try:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        except ValueError:
            pass
        total = len(self.active_connections)
        logger.info(f"WebSocket déconnecté. Total: {total}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_text(json.dumps(message))
        except WebSocketDisconnect:
            self.disconnect(websocket)
            logger.info("WebSocketDisconnect lors de l'envoi d'un message")
        except Exception:
            logger.exception("Erreur lors de l'envoi d'un message WebSocket")
            self.disconnect(websocket)

    async def broadcast(self, message: dict):
        # Create a snapshot to avoid issues if the list mutates while iterating
        async with self._lock:
            connections = list(self.active_connections)

        disconnected = []
        for connection in connections:
            try:
                await connection.send_text(json.dumps(message))
            except WebSocketDisconnect:
                disconnected.append(connection)
            except Exception:
                logger.exception("Erreur lors du broadcast WebSocket")
                disconnected.append(connection)

        # Nettoyer les connexions fermées
        for conn in disconnected:
            self.disconnect(conn)


manager = ConnectionManager()

# ==============================================================================
# ENDPOINTS API REST
# ==============================================================================


@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serve the main dashboard"""
    return FileResponse("ui/index.html")


@app.get("/api/config", response_model=ConfigResponse)
async def get_config():
    """Récupère la configuration actuelle"""
    return config_service.get_current_config()


@app.post("/api/config")
async def update_config(config_data: dict):
    """Met à jour la configuration"""
    result = config_service.update_config(config_data)

    # Broadcast config update to all clients
    await manager.broadcast({"type": "config_updated", "data": result.dict()})

    return result


@app.post("/api/symbols/load")
async def load_symbols(request: SymbolRequest):
    """Charge les symboles avec options"""
    try:
        symbols = await screening_service.load_optionable_symbols(
            min_market_cap=request.min_market_cap,
            min_volume=request.min_volume,
            enable_prefiltering=request.enable_prefiltering,
        )

        await manager.broadcast(
            {
                "type": "symbols_loaded",
                "data": {
                    "symbols": symbols,
                    "count": len(symbols),
                    "timestamp": datetime.now().isoformat(),
                },
            }
        )

        return {"success": True, "symbols": symbols, "count": len(symbols)}

    except Exception as e:
        logger.error(f"Erreur chargement symboles: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/screening/start")
async def start_screening(request: ScreeningRequest, background_tasks: BackgroundTasks):
    """Démarre un screening en arrière-plan"""

    # Valider la requête
    if not request.symbols:
        return {"success": False, "error": "Aucun symbole fourni"}

    # Générer un ID de session unique
    session_id = f"screening_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Démarrer le screening en arrière-plan en créant une tâche asynchrone
    try:
        asyncio.create_task(run_screening_task(session_id, request))
    except Exception:
        # Fallback: tenter d'ajouter via BackgroundTasks si create_task échoue
        background_tasks.add_task(run_screening_task, session_id, request)

    return {
        "success": True,
        "session_id": session_id,
        "message": f"Screening démarré pour {len(request.symbols)} symboles",
    }


@app.get("/api/screening/{session_id}/results")
async def get_screening_results(session_id: str):
    """Récupère les résultats d'un screening"""
    results = screening_service.get_session_results(session_id)
    return {
        "session_id": session_id,
        "results": results,
        "count": len(results) if results else 0,
    }


@app.get("/api/screening/history")
async def get_screening_history():
    """Récupère l'historique des screenings"""
    history = screening_service.get_screening_history()
    return {"history": history}


# ==============================================================================
# WEBSOCKET POUR TEMPS RÉEL
# ==============================================================================


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket pour communications temps réel"""
    await manager.connect(websocket)

    try:
        # Envoyer un message de bienvenue
        await manager.send_personal_message(
            {
                "type": "connected",
                "message": "Connexion WebSocket établie",
                "timestamp": datetime.now().isoformat(),
            },
            websocket,
        )

        # Écouter les messages du client
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                # Traiter différents types de messages
                if message.get("type") == "ping":
                    ts = datetime.now().isoformat()
                    await manager.send_personal_message(
                        {"type": "pong", "timestamp": ts},
                        websocket,
                    )

                elif message.get("type") == "subscribe_screening":
                    session_id = message.get("session_id")
                    # Logique d'abonnement aux updates de screening
                    await manager.send_personal_message(
                        {
                            "type": "subscribed",
                            "session_id": session_id,
                        },
                        websocket,
                    )

            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                msg = {"type": "error", "message": "Format invalide"}
                await manager.send_personal_message(msg, websocket)
            except Exception as e:
                logger.error(f"Erreur WebSocket: {e}")
                await manager.send_personal_message(
                    {"type": "error", "message": str(e)}, websocket
                )

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)


# ==============================================================================
# TÂCHES EN ARRIÈRE-PLAN
# ==============================================================================


async def run_screening_task(session_id: str, request: ScreeningRequest):
    """Exécute un screening en arrière-plan avec WebSocket updates"""
    start_time = datetime.now()

    # Créer la session en base
    try:
        persistence_service.create_session(
            session_id=session_id,
            symbols=request.symbols,
            option_type=request.option_type,
            max_dte=request.max_dte,
            min_volume=request.min_volume,
            min_oi=request.min_oi,
            min_whale_score=request.min_whale_score,
            enable_ai=request.enable_ai,
        )
    except Exception as e:
        logger.warning(f"Impossible de créer la session DB: {e}")

    try:
        await manager.broadcast(
            {
                "type": "screening_started",
                "session_id": session_id,
                "symbols_count": len(request.symbols),
                "option_type": request.option_type,
            }
        )

        # Callback de progression
        async def progress_callback(
            current: int, total: int, symbol: str, details: str
        ):
            pct = (current / total) * 100 if total > 0 else 0
            await manager.broadcast(
                {
                    "type": "screening_progress",
                    "session_id": session_id,
                    "progress": {
                        "current": current,
                        "total": total,
                        "symbol": symbol,
                        "details": details,
                        "percentage": pct,
                    },
                }
            )

        # Exécuter le screening
        results = await screening_service.run_screening(
            symbols=request.symbols,
            option_type=request.option_type,
            max_dte=request.max_dte,
            min_volume=request.min_volume,
            min_oi=request.min_oi,
            min_whale_score=request.min_whale_score,
            enable_ai=request.enable_ai,
            progress_callback=progress_callback,
        )

        # Résultats finaux
        await manager.broadcast(
            {
                "type": "screening_completed",
                "session_id": session_id,
                "results": [result.dict() for result in results],
                "count": len(results),
                "timestamp": datetime.now().isoformat(),
            }
        )

        result_count = len(results)
        logger.info(f"Screening {session_id} terminé: {result_count} résultats")

        # Sauvegarder les résultats en base
        try:
            duration = (datetime.now() - start_time).total_seconds()
            persistence_service.save_results(session_id, results)
            persistence_service.complete_session(session_id, result_count, duration)
        except Exception as e:
            logger.warning(f"Impossible de sauvegarder les résultats DB: {e}")

    except Exception as e:
        logger.exception(f"Erreur screening {session_id}")
        error_data = {
            "type": "screening_error",
            "session_id": session_id,
            "error": str(e),
        }
        await manager.broadcast(error_data)
        try:
            duration = (datetime.now() - start_time).total_seconds()
            persistence_service.complete_session(session_id, 0, duration, error=str(e))
        except Exception:
            pass


# ==============================================================================
# ENDPOINTS SUPPLÉMENTAIRES
# ==============================================================================


@app.get("/api/status")
async def get_status():
    """Statut de l'application"""
    config = config_service.get_current_config()
    return {
        "active": (
            screening_service.is_running
            if hasattr(screening_service, "is_running")
            else False
        ),
        "opportunities_count": len(
            getattr(screening_service, "current_opportunities", [])
        ),
        "websocket_connections": len(manager.active_connections),
        "environment": config.environment.value,
        "api_base_url": config.base_url,
        "ai_capabilities": config.ai_capabilities,
    }


@app.get("/api/opportunities")
async def get_current_opportunities():
    """Récupère les opportunités du dernier screening"""
    opps = getattr(screening_service, "current_opportunities", [])
    return {
        "opportunities": [o.dict() if hasattr(o, "dict") else o for o in opps],
        "count": len(opps),
    }


@app.get("/api/symbols/suggestions")
async def get_symbol_suggestions():
    """Suggestions de symboles populaires"""
    try:
        symbols = await screening_service.get_symbol_suggestions()
        return {"symbols": symbols}
    except Exception as e:
        return {
            "symbols": ["AAPL", "TSLA", "NVDA", "SPY", "QQQ", "MSFT", "AMZN", "META"],
            "note": str(e),
        }


@app.post("/api/symbols/validate")
async def validate_symbols(payload: dict):
    """Valide une liste de symboles"""
    symbols = payload.get("symbols", [])
    try:
        results = await screening_service.validate_symbols(symbols)
        return {"validation_results": results}
    except Exception as e:
        return {"validation_results": {s: True for s in symbols}, "note": str(e)}


@app.post("/api/recommendations")
async def get_trade_recommendations():
    """Génère des recommandations de trades IA"""
    try:
        recommendations = await screening_service.get_ai_trade_recommendations()
        return recommendations
    except Exception as e:
        logger.error(f"Erreur recommandations: {e}")
        return []


@app.get("/api/database/stats")
async def get_database_stats():
    """Statistiques de la base historique Unusual Whales"""
    try:
        stats = screening_service.unusual_whales_service.get_database_stats()
        return {
            "historical_database": stats,
            "status": "active" if "error" not in stats else "error",
        }
    except Exception as e:
        return {"historical_database": {"error": str(e)}, "status": "error"}


# ==============================================================================
# ENDPOINTS BASE DE DONNÉES PERSISTANTE
# ==============================================================================


@app.get("/api/db/sessions")
async def list_db_sessions(limit: int = 50):
    """Liste les dernières sessions de screening sauvegardées"""
    return {"sessions": persistence_service.get_sessions(limit=limit)}


@app.get("/api/db/sessions/{session_id}/results")
async def get_db_session_results(session_id: str):
    """Résultats persistés d'une session"""
    results = persistence_service.get_session_results(session_id)
    return {"session_id": session_id, "results": results, "count": len(results)}


@app.get("/api/db/top")
async def get_top_stored_opportunities(min_score: float = 60.0, limit: int = 100):
    """Meilleures opportunités stockées toutes sessions confondues"""
    return {
        "opportunities": persistence_service.get_top_opportunities(min_score, limit)
    }


@app.get("/api/db/stats")
async def get_db_stats():
    """Statistiques de la base de données SQLite"""
    return persistence_service.get_stats()


@app.get("/api/history/stats")
async def get_history_stats(underlying: str = None):
    """Statistiques options_history.db — IV Rank, Vol Trend, couverture"""
    try:
        stats = history_service.get_stats(underlying=underlying)
        return {"status": "ok", "data": stats}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/history/sparklines")
async def get_history_sparklines(symbols: str = ""):
    """
    Returns score history (last 7 scan days) for each option symbol.
    Query param: ?symbols=SYM1,SYM2,...  (comma-separated OCC symbols)
    Response: {"sparklines": {"SYM": [s_d1, s_d2, ...], ...}}
    """
    syms = [s.strip() for s in symbols.split(",") if s.strip()][:200]
    if not syms:
        return {"sparklines": {}}
    try:
        data = history_service.get_score_sparklines(syms)
        return {"sparklines": data}
    except Exception as exc:
        return {"sparklines": {}, "error": str(exc)}


# ==============================================================================
# POINT D'ENTRÉE
# ==============================================================================

if __name__ == "__main__":
    print("🚀 Lancement Options Whale Screener (FastAPI)")
    print("📊 Interface: http://localhost:8000")
    print("📚 Documentation API: http://localhost:8000/api/docs")

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Rechargement auto en développement
        reload_delay=2.0,  # Debounce 2s pour éviter les rechargements en cascade
        log_level="info",
    )
