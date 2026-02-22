"""
Earnings Calendar endpoint — backed by FMP, non-blocking.
GET /api/earnings/upcoming?days=7
Returns { "earnings": { "AAPL": { "date": "2026-02-24", "timing": "AMC" }, ... },
          "source": "fmp"|"empty",
          "cached": bool }
"""

import logging
import os
import time
from datetime import date, timedelta

import httpx
from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)

earnings_router = APIRouter(prefix="/api/earnings", tags=["earnings"])

# ── In-memory cache ────────────────────────────────────────────────────────────
_cache: dict = {}  # { "data": {...}, "ts": float }
_CACHE_TTL = 4 * 3600  # 4 h — refresh a few times per trading day


def _cached() -> dict | None:
    if _cache and (time.time() - _cache["ts"]) < _CACHE_TTL:
        return _cache["data"]
    return None


def _store(data: dict) -> None:
    _cache["data"] = data
    _cache["ts"] = time.time()


# ── Helpers ────────────────────────────────────────────────────────────────────


def _normalise_timing(raw: str) -> str:
    """Normalise FMP time field → 'BMO' | 'AMC' | '--'."""
    r = (raw or "").lower().strip()
    if r in ("bmo", "before market open", "pre market"):
        return "BMO"
    if r in ("amc", "after market close", "after hours"):
        return "AMC"
    return "--"


async def _fetch_fmp(days: int) -> dict:
    """
    Call FMP /v3/earnings_calendar and return {SYMBOL: {date, timing}}.
    Raises on any error so the caller can fall back gracefully.
    """
    api_key = os.getenv("FMP_API_KEY", "")
    if not api_key:
        raise ValueError("FMP_API_KEY not set")

    today = date.today()
    to_date = today + timedelta(days=days)
    url = (
        f"https://financialmodelingprep.com/stable/earnings-calendar"
        f"?from={today}&to={to_date}&apikey={api_key}"
    )

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)

    if resp.status_code == 401:
        raise ValueError("FMP_API_KEY invalid (401)")
    if resp.status_code == 429:
        raise ValueError("FMP rate limit hit (429)")
    resp.raise_for_status()

    raw = resp.json()
    if not isinstance(raw, list):
        raise ValueError(f"Unexpected FMP response type: {type(raw)}")

    result: dict = {}
    for item in raw:
        sym = (item.get("symbol") or "").strip().upper()
        if not sym:
            continue
        result[sym] = {
            "date": item.get("date", ""),
            "timing": _normalise_timing(item.get("time", "")),
        }

    logger.info(f"📅 Earnings: {len(result)} symbols from FMP ({today} → {to_date})")
    return result


# ── Endpoint ───────────────────────────────────────────────────────────────────


@earnings_router.get("/upcoming")
async def get_upcoming_earnings(
    days: int = Query(
        default=7, ge=1, le=30, description="Look-ahead window in calendar days"
    ),
    force_refresh: bool = Query(default=False),
):
    """
    Return earnings events in the next `days` calendar days.
    Non-blocking: returns empty dict on failure rather than raising.
    """
    if not force_refresh:
        cached = _cached()
        if cached is not None:
            return {
                "earnings": cached,
                "source": "cache",
                "cached": True,
                "count": len(cached),
            }

    try:
        data = await _fetch_fmp(days)
        _store(data)
        return {"earnings": data, "source": "fmp", "cached": False, "count": len(data)}

    except Exception as exc:
        logger.warning(f"⚠️  Earnings calendar unavailable: {exc} — returning empty set")
        return {
            "earnings": {},
            "source": "empty",
            "cached": False,
            "count": 0,
            "error": str(exc),
        }


# ── Utility for internal use ───────────────────────────────────────────────────


async def get_earnings_map(days: int = 7) -> dict:
    """
    Called by the hybrid screening service to enrich scan results.
    Always returns a dict (possibly empty) — never raises.
    """
    cached = _cached()
    if cached is not None:
        return cached

    try:
        data = await _fetch_fmp(days)
        _store(data)
        return data
    except Exception as exc:
        logger.warning(f"⚠️  get_earnings_map failed: {exc}")
        return {}
