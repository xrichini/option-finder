"""
API FastAPI - Remplace l'interface Streamlit
Interface web moderne avec WebSocket pour le screening d'options en temps réel

DEPRECATED: Ce module est conservé pour compatibilité descendante.
Le point d'entrée principal est app.py (racine du projet).
Démarrer avec: uvicorn app:app --reload  ou  python start.py
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import json
from datetime import datetime
import logging
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Import de nos services
from services.config_service import ConfigService
from services.screening_service import ScreeningService
from models.api_models import OptionsOpportunity, ConfigResponse
from api.hybrid_endpoints import hybrid_router
from api.short_interest_endpoints import short_interest_router

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Options Squeeze Finder",
    description="Interface de screening d'options avec données temps réel",
    version="2.0.0",
)

# Inclusion des routers
app.include_router(hybrid_router)
app.include_router(short_interest_router)


# Models Pydantic pour l'API
class ScreeningRequest(BaseModel):
    symbols: List[str]
    screening_type: str = "classic"  # "classic" ou "ai"


class ScreeningConfig(BaseModel):
    max_dte: int = 7
    min_volume: int = 100
    min_oi: int = 50
    min_whale_score: float = 20.0
    ai_enabled: bool = False


class ScreeningResponse(BaseModel):
    opportunities: List[OptionsOpportunity]
    total_count: int
    screening_type: str
    execution_time: float
    timestamp: str


# État global de l'application
class AppState:
    def __init__(self):
        self.config_service = ConfigService()
        self.screening_service = ScreeningService()
        self.current_opportunities: List[OptionsOpportunity] = []
        self.screening_active: bool = False
        self.connected_websockets: List[WebSocket] = []


app_state = AppState()


# WebSocket manager
class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connecté. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket déconnecté. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        if self.active_connections:
            message_str = json.dumps(message, default=str)
            for connection in self.active_connections.copy():
                try:
                    await connection.send_text(message_str)
                except Exception as e:
                    logger.warning(f"Erreur broadcast WebSocket: {e}")
                    self.active_connections.remove(connection)


websocket_manager = WebSocketManager()


# Progress callback pour WebSocket
def create_progress_callback():
    async def progress_callback(current: int, total: int, message: str):
        progress_data = {
            "type": "progress",
            "current": current,
            "total": total,
            "message": message,
            "percentage": (current / total * 100) if total > 0 else 0,
            "timestamp": datetime.now().isoformat(),
        }
        await websocket_manager.broadcast(progress_data)

    return progress_callback


# Routes API principales


@app.get("/")
async def get_dashboard():
    """Page principale du dashboard - Version moderne"""
    # Utilise le fichier ui/index.html avec la nouvelle interface
    ui_html_path = Path("ui/index.html")

    if ui_html_path.exists():
        with open(ui_html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    else:
        # Fallback sur l'ancien dashboard si le fichier ui/index.html n'existe pas
        static_html_path = Path("static/dashboard.html")
        if static_html_path.exists():
            with open(static_html_path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        else:
            # Dashboard intégré minimal en dernier recours
            return HTMLResponse(content=get_embedded_dashboard_html())


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket pour les mises à jour temps réel"""
    await websocket_manager.connect(websocket)
    try:
        while True:
            # Garde la connexion active
            data = await websocket.receive_text()
            # Peut traiter des commandes du client si nécessaire
            try:
                command = json.loads(data)
                if command.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except:
                pass  # Ignore les messages non-JSON
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)


@app.get("/api/config", response_model=ConfigResponse)
async def get_config():
    """Récupère la configuration actuelle"""
    return app_state.config_service.get_current_config()


@app.put("/api/config", response_model=ConfigResponse)
async def update_config(config: ScreeningConfig):
    """Met à jour la configuration"""
    return app_state.config_service.update_config(config.dict())


