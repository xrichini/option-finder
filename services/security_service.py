"""
Middleware de sécurité - API Key optionnelle + Rate Limiting via slowapi

Activation:
  - API Key : définir API_KEY=<secret> dans .env
              puis passer le header  X-API-Key: <secret>  dans chaque requête.
              Si API_KEY n'est pas défini, l'auth est désactivée (dev mode).
  - Rate limiting : actif par défaut (100 req/min par IP).
                    Configurable via RATE_LIMIT_PER_MINUTE dans .env.
"""

from __future__ import annotations

import os
import logging
from typing import Optional

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (lue depuis .env via dotenv, déjà chargé dans app.py)
# ---------------------------------------------------------------------------
_API_KEY: Optional[str] = os.getenv("API_KEY") or None
_SKIP_AUTH_ON_DOCS = True  # Toujours laisser passer /api/docs et /api/redoc

# Routes publiques (jamais bloquées même si API_KEY est définie)
_PUBLIC_PREFIXES = [
    "/",
    "/static",
    "/ui",
    "/api/docs",
    "/api/redoc",
    "/openapi.json",
    "/api/status",
    "/ws",
]


def _is_public(path: str) -> bool:
    return any(
        path == p or path.startswith(p + "/") or path.startswith(p + "?")
        for p in _PUBLIC_PREFIXES
    )


# ---------------------------------------------------------------------------
# Middleware FastAPI (Starlette BaseHTTPMiddleware)
# ---------------------------------------------------------------------------
from starlette.middleware.base import BaseHTTPMiddleware


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Vérifie le header X-API-Key sur chutes API protégées.
    - Si API_KEY n'est pas configuré → authentification désactivée (mode dev)
    - Les routes publiques listées dans _PUBLIC_PREFIXES sont toujours accessibles
    """

    async def dispatch(self, request: Request, call_next):
        if not _API_KEY:
            # Mode développement : aucune clé requise
            return await call_next(request)

        path = request.url.path
        if _is_public(path):
            return await call_next(request)

        provided_key = request.headers.get("X-API-Key") or request.query_params.get(
            "api_key"
        )

        if not provided_key:
            logger.warning(f"Requête non autorisée (pas de clé): {path}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing X-API-Key header"},
                headers={"WWW-Authenticate": "ApiKey"},
            )

        if provided_key != _API_KEY:
            logger.warning(f"Requête non autorisée (clé invalide): {path}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Invalid API key"},
            )

        return await call_next(request)


# ---------------------------------------------------------------------------
# Rate Limiting avec slowapi (optionnel - graceful degradation si absent)
# ---------------------------------------------------------------------------
_RATE_LIMIT = os.getenv("RATE_LIMIT_PER_MINUTE", "100")

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded

    limiter = Limiter(
        key_func=get_remote_address, default_limits=[f"{_RATE_LIMIT}/minute"]
    )
    RATE_LIMITING_AVAILABLE = True
    logger.info(f"Rate limiting activé: {_RATE_LIMIT} req/min par IP")

except ImportError:
    limiter = None  # type: ignore
    RATE_LIMITING_AVAILABLE = False
    logger.info("slowapi non installé - rate limiting désactivé (pip install slowapi)")


def setup_security(app) -> None:
    """
    Applique le middleware d'authentification et le rate limiter à l'app FastAPI.
    À appeler après la création de l'app, avant de démarrer uvicorn.
    """
    # API Key middleware
    app.add_middleware(APIKeyMiddleware)

    if _API_KEY:
        logger.info(f"API Key auth activée (clé chargée depuis .env)")
    else:
        logger.info("API Key auth désactivée (définir API_KEY dans .env pour activer)")

    # Rate limiting
    if RATE_LIMITING_AVAILABLE and limiter is not None:
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        logger.info(f"Rate limiting configuré: {_RATE_LIMIT} req/min")
