"""
Live quotes refresh — volatile option fields only.

POST /api/quotes/refresh
  body: {
    "option_symbols":     ["AAPL250321C00200000", ...],
    "underlying_symbols": ["AAPL", ...]
  }
  returns: {
    "options": {
      "AAPL250321C00200000": {
        "volume": 1234, "open_interest": 5678,
        "delta": -0.42, "implied_volatility": 0.45,
        "change_pct": 2.3
      }
    },
    "underlyings": {
      "AAPL": {"stock_volume": 45000000, "last": 213.5}
    },
    "refreshed_at": "2026-02-23T14:30:00"
  }

Design principles:
  - ONE Tradier call for everything (options + underlyings mixed in ?symbols)
  - NO FMP, NO scoring — strictly market-data volatiles
  - Max 100 symbols per call (Tradier limit)
  - Non-blocking: returns empty dicts on error, never raises
"""

import logging
from datetime import datetime

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from utils.config import Config

logger = logging.getLogger(__name__)

quotes_refresh_router = APIRouter(prefix="/api/quotes", tags=["quotes-refresh"])

_MAX_SYMBOLS = 100  # Tradier hard limit per request

# Fields that are truly static (never refreshed here):
#   sector, beta, insider, earnings, iv_rank, vol_trend_ratio,
#   whale_score, hybrid_score, sizzle_index (needs avg_vol history)


class QuotesRefreshRequest(BaseModel):
    option_symbols: list[str] = []
    underlying_symbols: list[str] = []


def _tradier_headers() -> dict:
    key = Config.get_tradier_api_key()
    return {"Authorization": f"Bearer {key}", "Accept": "application/json"}


def _tradier_quotes_url() -> str:
    return f"{Config.get_tradier_base_url()}/markets/quotes"


def _is_option_symbol(sym: str) -> bool:
    """
    OCC option symbols are 15+ chars (e.g. AAPL  250321C00200000).
    Equity tickers are typically ≤ 5 chars and all alpha.
    """
    return len(sym) > 6 and not sym.isalpha()


def _normalise_quotes(
    raw_quotes: list[dict],
) -> tuple[dict[str, dict], dict[str, dict]]:
    """Split a flat Tradier quote list into (options_dict, underlyings_dict)."""
    options: dict[str, dict] = {}
    underlyings: dict[str, dict] = {}

    for q in raw_quotes:
        sym = (q.get("symbol") or "").upper().strip()
        if not sym:
            continue

        if _is_option_symbol(sym):
            greeks = q.get("greeks") or {}
            # Tradier returns mid_iv or smv_vol for implied vol
            iv_raw = greeks.get("mid_iv") or greeks.get("smv_vol") or 0
            delta_raw = greeks.get("delta")
            volume = int(q.get("volume") or 0)
            oi = int(q.get("open_interest") or 0)
            chg = float(q.get("change_percentage") or 0)

            options[sym] = {
                "volume": volume,
                "open_interest": oi,
                "delta": (
                    round(float(delta_raw), 4) if delta_raw is not None else None
                ),
                "implied_volatility": (round(float(iv_raw), 4) if iv_raw else None),
                "change_pct": round(chg, 2),
            }
        else:
            volume = int(q.get("volume") or 0)
            last_raw = q.get("last") or q.get("close") or 0
            underlyings[sym] = {
                "stock_volume": volume,
                "last": round(float(last_raw), 4) if last_raw else None,
            }

    return options, underlyings


@quotes_refresh_router.post("/refresh")
async def endpoint_quotes_refresh(req: QuotesRefreshRequest):
    """
    Fetch volatile quote fields for active-grid options + underlyings.
    One Tradier call. Errors are swallowed — empty dicts returned.
    """
    all_syms = list(
        dict.fromkeys(  # deduplicate while preserving order
            [s.upper() for s in req.option_symbols if s]
            + [s.upper() for s in req.underlying_symbols if s]
        )
    )[:_MAX_SYMBOLS]

    empty = {
        "options": {},
        "underlyings": {},
        "refreshed_at": datetime.now().isoformat(),
    }

    if not all_syms:
        return empty

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                _tradier_quotes_url(),
                headers=_tradier_headers(),
                params={"symbols": ",".join(all_syms), "greeks": "true"},
            )
        resp.raise_for_status()
        payload = resp.json()

        # Tradier wraps result: {"quotes": {"quote": [...] or {...}}}
        quotes_block = payload.get("quotes") or {}
        raw_quotes = quotes_block.get("quote") or []
        if isinstance(raw_quotes, dict):  # single symbol → object, not array
            raw_quotes = [raw_quotes]

        options, underlyings = _normalise_quotes(raw_quotes)
        logger.debug(
            "🔄 Quotes refresh: %d options, %d underlyings",
            len(options),
            len(underlyings),
        )

    except httpx.HTTPStatusError as exc:
        logger.warning("Tradier quotes HTTP %s: %s", exc.response.status_code, exc)
        return {**empty, "error": f"Tradier {exc.response.status_code}"}
    except Exception as exc:
        logger.warning("Quotes refresh error: %s", exc)
        return {**empty, "error": str(exc)}

    return {
        "options": options,
        "underlyings": underlyings,
        "refreshed_at": datetime.now().isoformat(),
    }