@app.post("/api/screening/start", response_model=ScreeningResponse)
async def start_screening(request: ScreeningRequest):
    """Lance le screening d'options"""
    start_time = datetime.now()

    try:
        # Validation des symboles
        if not request.symbols:
            raise HTTPException(status_code=400, detail="Liste de symboles vide")

        # Notification de début
        await websocket_manager.broadcast(
            {
                "type": "screening_started",
                "symbols": request.symbols,
                "screening_type": request.screening_type,
                "timestamp": start_time.isoformat(),
            }
        )

        # Progress callback
        progress_cb = create_progress_callback()

        # Lancement du screening selon le type
        if request.screening_type == "ai":
            # TODO: Récupérer top_n depuis l'interface web
            # Pour l'instant, utilise une valeur par défaut de 10
            opportunities = await app_state.screening_service.screen_options_with_ai(
                symbols=request.symbols,
                progress_callback=progress_cb,
                top_n=10,  # Limite à 10 meilleures opportunités avec l'IA
            )
        else:
            opportunities = await app_state.screening_service.screen_options_classic(
                symbols=request.symbols, progress_callback=progress_cb
            )

        # Calcul du temps d'exécution
        execution_time = (datetime.now() - start_time).total_seconds()

        # Sauvegarde des résultats
        app_state.current_opportunities = opportunities

        # Préparation de la réponse
        response = ScreeningResponse(
            opportunities=opportunities,
            total_count=len(opportunities),
            screening_type=request.screening_type,
            execution_time=execution_time,
            timestamp=datetime.now().isoformat(),
        )

        # Notification de fin via WebSocket
        await websocket_manager.broadcast(
            {
                "type": "screening_completed",
                "data": {
                    "opportunities_count": len(opportunities),
                    "execution_time": execution_time,
                    "screening_type": request.screening_type,
                    "opportunities": [
                        opp.dict() for opp in opportunities[:10]
                    ],  # Top 10 seulement
                },
                "timestamp": datetime.now().isoformat(),
            }
        )

        logger.info(
            f"Screening {request.screening_type} terminé: {len(opportunities)} opportunités en {execution_time:.2f}s"
        )

        return response

    except Exception as e:
        error_msg = f"Erreur lors du screening: {str(e)}"
        logger.error(error_msg)

        # Notification d'erreur
        await websocket_manager.broadcast(
            {
                "type": "screening_error",
                "error": error_msg,
                "timestamp": datetime.now().isoformat(),
            }
        )

        raise HTTPException(status_code=500, detail=error_msg)


@app.get("/api/opportunities", response_model=List[OptionsOpportunity])
async def get_current_opportunities():
    """Récupère les opportunités actuelles"""
    return app_state.current_opportunities


@app.get("/api/symbols/suggestions")
async def get_symbol_suggestions():
    """Récupère des suggestions de symboles"""
    try:
        symbols = await app_state.screening_service.get_symbol_suggestions()
        return {"symbols": symbols}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/symbols/validate")
