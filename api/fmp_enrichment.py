"""
FMP Enrichment — Company Profile, Key Metrics TTM, Insider Trading.

Endpoints exposed:
  GET /api/fmp/profiles?symbols=AAPL,TSLA,...   (batch, cache 24h)
  GET /api/fmp/metrics?symbols=AAPL,TSLA,...    (per-sym, cache 24h)
  GET /api/fmp/insider?symbols=AAPL,TSLA,...    (per-sym, cache 4h)
  GET /api/fmp/cache/status

Internal helpers (used by hybrid_screening_service):
  get_profiles(symbols)       → {SYM: ProfileData}
  get_key_metrics(symbols)    → {SYM: MetricsData}
  get_insider_activity(symbols) → {SYM: InsiderData}

Quota strategy (FMP free tier = 250 req/day):
  - Profile: 1 batch call per scan run (comma-separated symbols) ≈ 5/day
  - Key metrics: per-symbol with 24h cache → ~50 first scan, 0 after
  - Insider: per-symbol with 4h cache → ~50 first scan, small after
  - Universe + Earnings: ≈ 14/day
  Total: ~69 first scan of day, ~14 after → well within 250 limit
"""

import asyncio
import logging
import os
import time
from datetime import date, timedelta
from typing import Any

import httpx
from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)

fmp_enrichment_router = APIRouter(prefix="/api/fmp", tags=["fmp-enrichment"])

_FMP_STABLE = "https://financialmodelingprep.com/stable"

# ── Per-symbol caches ──────────────────────────────────────────────────────────
# Each: { "SYM": {"data": {...}, "ts": float}, ... }
_profile_cache: dict = {}
_metrics_cache: dict = {}
_insider_cache: dict = {}

_TTL_PROFILE = 24 * 3600  # sector/beta rarely change
_TTL_METRICS = 24 * 3600  # TTM metrics, daily refresh enough
_TTL_INSIDER = 4 * 3600  # insider filings trickle through the day

# ── Daily quota tracker (FMP free tier = 250 req/day) ─────────────────────────
_quota: dict = {"date": "", "calls": 0}
_DAILY_LIMIT = 250


def _bump_quota() -> None:
    """Increment today's FMP request counter (auto-reset at midnight)."""
    today = date.today().isoformat()
    if _quota["date"] != today:
        _quota["date"] = today
        _quota["calls"] = 0
    _quota["calls"] += 1
    if _quota["calls"] % 10 == 0:
        remaining = max(0, _DAILY_LIMIT - _quota["calls"])
        logger.info(
            f"📊 FMP quota: {_quota['calls']}/{_DAILY_LIMIT} used today ({remaining} remaining)"
        )


# ── FMP key helper ─────────────────────────────────────────────────────────────


def _api_key() -> str:
    k = os.getenv("FMP_API_KEY", "")
    if not k:
        raise ValueError("FMP_API_KEY not set")
    return k


def _alive(cache: dict, sym: str, ttl: float) -> bool:
    entry = cache.get(sym)
    return bool(entry and (time.time() - entry["ts"]) < ttl)


# ══════════════════════════════════════════════════════════════════════════════
# 1. COMPANY PROFILE  /stable/profile?symbol=SYM1,SYM2,...
# ══════════════════════════════════════════════════════════════════════════════


def _parse_profile(raw: dict) -> dict:
    """Extract the fields we care about from a FMP profile item."""
    mkt = raw.get("marketCap") or raw.get("mktCap") or 0  # stable API uses marketCap
    if mkt >= 200e9:
        cap_label = "Mega"
    elif mkt >= 10e9:
        cap_label = "Large"
    elif mkt >= 2e9:
        cap_label = "Mid"
    elif mkt > 0:
        cap_label = "Small"
    else:
        cap_label = ""

    return {
        "sector": raw.get("sector") or "",
        "industry": raw.get("industry") or "",
        "beta": raw.get("beta"),
        "mkt_cap": mkt,
        "cap_label": cap_label,
        "description": (raw.get("description") or "")[:200],
        "ceo": raw.get("ceo") or "",
        "country": raw.get("country") or "",
    }


async def _fetch_profiles_batch(symbols: list[str]) -> dict:
    """One FMP call for up to ~50 comma-separated symbols."""
    url = f"{_FMP_STABLE}/profile"
    params = {"symbol": ",".join(symbols), "apikey": _api_key()}

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, params=params)

    if resp.status_code == 401:
        raise ValueError("FMP_API_KEY invalid (401)")
    if resp.status_code == 429:
        raise ValueError("FMP rate limit (429)")
    resp.raise_for_status()

    raw_list = resp.json()
    if not isinstance(raw_list, list):
        raise ValueError(f"Unexpected profile response: {type(raw_list)}")

    result = {}
    for item in raw_list:
        sym = (item.get("symbol") or "").upper().strip()
        if sym:
            result[sym] = _parse_profile(item)
    logger.debug(f"Profile batch {len(symbols)} requested → {len(result)} returned")
    return result


