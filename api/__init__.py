"""
Package API - Interface FastAPI moderne
Remplace Streamlit par une API REST + WebSocket

Point d'entrée canonical: app.py (racine)
Ce package expose les routers (hybrid, short_interest, filtering).
"""

# Lazy import to avoid FastAPI initialization issues during module imports
# Only import app when explicitly requested (e.g. from api import app)
# This prevents circular chains when importing other modules from api package


def __getattr__(name: str):
    """Lazy import for backward compatibility"""
    if name == "app":
        try:
            from app import app

            return app
        except ImportError:
            from .main import app

            return app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["app"]
