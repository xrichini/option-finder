"""
Package API - Interface FastAPI moderne
Remplace Streamlit par une API REST + WebSocket

Point d'entrée canonical: app.py (racine)
Ce package expose les routers (hybrid, short_interest, filtering).
"""

# Re-export de l'app principale pour compatibilité ascendante
try:
    from app import app  # noqa: F401  (root app.py)
except ImportError:
    from .main import app  # noqa: F401  (fallback)

__all__ = ["app"]