async def _fetch_profile_one(sym: str) -> dict:
    """Single-symbol fallback for free-tier FMP."""
    url = f"{_FMP_STABLE}/profile"
    params = {"symbol": sym, "apikey": _api_key()}
    _bump_quota()
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
    if resp.status_code in (401, 429):
        raise ValueError(f"FMP {resp.status_code} for profile/{sym}")
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, list) and data:
        return _parse_profile(data[0])
    return {}


async def get_profiles(symbols: list[str]) -> dict:
    """
    Return {SYM: profile_dict} for all symbols.
    New FMP stable API only supports single-symbol calls — fetch concurrently.
    Non-blocking — returns partial results on failure.
    """
    syms = [s.upper() for s in symbols if s]
    missing = [s for s in syms if not _alive(_profile_cache, s, _TTL_PROFILE)]

    if missing:
        sem = asyncio.Semaphore(10)

        async def _fetch(sym: str) -> None:
            async with sem:
                try:
                    d = await _fetch_profile_one(sym)
                    _profile_cache[sym] = {"data": d, "ts": time.time()}
                except Exception as exc:
                    logger.debug(f"profile/{sym}: {exc}")
                    _profile_cache[sym] = {"data": {}, "ts": time.time()}

        await asyncio.gather(*[_fetch(s) for s in missing])

        filled = sum(
            1
            for s in missing
            if _profile_cache.get(s, {}).get("data", {}).get("beta") is not None
        )
        logger.info(
            f"📊 Profiles: {len(missing)} symbols — beta filled: {filled}/{len(missing)}"
        )

    return {s: _profile_cache[s]["data"] for s in syms if s in _profile_cache}


# ══════════════════════════════════════════════════════════════════════════════
# 2. KEY METRICS (RATIOS TTM)  /stable/ratios-ttm?symbol={sym}
# ══════════════════════════════════════════════════════════════════════════════


def _parse_metrics(raw: dict) -> dict:
    # stable API uses different field names in ratios-ttm vs old v3/key-metrics-ttm
    pe = raw.get("priceToEarningsRatioTTM") or raw.get("peRatioTTM")
    pb = raw.get("priceToBookRatioTTM")
    de = raw.get("debtToEquityRatioTTM") or raw.get("debtToEquityTTM")
    roe = raw.get("returnOnEquityTTM") or raw.get("roeTTM")
    fcf_yield = raw.get("freeCashFlowYieldTTM")
    div_yield = raw.get("dividendYieldTTM") or raw.get("dividendYieldPercentageTTM")

    return {
        "pe_ratio": round(pe, 2) if pe else None,
        "pb_ratio": round(pb, 2) if pb else None,
        "debt_to_equity": round(de, 2) if de else None,
        "roe": round(roe * 100, 1) if roe else None,  # as %
        "fcf_yield": round(fcf_yield * 100, 2) if fcf_yield else None,
        "div_yield": round(div_yield, 4) if div_yield else None,
    }


async def _fetch_metrics_one(sym: str) -> dict:
    url = f"{_FMP_STABLE}/ratios-ttm"
    params = {"symbol": sym, "apikey": _api_key()}
    _bump_quota()
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)

    if resp.status_code in (401, 429):
        raise ValueError(f"FMP {resp.status_code} for metrics/{sym}")
    resp.raise_for_status()

    data = resp.json()
    if isinstance(data, list) and data:
        return _parse_metrics(data[0])
    return {}


async def get_key_metrics(symbols: list[str]) -> dict:
    """
    Return {SYM: metrics_dict}. Per-symbol cache 24h.
    Fetches missing symbols concurrently (max 10 at a time).
    Non-blocking.
    """
    syms = [s.upper() for s in symbols if s]
    missing = [s for s in syms if not _alive(_metrics_cache, s, _TTL_METRICS)]

    if missing:
        # Concurrently fetch, max 10 at a time to stay polite
        sem = asyncio.Semaphore(10)

        async def _fetch(sym: str):
            async with sem:
                try:
                    data = await _fetch_metrics_one(sym)
                    _metrics_cache[sym] = {"data": data, "ts": time.time()}
                except Exception as exc:
                    logger.debug(f"metrics/{sym}: {exc}")
                    _metrics_cache[sym] = {"data": {}, "ts": time.time()}

        await asyncio.gather(*[_fetch(s) for s in missing])
        logger.info(f"📈 Key metrics: fetched {len(missing)} symbols from FMP")

    return {s: _metrics_cache[s]["data"] for s in syms if s in _metrics_cache}


# ══════════════════════════════════════════════════════════════════════════════
# 3. INSIDER TRADING  /stable/insider-trading/search?symbol={sym}&limit=20
# ══════════════════════════════════════════════════════════════════════════════

# Cutoff: consider transactions in the last N days
_INSIDER_WINDOW_DAYS = 30

# FMP transaction type codes → direction
_BUY_CODES = {"P-Purchase", "A-Award", "M-Exempt"}
_SELL_CODES = {"S-Sale", "S-Sale+OE", "S-Sale+Disposition", "D-Return"}


