"""
Modèles Pydantic pour l'API REST FastAPI
Séparation claire entre API et logique métier
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

# ==============================================================================
# ENUMS
# ==============================================================================


class OptionType(str, Enum):
    CALL = "call"
    PUT = "put"


class EnvironmentType(str, Enum):
    SANDBOX = "sandbox"
    PRODUCTION = "production"


# ==============================================================================
# REQUÊTES API
# ==============================================================================


class SymbolRequest(BaseModel):
    """Requête pour charger des symboles"""

    min_market_cap: int = Field(
        default=100_000_000, description="Capitalisation minimum"
    )
    min_volume: int = Field(default=500_000, description="Volume stock minimum")
    enable_prefiltering: bool = Field(
        default=True, description="Activer le pré-filtrage"
    )


class ScreeningRequest(BaseModel):
    """Requête pour démarrer un screening"""

    symbols: List[str] = Field(..., description="Liste des symboles à analyser")
    option_type: OptionType = Field(..., description="Type d'options (call/put)")
    max_dte: int = Field(default=7, ge=1, le=45, description="DTE maximum")
    min_volume: int = Field(default=10, ge=1, description="Volume minimum")
    min_oi: int = Field(default=1, ge=0, description="Open Interest minimum")
    min_whale_score: float = Field(
        default=30.0, ge=0, le=100, description="Score whale minimum"
    )
    enable_ai: bool = Field(default=False, description="Activer l'analyse IA")


class ConfigUpdateRequest(BaseModel):
    """Requête pour mettre à jour la configuration"""

    environment: Optional[EnvironmentType] = None
    min_volume_threshold: Optional[int] = None
    min_oi_threshold: Optional[int] = None
    min_whale_score: Optional[float] = None
    ai_enabled: Optional[bool] = None


# ==============================================================================
# RÉPONSES API
# ==============================================================================


class ConfigResponse(BaseModel):
    """Configuration actuelle du système"""

    environment: EnvironmentType
    base_url: str
    is_development: bool
    min_volume_threshold: int
    min_oi_threshold: int
    min_whale_score: float
    ai_capabilities: bool
    screening_parameters: Dict[str, Any]


class OptionResult(BaseModel):
    """Résultat d'une option analysée"""

    symbol: str
    underlying: str
    strike: float
    expiration: str
    option_type: str
    volume_1d: int
    open_interest: int
    whale_score: float
    last_price: float = 0.0
    bid: float = 0.0
    ask: float = 0.0
    delta: float = 0.0
    implied_volatility: float = 0.0
    dte: int = 0

    # Greeks complets
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    rho: Optional[float] = None

    # Propriétés calculées
    vol_oi_ratio: float = 0.0
    block_size_category: str = ""
    is_unusual_activity: bool = False
    anomaly_score: Optional[float] = None
    ai_analysis: Optional[Dict[str, Any]] = None


class ScreeningResult(BaseModel):
    """Résultats complets d'un screening"""

    session_id: str
    timestamp: datetime
    option_type: OptionType
    symbols_analyzed: List[str]
    total_options_found: int
    results: List[OptionResult]
    execution_time: float
    parameters_used: Dict[str, Any]


class ScreeningProgress(BaseModel):
    """Progression d'un screening"""

    session_id: str
    current: int
    total: int
    symbol: str
    details: str
    percentage: float
    timestamp: datetime


class ScreeningSession(BaseModel):
    """Session de screening"""

    session_id: str
    status: str  # "running", "completed", "error"
    start_time: datetime
    end_time: Optional[datetime] = None
    option_type: OptionType
    symbols_count: int
    results_count: int = 0
    error_message: Optional[str] = None


# ==============================================================================
# WEBSOCKET MESSAGES
# ==============================================================================


class WebSocketMessage(BaseModel):
    """Message WebSocket générique"""

    type: str
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class ProgressMessage(WebSocketMessage):
    """Message de progression WebSocket"""

    type: str = "screening_progress"
    session_id: str
    progress: ScreeningProgress


class ResultsMessage(WebSocketMessage):
    """Message de résultats WebSocket"""

    type: str = "screening_completed"
    session_id: str
    results: List[OptionResult]
    count: int


class ErrorMessage(WebSocketMessage):
    """Message d'erreur WebSocket"""

    type: str = "error"
    error: str
    session_id: Optional[str] = None


# ==============================================================================
# MODÈLES HISTORIQUES
# ==============================================================================


class HistoricalData(BaseModel):
    """Données historiques d'une option"""

    symbol: str
    date: datetime
    volume: int
    open_interest: int
    price: float
    implied_volatility: float


class HistoricalAnalysis(BaseModel):
    """Analyse historique d'une option"""

    symbol: str
    volume_avg_7d: float
    volume_avg_30d: float
    oi_avg_7d: float
    oi_avg_30d: float
    volume_anomaly_score: float
    oi_anomaly_score: float
    trend: str  # "increasing", "decreasing", "stable"


# ==============================================================================
# RÉPONSES D'ERREUR
# ==============================================================================

# ==============================================================================
# MODÈLES TRADIER
# ==============================================================================


