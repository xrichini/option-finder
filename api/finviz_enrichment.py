"""
api/finviz_enrichment.py
Enrich opportunities with insider trading data from finviz-mcp + fallback sources.

Functions to add insider sentiment, recent insider activity, and advisor
recommendation signals to option opportunities.

Sources:
1. Finviz (finviz-mcp) - market-wide insider buys (last 30 days)
2. Yahoo Finance (yfinance) - ticker-specific insider transactions
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

logger = logging.getLogger("finviz_enrichment")

# Ensure finviz-mcp tools are importable
_finviz_mcp_path = Path(__file__).parent.parent / "src" / "finviz-mcp"
if _finviz_mcp_path.exists() and str(_finviz_mcp_path) not in sys.path:
    sys.path.insert(0, str(_finviz_mcp_path))


def _get_insider_sentiment_from_yfinance(ticker: str) -> dict[str, Any] | None:
    """
    (Deprecated - yfinance rate-limits too quickly)
    Fetch insider sentiment for a specific ticker from Yahoo Finance.

    Returns None - use Finviz instead.
    """
    return None


def _get_insider_sentiment_from_openinsider(ticker: str) -> dict[str, Any] | None:
    """
    Fetch insider sentiment for a specific ticker from OpenInsider.

    Returns: {'signal_strength': 'bullish'|'bearish'|'neutral', 'buys_count': int}
    or None if unavailable.
    """
    try:
        import requests
        from bs4 import BeautifulSoup

        url = f"https://openinsider.com/screener?s={ticker.upper()}&o=&pl=&ph=&ll=&lh=&fd=730&fdr=&td=&tdr=&L=&llt=&lmt=&lddr=&sind=&usi=1&ccrsl=&ctl=&ccurl=&isocode=&t=&po=&accHolder=1&whitelist=true&recInvest=true&copies=true&filter=&count=100"

        resp = requests.get(url, timeout=5)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Look for insider activity summary on page
        # OpenInsider shows insider buys vs sells in the results table
        rows = soup.find_all("tr")
        if not rows or len(rows) < 2:
            return None

        # Count buys vs sells in last 30 days
        buys = 0
        sells = 0
        cutoff_date = datetime.now() - timedelta(days=30)

        for row in rows[1:]:  # Skip header
            cols = row.find_all("td")
            if len(cols) < 12:
                continue

            try:
                # Column 2 is transaction type (BUY/SELL)
                transaction = cols[2].text.strip().upper()
                # Column 1 is date
                date_str = cols[1].text.strip()

                # Skip if date is too old
                try:
                    row_date = datetime.strptime(date_str, "%Y-%m-%d")
                    if row_date < cutoff_date:
                        continue
                except:
                    pass

                if "BUY" in transaction:
                    buys += 1
                elif "SALE" in transaction:
                    sells += 1
            except:
                continue

        if buys == 0 and sells == 0:
            return None

        # Determine signal strength
        net_sentiment = buys - sells
        if net_sentiment >= 3:
            signal = "very_bullish"
        elif net_sentiment >= 1:
            signal = "bullish"
        elif net_sentiment <= -3:
            signal = "very_bearish"
        elif net_sentiment <= -1:
            signal = "bearish"
        else:
            signal = "neutral"

        return {
            "signal_strength": signal,
            "buys_count": buys,
            "sells_count": sells,
            "net_sentiment": net_sentiment,
        }
    except Exception as e:
        logger.debug(f"OpenInsider scrape failed for {ticker}: {e}")
        return None


def get_insider_signals(limit: int = 100) -> dict[str, Any]:
    """
    Fetch recent insider buying activity (market-wide).

    Strategy: Try Finviz first (broad coverage) for recent buys from finvizfinance.

    Returns dict keyed by TICKER with metadata:
    {
        'AAPL': {
            'buys_count': 5,
            'signal_strength': 'bullish',
            'source': 'finviz'
        },
        ...
    }
    """
    insider_map = {}

    # Try Finviz first (market-wide recent buys)
    try:
        from tools.insider import get_market_insiders

        result = get_market_insiders(option="latest buys", limit=limit)

        # Aggregate by ticker
        for record in result.get("data", []):
            ticker = record.get("Ticker", "").upper()
            if not ticker:
                continue

            if ticker not in insider_map:
                insider_map[ticker] = {
                    "buys_count": 0,
                    "signal_strength": "neutral",
                    "source": "finviz",
                }

            insider_map[ticker]["buys_count"] += 1

        # Assign signal strength based on recent buy count
        for ticker, data in insider_map.items():
            if data["buys_count"] >= 3:
                data["signal_strength"] = "very_bullish"
            elif data["buys_count"] >= 2:
                data["signal_strength"] = "bullish"
            else:
                data["signal_strength"] = "mild_bullish"

        logger.info(
            f"✅ Finviz insider signals: {len(insider_map)} tickers with recent buys"
        )

    except Exception as e:
        logger.warning(f"⚠️  Finviz insider fetch failed: {e}")

    return insider_map


def enrich_opportunities_with_insider_data(opportunities: list[dict]) -> list[dict]:
    """
    Enrich each opportunity with insider trading signals.

    Adds fields:
    - insider_sentiment: 'bullish' | 'neutral' | 'bearish'
    - insider_signal_strength: count of recent buys or 'none'
    - insider_boost: multiplier for scoring (1.0-2.0 for bullish)

    Uses Finviz as primary source (market-wide insider buys, ~97 tickers with recent activity).
    Note: Limited to small-caps with recent insider activity; mega-caps get neutral sentiment.

    Args:
        opportunities: List of option opportunities (dicts)

    Returns:
        Same list but with insider fields added.
    """
    try:
        insider_map = get_insider_signals(limit=500)

        bullish_count = 0

        enriched = []
        for opp in opportunities:
            ticker = (opp.get("underlying_symbol") or opp.get("symbol", "")).upper()

            # Default insider data (neutral)
            opp["insider_sentiment"] = "neutral"
            opp["insider_signal_strength"] = "none"
            opp["insider_boost"] = 1.0
            opp["insider_source"] = "none"

            # Enrich from Finviz if available
            if ticker in insider_map:
                insider_data = insider_map[ticker]
                opp["insider_sentiment"] = insider_data["signal_strength"]
                opp["insider_signal_strength"] = insider_data["buys_count"]
                opp["insider_source"] = "finviz"

            # Apply boost based on sentiment
            sentiment = opp["insider_sentiment"]
            if sentiment == "very_bullish":
                opp["insider_boost"] = 1.2
            elif sentiment == "bullish":
                opp["insider_boost"] = 1.15
            elif sentiment == "mild_bullish":
                opp["insider_boost"] = 1.05
            elif sentiment == "bearish":
                opp["insider_boost"] = 0.95
            elif sentiment == "very_bearish":
                opp["insider_boost"] = 0.9

            # Count bullish signals
            if sentiment != "neutral":
                bullish_count += 1

            # Re-calculate score with insider boost
            if "score" in opp and isinstance(opp["score"], (int, float)):
                original_score = opp["score"]
                opp["score_original"] = original_score
                opp["score"] = round(original_score * opp["insider_boost"], 2)

            enriched.append(opp)

        finviz_covered = sum(1 for o in enriched if o.get("insider_source") == "finviz")

        logger.info(
            f"✅ Enriched {len(enriched)} opportunities. "
            f"Insider signals (Finviz): {finviz_covered} tickers. "
            f"Bullish: {bullish_count}"
        )
        return enriched

    except Exception as e:
        logger.error(f"❌ Error enriching opportunities: {e}", exc_info=True)
        # Return unmodified opportunities on error
        return opportunities
