#!/usr/bin/env python3
"""
FastAPI Options Screening Application
Architecture moderne remplaçant Streamlit
"""

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

# Import des endpoints hybrides et short interest
from api.hybrid_endpoints import hybrid_router
from api.short_interest_endpoints import short_interest_router

# Chargement des variables d'environnement
from dotenv import load_dotenv

load_dotenv()

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
except Exception as e:
    logger.warning(f"Could not mount static files: {e}")

# Services
screening_service = ScreeningService()
config_service = ConfigService()

# Inclusion des routers hybrides et short interest
app.include_router(hybrid_router)
app.include_router(short_interest_router)


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

    except Exception as e:
        logger.exception(f"Erreur screening {session_id}")
        error_data = {
            "type": "screening_error",
            "session_id": session_id,
            "error": str(e),
        }
        await manager.broadcast(error_data)


# ==============================================================================
# FICHIERS STATIQUES
# ==============================================================================

# Servir les fichiers statiques (CSS, JS, images)
app.mount("/static", StaticFiles(directory="ui/static"), name="static")
app.mount("/ui", StaticFiles(directory="ui"), name="ui")

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
        log_level="info",
    )