async def validate_symbols(symbols: List[str]):
    """Valide une liste de symboles"""
    try:
        validation_results = await app_state.screening_service.validate_symbols(symbols)
        return {"validation_results": validation_results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status")
async def get_status():
    """Récupère le statut de l'application"""
    config = app_state.config_service.get_current_config()
    return {
        "active": app_state.screening_active,
        "opportunities_count": len(app_state.current_opportunities),
        "websocket_connections": len(websocket_manager.active_connections),
        "environment": config.environment.value,
        "api_base_url": config.base_url,
        "ai_capabilities": config.ai_capabilities,
    }


@app.post("/api/recommendations")
async def get_trade_recommendations() -> List[Dict[str, Any]]:
    """
    Génère des recommandations de trades IA
    """
    try:
        recommendations = (
            await app_state.screening_service.get_ai_trade_recommendations()
        )

        logger.info(f"Généré {len(recommendations)} recommandations de trades")
        return recommendations

    except Exception as e:
        logger.error(f"Erreur génération recommandations: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la génération des recommandations: {str(e)}",
        )


@app.get("/api/database/stats")
async def get_database_stats():
    """
    Récupère les statistiques de la base historique Unusual Whales
    """
    try:
        stats = app_state.screening_service.unusual_whales_service.get_database_stats()

        return {
            "historical_database": stats,
            "status": "active" if "error" not in stats else "error",
        }

    except Exception as e:
        logger.error(f"Erreur récupération stats DB: {e}")
        return {"historical_database": {"error": str(e)}, "status": "error"}


# Gestion des fichiers statiques
# Mount the ui directory to serve CSS, JS, etc
data_dir = Path(__file__).parent.parent / "data"
ui_dir = Path(__file__).parent.parent / "ui"
ui_static_dir = ui_dir / "static"

app.mount("/ui", StaticFiles(directory=str(ui_dir)), name="ui")
app.mount("/static", StaticFiles(directory=str(ui_static_dir)), name="static")
app.mount("/data", StaticFiles(directory=str(data_dir)), name="data")


def get_embedded_dashboard_html() -> str:
    """Dashboard HTML moderne avec paramètres configurables"""
    return """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🐋 Options Squeeze Finder</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1f4e79 0%, #2e7d32 100%);
            color: white;
            min-height: 100vh;
            overflow-x: auto;
        }
        
        .main-container {
            display: flex;
            min-height: 100vh;
        }
        
        /* Sidebar */
        .sidebar {
            width: 320px;
            background: rgba(0,0,0,0.2);
            padding: 20px;
            backdrop-filter: blur(15px);
            border-right: 1px solid rgba(255,255,255,0.1);
            overflow-y: auto;
            max-height: 100vh;
        }
        
        .sidebar h2 {
            margin-bottom: 20px;
            color: #e8f5e8;
            font-size: 1.3rem;
        }
        
        .param-group {
            background: rgba(255,255,255,0.1);
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            backdrop-filter: blur(10px);
        }
        
        .param-group h3 {
            margin-bottom: 15px;
            color: #fff;
            font-size: 1.1rem;
            border-bottom: 2px solid rgba(255,255,255,0.2);
            padding-bottom: 8px;
        }
        
        .param-item {
            margin-bottom: 15px;
        }
        
        .param-item label {
            display: block;
            margin-bottom: 5px;
            font-weight: 600;
            color: #e8f5e8;
            font-size: 0.9rem;
        }
        
        .param-item input, .param-item select {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid rgba(255,255,255,0.3);
            border-radius: 6px;
            background: rgba(255,255,255,0.1);
            color: white;
            font-size: 0.9rem;
        }
        
        .param-item input:focus, .param-item select:focus {
            outline: none;
            border-color: #38ef7d;
            background: rgba(255,255,255,0.15);
        }
        
        .param-item input::placeholder {
            color: rgba(255,255,255,0.6);
        }
        
        .range-display {
            text-align: center;
            font-size: 0.8rem;
            color: #38ef7d;
            margin-top: 3px;
        }
        
        /* Main content */
        .main-content {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
            padding: 25px;
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            backdrop-filter: blur(10px);
        }
        
        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #ff6b6b, #ffd93d);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .controls {
            display: grid;
            grid-template-columns: 1fr auto;
            gap: 20px;
            margin-bottom: 30px;
            align-items: end;
        }
        
        .symbols-input {
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 10px;
            backdrop-filter: blur(10px);
        }
        
        .symbols-input input {
            width: 100%;
            padding: 12px;
            border: 1px solid rgba(255,255,255,0.3);
            border-radius: 8px;
            background: rgba(255,255,255,0.1);
            color: white;
            font-size: 1rem;
        }
        
        .action-buttons {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        
        button {
            padding: 12px 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s ease;
            text-transform: uppercase;
            font-size: 0.9rem;
        }
        
        .btn-primary {
            background: linear-gradient(45deg, #11998e, #38ef7d);
            color: white;
        }
        
        .btn-secondary {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }
        
        .status {
            text-align: center;
            padding: 15px;
            margin: 20px 0;
            border-radius: 10px;
            font-weight: bold;
            background: rgba(255,255,255,0.1);
        }
        
        .progress {
            width: 100%;
            height: 25px;
            background: rgba(255,255,255,0.2);
            border-radius: 10px;
            overflow: hidden;
            margin: 20px 0;
            display: none;
        }
        
        .progress-bar {
            height: 100%;
            background: linear-gradient(45deg, #11998e, #38ef7d);
            width: 0%;
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 0.8rem;
        }
        
        .results {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 20px;
            backdrop-filter: blur(10px);
            display: none;
        }
        
        .results-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid rgba(255,255,255,0.2);
        }
        
        .opportunity {
            background: linear-gradient(135deg, rgba(255,255,255,0.15), rgba(255,255,255,0.05));
            border-left: 4px solid #38ef7d;
            margin: 15px 0;
            padding: 20px;
            border-radius: 0 10px 10px 0;
            transition: transform 0.3s ease;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }
        
        .opportunity:hover {
            transform: translateX(5px);
        }
        
        .opportunity-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        
        .opportunity-title {
            font-size: 1.3rem;
            font-weight: bold;
            color: #38ef7d;
        }
        
        .whale-score {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: bold;
            background: linear-gradient(45deg, #ff6b6b, #ffd93d);
            color: #000;
        }
        
        .opportunity-details {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
            font-size: 0.9rem;
            opacity: 0.9;
        }
        
        .detail-item {
            background: rgba(255,255,255,0.1);
            padding: 8px 12px;
            border-radius: 6px;
            text-align: center;
        }
        
        .detail-label {
            font-size: 0.7rem;
            opacity: 0.8;
            text-transform: uppercase;
            margin-bottom: 2px;
        }
        
        .detail-value {
            font-weight: bold;
            font-size: 1rem;
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .main-container {
                flex-direction: column;
            }
            
            .sidebar {
                width: 100%;
                max-height: none;
            }
            
            .controls {
                grid-template-columns: 1fr;
            }
        }
        
        /* Animation */
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.7; }
            100% { opacity: 1; }
        }
        
        .loading {
            animation: pulse 2s infinite;
        }
    </style>
</head>
<body>
    <div class="main-container">
        <!-- Sidebar avec paramètres -->
        <div class="sidebar">
            <h2>⚙️ Configuration</h2>
            
            <!-- Paramètres de filtrage symboles -->
            <div class="param-group">
                <h3>📈 Filtrage Symboles</h3>
                
                <div class="param-item">
                    <label>Capitalisation minimum</label>
                    <select id="minMarketCap">
                        <option value="50000000">50M $</option>
                        <option value="100000000" selected>100M $</option>
                        <option value="500000000">500M $</option>
                        <option value="1000000000">1B $</option>
                    </select>
                </div>
                
                <div class="param-item">
                    <label>Volume stock minimum</label>
                    <select id="minStockVolume">
                        <option value="100000">100K</option>
                        <option value="500000" selected>500K</option>
                        <option value="1000000">1M</option>
                        <option value="2000000">2M</option>
                    </select>
                </div>
            </div>
            
            <!-- Paramètres de filtrage options -->
            <div class="param-group">
                <h3>🎯 Filtrage Options</h3>
                
                <div class="param-item">
                    <label>📅 DTE maximum</label>
                    <input type="range" id="maxDte" min="1" max="21" value="7">
                    <div class="range-display"><span id="maxDteValue">7</span> jours</div>
                </div>
                
                <div class="param-item">
                    <label>📈 Volume minimum</label>
                    <input type="number" id="minVolume" min="10" max="10000" value="100" step="10">
                </div>
                
                <div class="param-item">
                    <label>📈 Open Interest minimum</label>
                    <input type="number" id="minOI" min="1" max="5000" value="50" step="10">
                </div>
                
                <div class="param-item">
                    <label>🐋 Score Whale minimum</label>
                    <input type="range" id="minWhaleScore" min="20" max="95" value="30" step="5">
                    <div class="range-display"><span id="whaleScoreValue">30</span> points</div>
                </div>
                
                <div class="param-item">
                    <label>📊 Ratio Vol/OI minimum</label>
                    <input type="range" id="minVolOI" min="0" max="5" value="1" step="0.1">
                    <div class="range-display"><span id="volOIValue">1.0</span>x</div>
                </div>
            </div>
            
            <!-- Paramètres IA -->
            <div class="param-group">
                <h3>🧠 Analyse IA</h3>
                
                <div class="param-item">
                    <label>Top N avec IA</label>
                    <input type="number" id="aiTopN" min="3" max="20" value="5">
                    <small style="opacity: 0.7;">Nombre d'opportunités à analyser avec l'IA</small>
                </div>
                
                <div style="margin-top: 15px; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 6px; font-size: 0.8rem;">
                    <strong style="color: #38ef7d;">📊 Score IA (0-100%) :</strong><br>
                    <span style="opacity: 0.8;">
                    • Volume exceptionnel : 30pts<br>
                    • Open Interest solide : 25pts<br>
                    • Ratio Volume/OI : 20pts<br>
                    • DTE optimal (3-14j) : 15pts<br>
                    • Spread raisonnable : 10pts
                    </span>
                </div>
            </div>
        </div>
        
        <!-- Contenu principal -->
        <div class="main-content">
            <div class="header">
                <h1>🐋 Options Squeeze Finder</h1>
                <p>Détection des Big Calls & Puts avec Analyse IA temps réel</p>
            </div>
            
            <div class="controls">
                <div class="symbols-input">
                    <label>🎯 Symboles à analyser (séparés par virgules)</label>
                    <input type="text" id="symbols" placeholder="AAPL,TSLA,NVDA,SPY,QQQ" value="AAPL,TSLA,NVDA,SPY">
                </div>
                
                <div class="action-buttons">
                    <button id="startClassic" class="btn-primary">🚀 Screening Classique</button>
                    <button id="startAI" class="btn-secondary">🧠 Screening IA</button>
                    <button id="getRecommendations" class="btn-secondary" style="background: linear-gradient(45deg, #ff6b6b, #ffd93d);">📊 Recommandations IA</button>
                </div>
            </div>
            
            <div class="status" id="status">
                Prêt à démarrer le screening
            </div>
            
            <div class="progress" id="progress">
                <div class="progress-bar" id="progressBar">0%</div>
            </div>
            
            <div class="results" id="results">
                <div class="results-header">
                    <h2>📈 Opportunités Détectées</h2>
                    <span id="resultsCount">0 opportunités</span>
                </div>
                <div id="opportunitiesList"></div>
            </div>
        </div>
    </div>

    <script>
        let ws = null;
        let currentConfig = {};
        
        // Connexion WebSocket
        function connectWebSocket() {
            const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws`);
            
            ws.onopen = () => console.log('🔗 WebSocket connecté');
            ws.onmessage = (event) => handleWebSocketMessage(JSON.parse(event.data));
            ws.onerror = (error) => console.error('❌ Erreur WebSocket:', error);
            ws.onclose = () => {
                console.log('🔌 WebSocket fermé, reconnexion...');
                setTimeout(connectWebSocket, 3000);
            };
        }
        
        // Gestion des messages WebSocket
        function handleWebSocketMessage(data) {
            const status = document.getElementById('status');
            const progress = document.getElementById('progress');
            const progressBar = document.getElementById('progressBar');
            
            switch(data.type) {
                case 'screening_started':
                    status.textContent = `🔄 Screening ${data.screening_type} démarré...`;
                    progress.style.display = 'block';
                    break;
                    
                case 'progress':
                    const percentage = Math.round(data.percentage);
                    progressBar.style.width = percentage + '%';
                    progressBar.textContent = percentage + '%';
                    status.textContent = data.message;
                    break;
                    
                case 'screening_completed':
                    status.textContent = `✅ Screening terminé en ${data.data.execution_time.toFixed(1)}s: ${data.data.opportunities_count} opportunités`;
                    progress.style.display = 'none';
                    displayOpportunities(data.data.opportunities, data.data.opportunities_count);
                    break;
                    
                case 'screening_error':
                    status.textContent = `❌ Erreur: ${data.error}`;
                    progress.style.display = 'none';
                    break;
            }
        }
        
        // Affichage des opportunités
        function displayOpportunities(opportunities, totalCount) {
            const results = document.getElementById('results');
            const list = document.getElementById('opportunitiesList');
            const count = document.getElementById('resultsCount');
            
            count.textContent = `${totalCount} opportunités`;
            
            if (!opportunities || opportunities.length === 0) {
                list.innerHTML = '<p style="text-align: center; opacity: 0.7;">Aucune opportunité trouvée avec les critères actuels</p>';
            } else {
                list.innerHTML = opportunities.map(opp => `
                    <div class="opportunity">
                        <div class="opportunity-header">
                            <span class="opportunity-title">${opp.underlying_symbol} - ${opp.option_type.toUpperCase()}</span>
                            <span class="whale-score">${opp.whale_score.toFixed(1)}</span>
                        </div>
                        <div class="opportunity-details">
                            <div class="detail-item">
                                <div class="detail-label">Strike</div>
                                <div class="detail-value">$${opp.strike}</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">DTE</div>
                                <div class="detail-value">${opp.dte}j</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">Volume</div>
                                <div class="detail-value">${opp.volume.toLocaleString()}</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">Open Interest</div>
                                <div class="detail-value">${opp.open_interest.toLocaleString()}</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">Bid/Ask</div>
                                <div class="detail-value">$${opp.bid}/$${opp.ask}</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">Dernier</div>
                                <div class="detail-value">$${opp.last}</div>
                            </div>
                        </div>
                    </div>
                `).join('');
            }
            
            results.style.display = 'block';
        }
        
        // Mise à jour des affichages de range
        function updateRangeDisplays() {
            document.getElementById('maxDteValue').textContent = document.getElementById('maxDte').value;
            document.getElementById('whaleScoreValue').textContent = document.getElementById('minWhaleScore').value;
            document.getElementById('volOIValue').textContent = parseFloat(document.getElementById('minVolOI').value).toFixed(1);
        }
        
        // Gestion des recommandations
        async function getTradeRecommendations() {
            const status = document.getElementById('status');
            status.textContent = '📊 Génération des recommandations IA...';
            status.classList.add('loading');
            
            try {
                const response = await fetch('/api/recommendations', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'}
                });
                
                if (!response.ok) {
                    throw new Error(`Erreur HTTP: ${response.status}`);
                }
                
                const recommendations = await response.json();
                displayRecommendations(recommendations);
                
                status.textContent = `✅ Généré ${recommendations.length} recommandations IA`;
                status.classList.remove('loading');
                
            } catch (error) {
                status.textContent = `❌ Erreur: ${error.message}`;
                status.classList.remove('loading');
            }
        }
        
        // Affichage des recommandations
        function displayRecommendations(recommendations) {
            const results = document.getElementById('results');
            const list = document.getElementById('opportunitiesList');
            const count = document.getElementById('resultsCount');
            const header = document.querySelector('.results-header h2');
            
            header.textContent = '📊 Recommandations de Trades IA';
            count.textContent = `${recommendations.length} recommandations`;
            
            if (!recommendations || recommendations.length === 0) {
                list.innerHTML = '<p style="text-align: center; opacity: 0.7;">Aucune recommandation disponible</p>';
            } else {
                list.innerHTML = recommendations.map(rec => `
                    <div class="opportunity" style="border-left-color: #ff6b6b; cursor: pointer;" onclick="showTradeDetails('${rec.option_symbol}', '${rec.symbol}')">
                        <div class="opportunity-header">
                            <span class="opportunity-title">${rec.trade_type} - ${rec.symbol}</span>
                            <div style="text-align: center;">
                                <span class="whale-score" style="background: linear-gradient(45deg, #38ef7d, #11998e);">${(rec.confidence_level * 100).toFixed(0)}%</span>
                                <div style="font-size: 0.7rem; opacity: 0.8; margin-top: 2px;">Score IA</div>
                            </div>
                        </div>
                        <div style="margin: 10px 0; padding: 15px; background: rgba(56,239,125,0.1); border-radius: 8px; border: 1px solid rgba(56,239,125,0.3);">
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px;">
                                <div><strong>🎯 Action:</strong> <span style="color: #38ef7d;">${rec.full_recommendation}</span></div>
                                <div><strong>📅 Expiration:</strong> ${rec.expiration_date} (${rec.dte}j)</div>
                                <div><strong>💰 Strike:</strong> $${rec.strike}</div>
                                <div><strong>📈 Dernier Prix:</strong> $${rec.entry_price.toFixed(2)}</div>
                            </div>
                            <div style="font-size: 0.9rem;">
                                <strong>Stratégie:</strong> ${rec.strategy_description}<br>
                                <strong>Outlook:</strong> ${rec.market_outlook}<br>
                                ${rec.key_factors.length > 0 ? '<strong>Facteurs clés:</strong> ' + rec.key_factors.join(', ') : ''}
                            </div>
                        </div>
                        <div class="opportunity-details">
                            <div class="detail-item">
                                <div class="detail-label">Entrée</div>
                                <div class="detail-value">$${rec.entry_price.toFixed(2)}</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">Cible</div>
                                <div class="detail-value">$${rec.target_price.toFixed(2)}</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">Stop Loss</div>
                                <div class="detail-value">$${rec.stop_loss.toFixed(2)}</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">Risk/Reward</div>
                                <div class="detail-value">${rec.risk_reward_ratio.toFixed(1)}:1</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">Probabilité</div>
                                <div class="detail-value">${(rec.probability_success * 100).toFixed(0)}%</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">Horizon</div>
                                <div class="detail-value">${rec.time_horizon}</div>
                            </div>
                        </div>
                        ${rec.warnings && rec.warnings.length > 0 ? `
                            <div style="margin-top: 15px; padding: 10px; background: rgba(255,107,107,0.2); border-radius: 5px; border-left: 3px solid #ff6b6b;">
                                ${rec.warnings.join('<br>')}
                            </div>
                        ` : ''}
                    </div>
                `).join('');
            }
            
            results.style.display = 'block';
        }
        
        // Modal pour détails de trade
        function showTradeDetails(optionSymbol, underlyingSymbol) {
            // Pour l'instant, simple alert - peut être étendu en modal complet
            alert(`Détails du trade :\n\nOption: ${optionSymbol}\nTitre: ${underlyingSymbol}\n\n💡 Cliquez sur cette recommandation pour voir tous les détails !`);
        }
        
        // Lancement du screening
        async function startScreening(type) {
            const symbols = document.getElementById('symbols').value.split(',').map(s => s.trim()).filter(s => s);
            
            if (symbols.length === 0) {
                alert('Veuillez saisir au moins un symbole');
                return;
            }
            
            // TODO: Implémenter la mise à jour de la config via API
            // updateConfig();
            
            try {
                const response = await fetch('/api/screening/start', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        symbols: symbols,
                        screening_type: type
                    })
                });
                
                if (!response.ok) {
                    throw new Error(`Erreur HTTP: ${response.status}`);
                }
                
            } catch (error) {
                document.getElementById('status').textContent = `❌ Erreur: ${error.message}`;
            }
        }
        
        // Événements
        document.addEventListener('DOMContentLoaded', () => {
            // Mise à jour des affichages range
            document.getElementById('maxDte').addEventListener('input', updateRangeDisplays);
            document.getElementById('minWhaleScore').addEventListener('input', updateRangeDisplays);
            document.getElementById('minVolOI').addEventListener('input', updateRangeDisplays);
            
            // Boutons de screening
            document.getElementById('startClassic').addEventListener('click', () => startScreening('classic'));
            document.getElementById('startAI').addEventListener('click', () => startScreening('ai'));
            document.getElementById('getRecommendations').addEventListener('click', getTradeRecommendations);
            
            // Initialisation
            updateRangeDisplays();
            connectWebSocket();
        });
    </script>
</body>
</html>
    """


if __name__ == "__main__":
    import uvicorn

    print("🚀 Démarrage du serveur Options Squeeze Finder...")
    print("📊 Interface disponible sur: http://localhost:8000")

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
