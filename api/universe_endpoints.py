"""Universe Endpoints — S&P 500, Nasdaq 100 & DOW 30.

Stratégie de fetch (dans l'ordre) :
  1. Financial Modeling Prep API  (FMP_API_KEY dans .env)
  2. Fallback Wikipedia scraping
Cache mémoire 24h.
"""

import os
import time
import logging
import requests
from fastapi import APIRouter
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

universe_router = APIRouter(prefix="/api/universe", tags=["universe"])

# ---------------------------------------------------------------------------
# Cache in-memory : { "sp500": {"symbols": [...], "ts": float, "source": str} }
# ---------------------------------------------------------------------------
_CACHE: dict = {}
_CACHE_TTL = 86400  # 24 h

# ---------------------------------------------------------------------------
# URLs
# ---------------------------------------------------------------------------
_FMP_BASE = "https://financialmodelingprep.com/api/v3"
_FMP_ENDPOINTS = {
    "sp500": f"{_FMP_BASE}/sp500_constituent",
    "nasdaq100": f"{_FMP_BASE}/nasdaq_constituent",
    "dow30": f"{_FMP_BASE}/dowjones_constituent",
}

_WIKI_URLS = {
    "sp500": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
    "nasdaq100": "https://en.wikipedia.org/wiki/Nasdaq-100",
    "dow30": "https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average",
}

# Sanity-check bounds : (min, max) tickers attendus
_BOUNDS = {
    "sp500": (490, 510),
    "nasdaq100": (95, 110),
    "dow30": (25, 35),
}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ---------------------------------------------------------------------------
# Helpers cache
# ---------------------------------------------------------------------------


def _cached(key: str) -> Optional[List[str]]:
    entry = _CACHE.get(key)
    if entry and (time.time() - entry["ts"]) < _CACHE_TTL:
        return entry["symbols"]
    return None


def _store(key: str, symbols: List[str], source: str) -> None:
    _CACHE[key] = {"symbols": symbols, "ts": time.time(), "source": source}


def _normalize(symbols: List[str]) -> List[str]:
    """Nettoyage commun : strip, BRK.B → BRK-B (Tradier format), filtre longueur."""
    out = []
    for s in symbols:
        s = str(s).strip().replace(".", "-")
        if s and s.lower() != "nan" and 1 <= len(s) <= 6:
            out.append(s)
    return out


# ---------------------------------------------------------------------------
# FMP fetch (source primaire)
# ---------------------------------------------------------------------------


def _fetch_fmp(universe: str) -> List[str]:
    """
    Récupère les constituants via Financial Modeling Prep.
    Lève ValueError si clé absente ou réponse invalide.
    """
    api_key = os.getenv("FMP_API_KEY", "")
    if not api_key:
        raise ValueError("FMP_API_KEY non défini dans .env")

    url = _FMP_ENDPOINTS[universe]
    resp = requests.get(url, params={"apikey": api_key}, timeout=15)

    if resp.status_code == 401:
        raise ValueError("FMP_API_KEY invalide ou expiré (HTTP 401)")
    if resp.status_code == 429:
        raise ValueError("FMP rate-limit atteint (HTTP 429)")
    resp.raise_for_status()

    data = resp.json()
    if not isinstance(data, list):
        raise ValueError(f"Réponse FMP inattendue pour {universe}: {type(data)}")

    symbols = _normalize([row.get("symbol", "") for row in data])

    lo, hi = _BOUNDS[universe]
    if not (lo <= len(symbols) <= hi):
        raise ValueError(
            f"FMP {universe}: {len(symbols)} tickers reçus, attendu {lo}–{hi}"
        )

    logger.info(f"✅ FMP {universe}: {len(symbols)} tickers")
    return symbols


# ---------------------------------------------------------------------------
# Wikipedia fallback
# ---------------------------------------------------------------------------