def _parse_insider(raw_list: list[dict]) -> dict:
    cutoff = date.today() - timedelta(days=_INSIDER_WINDOW_DAYS)
    buys = 0
    sells = 0
    buy_shares = 0
    sell_shares = 0
    total = 0

    for item in raw_list:
        try:
            d = date.fromisoformat(item.get("transactionDate", "2000-01-01"))
        except ValueError:
            continue
        if d < cutoff:
            continue

        tx_type = item.get("transactionType", "")
        shares = abs(item.get("securitiesTransacted") or 0)
        total += 1

        if tx_type in _BUY_CODES:
            buys += 1
            buy_shares += shares
        elif tx_type in _SELL_CODES:
            sells += 1
            sell_shares += shares

    # Signal
    if buys == 0 and sells == 0:
        signal = "neutral"
        icon = "⚪"
    elif buys >= sells * 2:
        signal = "bullish"
        icon = "🟢"
    elif sells >= buys * 2:
        signal = "bearish"
        icon = "🔴"
    else:
        signal = "mixed"
        icon = "🟡"

    return {
        "signal": signal,
        "icon": icon,
        "buys": buys,
        "sells": sells,
        "buy_shares": buy_shares,
        "sell_shares": sell_shares,
        "recent_count": total,
    }


async def _fetch_insider_one(sym: str) -> dict:
    url = f"{_FMP_STABLE}/insider-trading/search"
    params = {"symbol": sym, "limit": 20, "apikey": _api_key()}
    _bump_quota()
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)

    if resp.status_code in (401, 402, 403, 429):
        raise ValueError(
            f"FMP {resp.status_code}: insider-trading not available (paid feature)"
        )
    resp.raise_for_status()

    data = resp.json()
    if isinstance(data, list):
        return _parse_insider(data)
    return {
        "signal": "neutral",
        "icon": "⚪",
        "buys": 0,
        "sells": 0,
        "buy_shares": 0,
        "sell_shares": 0,
        "recent_count": 0,
    }


async def get_insider_activity(symbols: list[str]) -> dict:
    """
    Return {SYM: insider_dict}. Per-symbol cache 4h.
    Fetches missing symbols concurrently (max 5 at a time).
    Non-blocking.
    """
    syms = [s.upper() for s in symbols if s]
    missing = [s for s in syms if not _alive(_insider_cache, s, _TTL_INSIDER)]

    if missing:
        sem = asyncio.Semaphore(5)

        async def _fetch(sym: str):
            async with sem:
                try:
                    data = await _fetch_insider_one(sym)
                    _insider_cache[sym] = {"data": data, "ts": time.time()}
                except Exception as exc:
                    logger.debug(f"insider/{sym}: {exc}")
                    _insider_cache[sym] = {
                        "data": {
                            "signal": "neutral",
                            "icon": "⚪",
                            "buys": 0,
                            "sells": 0,
                            "buy_shares": 0,
                            "sell_shares": 0,
                            "recent_count": 0,
                        },
                        "ts": time.time(),
                    }

        await asyncio.gather(*[_fetch(s) for s in missing])
        logger.info(f"👤 Insider: fetched {len(missing)} symbols from FMP")

    return {s: _insider_cache[s]["data"] for s in syms if s in _insider_cache}


# ══════════════════════════════════════════════════════════════════════════════
# FASTAPI ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════


def _parse_symbols(raw: str) -> list[str]:
    return [s.strip().upper() for s in raw.split(",") if s.strip()]


@fmp_enrichment_router.get("/profiles")
async def endpoint_profiles(
    symbols: str = Query(..., description="Comma-separated tickers")
):
    syms = _parse_symbols(symbols)
    data = await get_profiles(syms)
    return {"profiles": data, "count": len(data)}


@fmp_enrichment_router.get("/metrics")
async def endpoint_metrics(
    symbols: str = Query(..., description="Comma-separated tickers")
):
    syms = _parse_symbols(symbols)
    data = await get_key_metrics(syms)
    return {"metrics": data, "count": len(data)}


@fmp_enrichment_router.get("/insider")
async def endpoint_insider(
    symbols: str = Query(..., description="Comma-separated tickers")
):
    syms = _parse_symbols(symbols)
    data = await get_insider_activity(syms)
    return {"insider": data, "count": len(data)}


@fmp_enrichment_router.get("/cache/status")
async def endpoint_cache_status():
    now = time.time()

    def _summary(cache: dict, ttl: float) -> dict:
        live = sum(1 for v in cache.values() if (now - v["ts"]) < ttl)
        return {"total": len(cache), "live": live, "stale": len(cache) - live}

    remaining = max(0, _DAILY_LIMIT - _quota["calls"])
    return {
        "profiles": _summary(_profile_cache, _TTL_PROFILE),
        "metrics": _summary(_metrics_cache, _TTL_METRICS),
        "insider": _summary(_insider_cache, _TTL_INSIDER),
        "quota": {
            "date": _quota["date"] or date.today().isoformat(),
            "calls_today": _quota["calls"],
            "daily_limit": _DAILY_LIMIT,
            "remaining": remaining,
            "pct_used": round(_quota["calls"] / _DAILY_LIMIT * 100, 1),
        },
    }