class OptionData(BaseModel):
    """Données d'une option individuelle"""

    symbol: str
    option_type: str
    strike: float
    expiration_date: str
    volume: Optional[int] = 0
    open_interest: Optional[int] = 0
    bid: Optional[float] = 0.0
    ask: Optional[float] = 0.0
    last: Optional[float] = 0.0


class OptionsChainData(BaseModel):
    """Chaîne d'options"""

    option: List[OptionData]


class OptionsChainSnapshot(BaseModel):
    """Snapshot complet des chaînes d'options"""

    symbol: str
    options: Optional[OptionsChainData] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class OptionsOpportunity(BaseModel):
    """Opportunité d'option détectée"""

    underlying_symbol: str
    option_symbol: str
    option_type: str
    strike: float
    expiration_date: str
    dte: int
    volume: int
    open_interest: int
    bid: float
    ask: float
    last: float
    whale_score: float
    reasoning: str = ""
    ai_analysis: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    # Greeks (valeurs optionnelles)
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    rho: Optional[float] = None
    implied_volatility: Optional[float] = None

    # --- Champs enrichis (inline avec Ghost Prints) ---
    vol_oi_ratio: float = 0.0  # Vol / Open Interest
    change_pct: float = 0.0  # % de changement du prix option
    stock_volume: int = 0  # Volume du sous-jacent (actions)
    underlying_price: float = 0.0  # Prix du sous-jacent
    sector: str = ""  # Secteur (Technology, ETF, ...)
    sizzle_index: float = 0.0  # Vol actuel / moyenne 30j (Unusual Whales)
    moneyness: str = ""  # ITM / OTM / ATM
    moneyness_pct: float = 0.0  # % distance strike/sous-jacent

    # --- Métriques historiques comparatives (calculées depuis options_history.db) ---
    iv_rank: float = 0.0        # IV Rank 52 semaines (0-100)
    iv_percentile: float = 0.0  # IV Percentile 252j (0-100)
    oi_spike_ratio: float = 0.0 # OI aujourd'hui / avg OI 5j
    vol_trend_ratio: float = 0.0 # Vol aujourd'hui / avg Vol 5j


class ErrorResponse(BaseModel):
    """Réponse d'erreur standardisée"""

    success: bool = False
    error: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class SuccessResponse(BaseModel):
    """Réponse de succès standardisée"""

    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None


# ==============================================================================
# FILTRES AVANCÉS
# ==============================================================================


class AdvancedFilters(BaseModel):
    """Filtres avancés pour le screening d'options"""

    # Filtres de prix/strikes
    min_strike: Optional[float] = Field(None, description="Strike minimum")
    max_strike: Optional[float] = Field(None, description="Strike maximum")

    # Filtres de temps
    min_dte: Optional[int] = Field(None, ge=0, description="DTE minimum")
    max_dte: Optional[int] = Field(None, le=365, description="DTE maximum")

    # Filtres IV
    min_iv: Optional[float] = Field(None, ge=0, description="IV minimum (%)")
    max_iv: Optional[float] = Field(None, le=500, description="IV maximum (%)")

    # Filtres volume/OI
    min_volume: Optional[int] = Field(None, ge=0, description="Volume minimum")
    max_volume: Optional[int] = Field(None, description="Volume maximum")
    min_oi: Optional[int] = Field(None, ge=0, description="OI minimum")
    max_oi: Optional[int] = Field(None, description="OI maximum")

    # Filtres Greeks
    min_delta: Optional[float] = Field(None, ge=-1, le=1, description="Delta minimum")
    max_delta: Optional[float] = Field(None, ge=-1, le=1, description="Delta maximum")

    # Filtres whale score
    min_whale_score: Optional[float] = Field(
        None, ge=0, le=100, description="Score whale minimum"
    )
    max_whale_score: Optional[float] = Field(
        None, ge=0, le=100, description="Score whale maximum"
    )

    # Filtres prix
    min_price: Optional[float] = Field(None, ge=0, description="Prix minimum")
    max_price: Optional[float] = Field(None, description="Prix maximum")


class FilterPreset(BaseModel):
    """Preset de filtres sauvegardés"""

    name: str = Field(..., description="Nom du preset")
    description: Optional[str] = Field(None, description="Description")
    filters: AdvancedFilters = Field(..., description="Filtres du preset")
    is_default: bool = Field(default=False, description="Est-ce le preset par défaut?")


class AdvancedScreeningRequest(BaseModel):
    """Requête de screening avec filtres avancés"""

    symbols: List[str] = Field(..., description="Symboles à analyser")
    option_type: OptionType = Field(..., description="Type d'options")
    filters: AdvancedFilters = Field(
        default_factory=AdvancedFilters, description="Filtres avancés"
    )
    preset_name: Optional[str] = Field(None, description="Nom du preset si applicable")
    enable_ai: bool = Field(default=False, description="Activer analyse IA")


# ==============================================================================
# UTILITAIRES
# ==============================================================================


def create_error_response(
    error: str, code: str = None, details: Dict = None
) -> ErrorResponse:
    """Créer une réponse d'erreur standardisée"""
    return ErrorResponse(error=error, error_code=code, details=details)


def create_success_response(message: str, data: Dict = None) -> SuccessResponse:
    """Créer une réponse de succès standardisée"""
    return SuccessResponse(message=message, data=data)
