"""
Modèles SQLModel - tables de la base de données SQLite
"""

from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
import json


class ScreeningSession(SQLModel, table=True):
    """Une session de screening (run)"""

    __tablename__ = "screening_sessions"

    id: str = Field(
        primary_key=True, description="session_id unique ex: screening_20260222_143000"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Paramètres du screening
    symbols_json: str = Field(
        default="[]", description="JSON list des symboles analysés"
    )
    option_type: str = Field(default="call")
    max_dte: int = Field(default=7)
    min_volume: int = Field(default=10)
    min_oi: int = Field(default=1)
    min_whale_score: float = Field(default=30.0)
    enable_ai: bool = Field(default=False)

    # Résumé
    status: str = Field(default="running")  # running | completed | error
    result_count: int = Field(default=0)
    duration_seconds: float = Field(default=0.0)
    error_message: Optional[str] = None

    # Relation
    results: List["ScreeningResult"] = Relationship(back_populates="session")

    @property
    def symbols(self) -> List[str]:
        return json.loads(self.symbols_json)

    @symbols.setter
    def symbols(self, value: List[str]):
        self.symbols_json = json.dumps(value)


class ScreeningResult(SQLModel, table=True):
    """Un résultat individuel (une opportunité option) dans une session"""

    __tablename__ = "screening_results"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="screening_sessions.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Identité du contrat
    symbol: str = Field(index=True)
    underlying: str = Field(default="")
    option_type: str = Field(default="call")
    strike: float = Field(default=0.0)
    expiration: str = Field(default="")
    dte: int = Field(default=0)

    # Métriques de marché
    volume: int = Field(default=0)
    open_interest: int = Field(default=0)
    bid: float = Field(default=0.0)
    ask: float = Field(default=0.0)
    last_price: float = Field(default=0.0)

    # Greeks
    delta: float = Field(default=0.0)
    implied_volatility: float = Field(default=0.0)
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None

    # Score
    whale_score: float = Field(default=0.0, index=True)
    vol_oi_ratio: float = Field(default=0.0)
    is_unusual_activity: bool = Field(default=False)

    # Relation
    session: Optional[ScreeningSession] = Relationship(back_populates="results")
