"""
api/finviz_enrichment.py
Enrich opportunities with insider trading data from finviz-mcp.

Functions to add insider sentiment, recent insider activity, and advisor
recommendation signals to option opportunities.
"""

import logging
from typing import Any

logger = logging.getLogger("finviz_enrichment")


def get_insider_signals(limit: int = 100) -> dict[str, Any]:
    """
    Fetch recent insider buying activity (market-wide).

    Returns dict keyed by TICKER with metadata:
    {
        'AAPL': {
            'buys_count': 5,
            'recent_buy': True,
            'signal_strength': 'bullish'
        },
        ...
    }
    """
    try:
        from tools.insider import get_market_insiders

        result = get_market_insiders(option="latest buys", limit=limit)

        # Aggregate by ticker
        insider_map = {}
        for record in result.get("data", []):
            ticker = record.get("Ticker", "").upper()
            if not ticker:
                continue

            if ticker not in insider_map:
                insider_map[ticker] = {
                    "buys_count": 0,
                    "recent_buy": False,
                    "signal_strength": "neutral",
                }

            insider_map[ticker]["buys_count"] += 1

        # Assign signal strength based on recent buy count
        for ticker, data in insider_map.items():
            data["recent_buy"] = True
            if data["buys_count"] >= 3:
                data["signal_strength"] = "very_bullish"
            elif data["buys_count"] >= 2:
                data["signal_strength"] = "bullish"
            else:
                data["signal_strength"] = "mild_bullish"

        logger.info(
            f"✅ Insider signals retrieved: {len(insider_map)} tickers with recent buys"
        )
        return insider_map

    except ImportError as e:
        logger.warning(f"⚠️  finviz-mcp not available: {e}")
        return {}
    except Exception as e:
        logger.error(f"❌ Error fetching insider signals: {e}", exc_info=True)
        return {}


def enrich_opportunities_with_insider_data(opportunities: list[dict]) -> list[dict]:
    """
    Enrich each opportunity with insider trading signals.

    Adds fields:
    - insider_sentiment: 'bullish' | 'neutral' | 'bearish'
    - insider_signal_strength: count of recent buys or 'none'
    - insider_boost: multiplier for scoring (1.0-2.0 for bullish)

    Args:
        opportunities: List of option opportunities (dicts)

    Returns:
        Same list but with insider fields added.
    """
    try:
        insider_map = get_insider_signals(limit=150)

        enriched = []
        for opp in opportunities:
            ticker = opp.get("symbol", "").upper()

            # Default insider data (neutral)
            opp["insider_sentiment"] = "neutral"
            opp["insider_signal_strength"] = "none"
            opp["insider_boost"] = 1.0

            # Enrich if ticker has recent insider buys
            if ticker in insider_map:
                insider_data = insider_map[ticker]
                opp["insider_sentiment"] = insider_data["signal_strength"]
                opp["insider_signal_strength"] = insider_data["buys_count"]

                # Boost multiplier based on signal strength
                if insider_data["signal_strength"] == "very_bullish":
                    opp["insider_boost"] = 1.2
                elif insider_data["signal_strength"] == "bullish":
                    opp["insider_boost"] = 1.15
                elif insider_data["signal_strength"] == "mild_bullish":
                    opp["insider_boost"] = 1.05

            # Re-calculate score with insider boost
            if "score" in opp and isinstance(opp["score"], (int, float)):
                original_score = opp["score"]
                opp["score_original"] = original_score
                opp["score"] = round(original_score * opp["insider_boost"], 2)

            enriched.append(opp)

        logger.info(
            f"✅ Enriched {len(enriched)} opportunities with insider data. "
            f"Bullish signals: {sum(1 for o in enriched if o.get('insider_sentiment') != 'neutral')}"
        )
        return enriched

    except Exception as e:
        logger.error(f"❌ Error enriching opportunities: {e}", exc_info=True)
        # Return unmodified opportunities on error
        return opportunities
