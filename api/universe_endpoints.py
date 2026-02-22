"""
Universe Endpoints — S&P 500 & Nasdaq 100 depuis Wikipedia
Cache mémoire 24h pour éviter les requêtes répétées.
"""

import time
import logging
import requests
from fastapi import APIRouter
from typing import List, Optional

logger = logging.getLogger(__name__)

universe_router = APIRouter(prefix="/api/universe", tags=["universe"])

# ---------------------------------------------------------------------------
# Cache in-memory : { "sp500": {"symbols": [...], "ts": float}, ... }
# ---------------------------------------------------------------------------
_CACHE: dict = {}
_CACHE_TTL = 86400  # 24h en secondes

SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
NASDAQ100_URL = "https://en.wikipedia.org/wiki/Nasdaq-100"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cached(key: str) -> Optional[List[str]]:
    entry = _CACHE.get(key)
    if entry and (time.time() - entry["ts"]) < _CACHE_TTL:
        return entry["symbols"]
    return None


def _store(key: str, symbols: List[str]) -> None:
    _CACHE[key] = {"symbols": symbols, "ts": time.time()}


def _fetch_sp500() -> List[str]:
    """Scrape la première table Wikipedia de la liste S&P 500."""
    try:
        import pandas as pd
        from io import StringIO

        resp = requests.get(SP500_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        tables = pd.read_html(StringIO(resp.text), header=0)
        df = tables[0]
        # Colonne ticker : "Symbol" ou "Ticker symbol"
        col = next((c for c in df.columns if "symbol" in c.lower()), df.columns[0])
        symbols = (
            df[col]
            .astype(str)
            .str.strip()
            .str.replace(".", "-", regex=False)  # BRK.B → BRK-B (Tradier format)
            .tolist()
        )
        symbols = [s for s in symbols if s and len(s) <= 6]
        logger.info(f"📋 S&P 500 : {len(symbols)} tickers depuis Wikipedia")
        return symbols
    except Exception as e:
        logger.error(f"Erreur fetch S&P 500 : {e}")
        raise


def _fetch_nasdaq100() -> List[str]:
    """Scrape la table des composantes Nasdaq-100 depuis Wikipedia."""
    try:
        import pandas as pd
        from io import StringIO

        resp = requests.get(NASDAQ100_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        tables = pd.read_html(StringIO(resp.text), header=0)
        # La table des composantes contient "Ticker" ou "Symbol"
        for df in tables:
            cols_lower = [c.lower() for c in df.columns]
            if any("ticker" in c or "symbol" in c for c in cols_lower):
                col = next(
                    c
                    for c in df.columns
                    if "ticker" in c.lower() or "symbol" in c.lower()
                )
                symbols = (
                    df[col]
                    .astype(str)
                    .str.strip()
                    .str.replace(".", "-", regex=False)
                    .tolist()
                )
                symbols = [s for s in symbols if s and len(s) <= 6]
                if len(symbols) >= 90:
                    logger.info(
                        f"📋 Nasdaq-100 : {len(symbols)} tickers depuis Wikipedia"
                    )
                    return symbols
        raise ValueError("Table Nasdaq-100 introuvable dans la page Wikipedia")
    except Exception as e:
        logger.error(f"Erreur fetch Nasdaq-100 : {e}")
        raise


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@universe_router.get("/sp500")
async def get_sp500(force_refresh: bool = False):
    """
    Retourne la liste des tickers S&P 500 (cache 24h).
    Paramètre : force_refresh=true pour ignorer le cache.
    """
    if not force_refresh:
        cached = _cached("sp500")
        if cached:
            return {
                "universe": "sp500",
                "symbols": cached,
                "count": len(cached),
                "cached": True,
                "cache_age_h": round((time.time() - _CACHE["sp500"]["ts"]) / 3600, 1),
            }
    try:
        symbols = _fetch_sp500()
        _store("sp500", symbols)
        return {
            "universe": "sp500",
            "symbols": symbols,
            "count": len(symbols),
            "cached": False,
            "source": "wikipedia",
        }
    except Exception as e:
        return {"error": str(e), "universe": "sp500", "symbols": [], "count": 0}


@universe_router.get("/nasdaq100")
async def get_nasdaq100(force_refresh: bool = False):
    """
    Retourne la liste des tickers Nasdaq-100 (cache 24h).
    """
    if not force_refresh:
        cached = _cached("nasdaq100")
        if cached:
            return {
                "universe": "nasdaq100",
                "symbols": cached,
                "count": len(cached),
                "cached": True,
                "cache_age_h": round(
                    (time.time() - _CACHE["nasdaq100"]["ts"]) / 3600, 1
                ),
            }
    try:
        symbols = _fetch_nasdaq100()
        _store("nasdaq100", symbols)
        return {
            "universe": "nasdaq100",
            "symbols": symbols,
            "count": len(symbols),
            "cached": False,
            "source": "wikipedia",
        }
    except Exception as e:
        return {"error": str(e), "universe": "nasdaq100", "symbols": [], "count": 0}


@universe_router.get("/cache/status")
async def cache_status():
    """État du cache mémoire universes."""
    result = {}
    for key, entry in _CACHE.items():
        age_s = time.time() - entry["ts"]
        result[key] = {
            "count": len(entry["symbols"]),
            "age_h": round(age_s / 3600, 2),
            "expires_in_h": round((_CACHE_TTL - age_s) / 3600, 2),
            "valid": age_s < _CACHE_TTL,
        }
    return {"cache": result}


@universe_router.delete("/cache")
async def clear_cache():
    """Vide le cache — force re-fetch au prochain appel."""
    _CACHE.clear()
    return {"status": "cleared"}