def _fetch_wikipedia(universe: str) -> List[str]:
    """Scrape Wikipedia comme source de secours."""
    import pandas as pd
    from io import StringIO

    url = _WIKI_URLS[universe]
    resp = requests.get(url, headers=_HEADERS, timeout=15)
    resp.raise_for_status()
    tables = pd.read_html(StringIO(resp.text), header=0)

    lo, hi = _BOUNDS[universe]

    for df in tables:
        cols_lower = [c.lower() for c in df.columns]
        if any("symbol" in c or "ticker" in c for c in cols_lower):
            col = next(
                c for c in df.columns if "symbol" in c.lower() or "ticker" in c.lower()
            )
            symbols = _normalize(df[col].tolist())
            if lo <= len(symbols) <= hi:
                logger.info(f"✅ Wikipedia {universe}: {len(symbols)} tickers")
                return symbols

    raise ValueError(
        f"Table {universe} introuvable sur Wikipedia (aucune table valide)"
    )


# ---------------------------------------------------------------------------
# Orchestrateur : FMP → Wikipedia → erreur
# ---------------------------------------------------------------------------


def _fetch_universe(universe: str) -> Tuple[List[str], str]:
    """
    Retourne (symbols, source).
    Essaie FMP d'abord ; en cas d'erreur, tente Wikipedia.
    """
    errors = []

    # 1. FMP
    try:
        return _fetch_fmp(universe), "fmp"
    except Exception as e:
        errors.append(f"FMP: {e}")
        logger.warning(f"⚠️  FMP {universe} indisponible, fallback Wikipedia — {e}")

    # 2. Wikipedia
    try:
        return _fetch_wikipedia(universe), "wikipedia"
    except Exception as e:
        errors.append(f"Wikipedia: {e}")
        logger.error(f"❌ Wikipedia {universe} aussi en échec — {e}")

    raise RuntimeError(
        f"Impossible de récupérer {universe}. Erreurs: {' | '.join(errors)}"
    )


# ---------------------------------------------------------------------------
# Logique commune aux endpoints
# ---------------------------------------------------------------------------


def _universe_endpoint(universe: str, force_refresh: bool) -> dict:
    if not force_refresh:
        cached = _cached(universe)
        if cached:
            entry = _CACHE[universe]
            return {
                "universe": universe,
                "symbols": cached,
                "count": len(cached),
                "cached": True,
                "source": entry.get("source", "cache"),
                "cache_age_h": round((time.time() - entry["ts"]) / 3600, 1),
            }
    try:
        symbols, source = _fetch_universe(universe)
        _store(universe, symbols, source)
        return {
            "universe": universe,
            "symbols": symbols,
            "count": len(symbols),
            "cached": False,
            "source": source,
        }
    except Exception as e:
        logger.error(f"Erreur finale {universe}: {e}")
        return {"error": str(e), "universe": universe, "symbols": [], "count": 0}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@universe_router.get("/sp500")
async def get_sp500(force_refresh: bool = False):
    """Retourne les ~500 tickers S&P 500 (cache 24h). FMP → Wikipedia."""
    return _universe_endpoint("sp500", force_refresh)


@universe_router.get("/nasdaq100")
async def get_nasdaq100(force_refresh: bool = False):
    """Retourne les ~100 tickers Nasdaq-100 (cache 24h). FMP → Wikipedia."""
    return _universe_endpoint("nasdaq100", force_refresh)


@universe_router.get("/dow30")
async def get_dow30(force_refresh: bool = False):
    """Retourne les 30 tickers DOW Jones (cache 24h). FMP → Wikipedia."""
    return _universe_endpoint("dow30", force_refresh)


@universe_router.get("/cache/status")
async def cache_status():
    """État du cache mémoire universes."""
    result = {}
    for key, entry in _CACHE.items():
        age_s = time.time() - entry["ts"]
        result[key] = {
            "count": len(entry["symbols"]),
            "source": entry.get("source", "unknown"),
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
