"""
Earnings Calendar endpoint — backed by FMP, non-blocking.
GET /api/earnings/upcoming?days=7
Returns { "earnings": { "AAPL": { "date": "2026-02-24", "timing": "AMC" }, ... },
          "source": "fmp"|"empty",
          "cached": bool }
"""

import logging
from fastapi import APIRouter, Query
from api.earnings_utils import get_earnings_map

logger = logging.getLogger(__name__)

earnings_router = APIRouter(prefix="/api/earnings", tags=["earnings"])


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
    data = await get_earnings_map(days)
    return {
        "earnings": data,
        "source": "fmp" if data else "empty",
        "cached": False,
        "count": len(data),
    }
