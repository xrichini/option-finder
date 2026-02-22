"""
Service de persistence - sauvegarde et lecture des sessions/résultats de screening
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from sqlmodel import Session, select, col
from db import engine, init_db
from db.models import ScreeningSession, ScreeningResult

logger = logging.getLogger(__name__)


class PersistenceService:
    """CRUD pour les sessions et résultats de screening"""

    def __init__(self):
        init_db()

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    def create_session(
        self,
        session_id: str,
        symbols: List[str],
        option_type: str,
        max_dte: int,
        min_volume: int,
        min_oi: int,
        min_whale_score: float,
        enable_ai: bool,
    ) -> ScreeningSession:
        """Crée une nouvelle session en base"""
        session_obj = ScreeningSession(
            id=session_id,
            symbols_json=__import__("json").dumps(symbols),
            option_type=option_type,
            max_dte=max_dte,
            min_volume=min_volume,
            min_oi=min_oi,
            min_whale_score=min_whale_score,
            enable_ai=enable_ai,
            status="running",
        )
        with Session(engine) as db:
            db.add(session_obj)
            db.commit()
            db.refresh(session_obj)
        logger.info(f"Session créée: {session_id}")
        return session_obj

    def complete_session(
        self,
        session_id: str,
        result_count: int,
        duration_seconds: float,
        error: Optional[str] = None,
    ) -> None:
        """Marque la session comme terminée"""
        with Session(engine) as db:
            stmt = select(ScreeningSession).where(ScreeningSession.id == session_id)
            session_obj = db.exec(stmt).first()
            if session_obj:
                session_obj.status = "error" if error else "completed"
                session_obj.completed_at = datetime.utcnow()
                session_obj.result_count = result_count
                session_obj.duration_seconds = round(duration_seconds, 2)
                session_obj.error_message = error
                db.add(session_obj)
                db.commit()

    def save_results(self, session_id: str, results: List[Any]) -> int:
        """
        Sauvegarde une liste d'opportunités (OptionsOpportunity ou dict).
        Retourne le nombre de lignes insérées.
        """
        rows = []
        for r in results:
            d = r.dict() if hasattr(r, "dict") else (r if isinstance(r, dict) else {})
            row = ScreeningResult(
                session_id=session_id,
                symbol=d.get("symbol", d.get("option_symbol", "")),
                underlying=d.get("underlying", d.get("underlying_symbol", "")),
                option_type=d.get("option_type", "call"),
                strike=float(d.get("strike", 0)),
                expiration=str(d.get("expiration", "")),
                dte=int(d.get("dte", 0)),
                volume=int(d.get("volume_1d", d.get("volume", 0))),
                open_interest=int(d.get("open_interest", 0)),
                bid=float(d.get("bid", 0)),
                ask=float(d.get("ask", 0)),
                last_price=float(d.get("last", d.get("last_price", 0))),
                delta=float(d.get("delta", 0)),
                implied_volatility=float(d.get("implied_volatility", 0)),
                gamma=d.get("gamma"),
                theta=d.get("theta"),
                vega=d.get("vega"),
                whale_score=float(d.get("whale_score", 0)),
                vol_oi_ratio=float(d.get("vol_oi_ratio", 0)),
                is_unusual_activity=bool(d.get("is_unusual_activity", False)),
            )
            rows.append(row)

        with Session(engine) as db:
            db.add_all(rows)
            db.commit()

        return len(rows)

    # ------------------------------------------------------------------
    # Lecture
    # ------------------------------------------------------------------

    def get_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Dernières sessions triées par date décroissante"""
        with Session(engine) as db:
            stmt = (
                select(ScreeningSession)
                .order_by(col(ScreeningSession.created_at).desc())
                .limit(limit)
            )
            sessions = db.exec(stmt).all()
        return [
            {
                "id": s.id,
                "created_at": s.created_at.isoformat(),
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                "status": s.status,
                "symbols": s.symbols,
                "option_type": s.option_type,
                "result_count": s.result_count,
                "duration_seconds": s.duration_seconds,
            }
            for s in sessions
        ]

    def get_session_results(self, session_id: str) -> List[Dict[str, Any]]:
        """Résultats d'une session donnée"""
        with Session(engine) as db:
            stmt = (
                select(ScreeningResult)
                .where(ScreeningResult.session_id == session_id)
                .order_by(col(ScreeningResult.whale_score).desc())
            )
            results = db.exec(stmt).all()
        return [
            {
                "id": r.id,
                "symbol": r.symbol,
                "underlying": r.underlying,
                "option_type": r.option_type,
                "strike": r.strike,
                "expiration": r.expiration,
                "dte": r.dte,
                "volume": r.volume,
                "open_interest": r.open_interest,
                "bid": r.bid,
                "ask": r.ask,
                "last_price": r.last_price,
                "delta": r.delta,
                "implied_volatility": r.implied_volatility,
                "whale_score": r.whale_score,
                "vol_oi_ratio": r.vol_oi_ratio,
                "is_unusual_activity": r.is_unusual_activity,
            }
            for r in results
        ]

    def get_top_opportunities(
        self, min_whale_score: float = 60.0, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Meilleures opportunités toutes sessions confondues"""
        with Session(engine) as db:
            stmt = (
                select(ScreeningResult)
                .where(col(ScreeningResult.whale_score) >= min_whale_score)
                .order_by(col(ScreeningResult.whale_score).desc())
                .limit(limit)
            )
            results = db.exec(stmt).all()
        return [
            {
                "id": r.id,
                "session_id": r.session_id,
                "symbol": r.symbol,
                "option_type": r.option_type,
                "strike": r.strike,
                "expiration": r.expiration,
                "whale_score": r.whale_score,
                "volume": r.volume,
                "open_interest": r.open_interest,
                "implied_volatility": r.implied_volatility,
            }
            for r in results
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Statistiques globales de la base"""
        with Session(engine) as db:
            total_sessions = db.exec(select(ScreeningSession)).all()
            total_results = db.exec(select(ScreeningResult)).all()
            completed = [s for s in total_sessions if s.status == "completed"]
        return {
            "total_sessions": len(total_sessions),
            "completed_sessions": len(completed),
            "total_opportunities_stored": len(total_results),
            "db_path": str(engine.url),
        }


# Singleton
persistence_service = PersistenceService()
