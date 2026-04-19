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

            # ─── Phase 1: Moneyness Bucket Enhancement ───
            # ATM options = highest quality (highest gamma, most liquid)
            # FAR OTM = lottery tickets (skip)
            moneyness = opp.get("moneyness", "")
            moneyness_pct = opp.get("moneyness_pct", 0.0)
            moneyness_boost = 1.0

            if moneyness == "ATM":
                # ATM = optimal for gamma trades, highest quality whale activity
                moneyness_boost = 1.05  # +5% score boost
                opp["moneyness_quality"] = "premium"
            elif moneyness == "OTM" and abs(moneyness_pct) < 1.0:
                # Slightly OTM (< 1% OTM) = directional play, good quality
                moneyness_boost = 1.02  # +2% score boost
                opp["moneyness_quality"] = "good"
            elif moneyness == "ITM":
                # ITM calls/puts = more defensive, but still liquid
                moneyness_boost = 1.01  # +1% score boost
                opp["moneyness_quality"] = "good"
            elif moneyness == "OTM" and abs(moneyness_pct) >= 3.0:
                # Far OTM (3%+ OTM) = lottery tickets, low quality
                moneyness_boost = 0.85  # -15% score penalty
                opp["moneyness_quality"] = "low"
            else:
                opp["moneyness_quality"] = "neutral"

            # Apply moneyness boost to current score
            if "score" in opp and isinstance(opp["score"], (int, float)):
                opp["score"] = round(opp["score"] * moneyness_boost, 2)

            # ─── Phase 1: Fill Aggression / Conviction Buying ───
            # If whale paid aggressively (at/near ask), it shows high conviction
            fill_aggression = opp.get("fill_aggression", "normal")
            fill_aggression_boost = 1.0

            if fill_aggression == "aggressive":
                # Paying 80%+ through spread = high conviction, institutional execution
                fill_aggression_boost = 1.03  # +3% score boost
                opp["aggression_signal"] = "high_conviction"
            elif fill_aggression == "patient":
                # Accumulating quietly = could be bottom-fishing or distribution
                fill_aggression_boost = 1.0  # Neutral
                opp["aggression_signal"] = "accumulating"
            else:
                opp["aggression_signal"] = "normal"

            # Apply fill aggression boost to current score
            if "score" in opp and isinstance(opp["score"], (int, float)):
                opp["score"] = round(opp["score"] * fill_aggression_boost, 2)

            # ─── Phase 1: Size Percentile / Volume Conviction ───
            # Contracts with 30-day volume significantly above average = high interest
            size_pct = opp.get("size_percentile", 0.0)
            size_percentile_boost = 1.0
            size_percentile_badge = "normal"

            if size_pct >= 95.0:
                # Top 1% by volume (2x+ 30-day average) = exceptional
                size_percentile_boost = 1.05  # +5% boost
                size_percentile_badge = "🟢🟢 Top 1%"
            elif size_pct >= 80.0:
                # Top 5% by volume (1.3x+ 30-day average) = notable
                size_percentile_boost = 1.03  # +3% boost
                size_percentile_badge = "🟢 Top 5%"
            elif size_pct >= 75.0:
                # Top 25% by volume (at/above 30-day average) = decent
                size_percentile_boost = 1.01  # +1% boost
                size_percentile_badge = "🟡 Top 25%"
            else:
                size_percentile_badge = "below_avg"

            opp["size_percentile_badge"] = size_percentile_badge

            # Apply size percentile boost to current score
            if "score" in opp and isinstance(opp["score"], (int, float)):
                opp["score"] = round(opp["score"] * size_percentile_boost, 2)

            # ─── Phase 2: IV Crush Risk / Volatility Compression ───
            # High IV crush risk = IV likely to compress (mean reversion to lower levels)
            # This typically happens post-earnings or after volatility events
            iv_crush_risk = opp.get("iv_crush_risk", 0.0)
            iv_crush_boost = 1.0
            iv_crush_badge = "normal"

            if iv_crush_risk >= 1.5:
                # Elevated IV crush risk: sell side (short calls/long puts) favored
                iv_crush_boost = 0.97  # -3% penalty for long calls, neutral for puts
                iv_crush_badge = "⚠️  High Risk (1.5x+)"
            elif iv_crush_risk >= 1.2:
                # Moderately elevated IV
                iv_crush_boost = 0.99  # -1% slight penalty
                iv_crush_badge = "elevated"
            else:
                iv_crush_badge = "low_crush_risk"

            opp["iv_crush_badge"] = iv_crush_badge

            # Apply IV crush penalty to current score
            if "score" in opp and isinstance(opp["score"], (int, float)):
                opp["score"] = round(opp["score"] * iv_crush_boost, 2)

            # ─── Phase 2: Fill Velocity / Institutional Interest ───
            # High fill velocity = aggressive institutional buying (conviction signal)
            fill_velocity = opp.get("fill_velocity", 0.0)
            fill_vel_boost = 1.0
            fill_vel_badge = "normal"

            if fill_velocity >= 5000:
                # Exceptional velocity: >5000 contracts/minute = massive institutional flow
                fill_vel_boost = 1.04  # +4% boost
                fill_vel_badge = "🔥 Exceptional (5k+/min)"
            elif fill_velocity >= 1000:
                # Normal institutional activity
                fill_vel_boost = 1.0
                fill_vel_badge = "steady"
            else:
                # Below average activity
                fill_vel_badge = "low_activity"

            opp["fill_velocity_badge"] = fill_vel_badge

            # Apply fill velocity boost to current score
            if "score" in opp and isinstance(opp["score"], (int, float)):
                opp["score"] = round(opp["score"] * fill_vel_boost, 2)

            # ─── Phase 3: Order Flow Strength / Institutional Conviction ───
            # Analyze accumulation vs distribution patterns
            flow_strength = opp.get("order_flow_strength", 50.0)
            flow_direction = opp.get("order_flow_direction", "neutral")
            flow_boost = 1.0
            flow_badge = "neutral"

            if flow_direction == "strong_bullish":
                # Aggressive institutional accumulation with expanding OI
                flow_boost = 1.06  # +6% boost (highest signal)
                flow_badge = "💪 Strong Bull"
            elif flow_direction == "bullish":
                # Positive flow: accumulation or steady buying
                flow_boost = 1.03  # +3% boost
                flow_badge = "📈 Bullish"
            elif flow_direction == "strong_bearish":
                # Aggressive distribution or liquidation
                flow_boost = 0.94  # -6% penalty
                flow_badge = "⚠️ Strong Bear"
            elif flow_direction == "bearish":
                # Negative flow: distribution detected
                flow_boost = 0.97  # -3% penalty
                flow_badge = "📉 Bearish"
            else:
                flow_badge = "neutral"

            opp["order_flow_badge"] = flow_badge

            # Apply order flow boost to current score
            if "score" in opp and isinstance(opp["score"], (int, float)):
                opp["score"] = round(opp["score"] * flow_boost, 2)

            # ─── Phase 3: Volatility Smile & Crush Assessment ───
            # Detect if IV is elevated and smile pattern suggests reversal
            smile_width = opp.get("volatility_smile", 0.0)
            crush_prob = opp.get("crush_probability", 0.0)
            crush_catalyst = opp.get("crush_catalyst", "none")
            crush_boost = 1.0
            crush_badge = "normal"

            if crush_catalyst == "earnings":
                # Earnings catalyst = guaranteed IV crush post-earnings
                if crush_prob >= 75:
                    crush_boost = 0.90  # -10% for long calls, neutral for puts
                    crush_badge = "⚡ EARNINGS"
                else:
                    crush_boost = 0.95  # -5% hedge
                    crush_badge = "⚡ Earnings"
            elif crush_prob >= 75:
                # Very high crush probability (high smile + high IV)
                crush_boost = 0.93  # -7% penalty for long options
                crush_badge = "🔴 Extreme Crush Risk"
            elif crush_prob >= 50:
                # Moderate to high crush risk
                crush_boost = 0.96  # -4% penalty
                crush_badge = "🟠 High Crush Risk"
            elif crush_prob >= 25:
                # Noticeable crush risk
                crush_boost = 0.98  # -2% penalty
                crush_badge = "🟡 Moderate Crush"
            else:
                crush_badge = "🟢 Low Risk"

            opp["iv_crush_badge"] = crush_badge

            # Apply crush probability penalty to current score
            if "score" in opp and isinstance(opp["score"], (int, float)):
                opp["score"] = round(opp["score"] * crush_boost, 2)

            # Cap score at 100
            if "score" in opp and isinstance(opp["score"], (int, float)):
                opp["score"] = min(100.0, max(0.0, opp["score"]))

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
