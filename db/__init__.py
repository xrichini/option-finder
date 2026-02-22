"""
Base de données SQLite avec SQLModel
Stockage persistant des sessions et résultats de screening
"""

from sqlmodel import SQLModel, create_engine, Session
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Chemin de la base de données (créée à la racine du projet)
DB_PATH = Path(__file__).parent.parent / "data" / "squeeze_finder.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    """Crée toutes les tables si elles n'existent pas encore"""
    from db.models import ScreeningSession, ScreeningResult  # noqa: F401

    SQLModel.metadata.create_all(engine)
    logger.info(f"Base de données initialisée: {DB_PATH}")


def get_session():
    """Générateur de session DB (pour injection de dépendance FastAPI)"""
    with Session(engine) as session:
        yield session
