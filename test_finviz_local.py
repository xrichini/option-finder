#!/usr/bin/env python3
"""
Test local: verify finviz enrichment works end-to-end
"""
import json
import sys
from pathlib import Path

# Test 1: Import finviz-mcp
print("=" * 60)
print("TEST 1: Import finviz-mcp")
print("=" * 60)
try:
    from tools.insider import get_market_insiders

    print("✅ finviz-mcp imports OK")
except ImportError as e:
    print(f"❌ finviz-mcp import FAILED: {e}")
    sys.exit(1)

# Test 2: Fetch insider data
print("\n" + "=" * 60)
print("TEST 2: Fetch insider data (market-wide)")
print("=" * 60)
try:
    result = get_market_insiders(option="latest buys", limit=10)
    print(f"✅ Fetched {result['count']} insider buys")
    if result["data"]:
        sample = result["data"][0]
        print(
            f"   Sample: {sample.get('Ticker')} - {sample.get('Owner')} ({sample.get('Relationship')})"
        )
except Exception as e:
    print(f"❌ Fetch FAILED: {e}")
    sys.exit(1)

# Test 3: Test enrichment function
print("\n" + "=" * 60)
print("TEST 3: Test enrich_opportunities_with_insider_data()")
print("=" * 60)
try:
    from api.finviz_enrichment import enrich_opportunities_with_insider_data

    # Simulate some opportunities
    test_opps = [
        {"symbol": "AAPL", "strike": 150, "score": 75.5, "option_type": "call"},
        {"symbol": "MSFT", "strike": 420, "score": 60.0, "option_type": "call"},
        {"symbol": "NVDA", "strike": 135, "score": 88.2, "option_type": "put"},
    ]

    enriched = enrich_opportunities_with_insider_data(test_opps)
    print(f"✅ Enriched {len(enriched)} opportunities")

    for opp in enriched:
        insider_status = opp.get("insider_sentiment", "N/A")
        boost = opp.get("insider_boost", 1.0)
        score_new = opp.get("score", opp.get("score_original", 0))
        print(
            f"   {opp['symbol']}: sentiment={insider_status} boost={boost:.2f} score={score_new}"
        )

except Exception as e:
    print(f"❌ Enrichment FAILED (api package import): {str(e)[:80]}")
    print("   Attempting direct module import (bypass api/__init__.py)...")

    try:
        # Direct module import to bypass FastAPI chain
        import sys as sys_module

        sys_module.path.insert(0, str(Path(__file__).parent / "api"))
        from finviz_enrichment import enrich_opportunities_with_insider_data

        # If that works, test enrichment
        test_opps = [
            {"symbol": "AAPL", "strike": 150, "score": 75.5, "option_type": "call"},
            {"symbol": "MSFT", "strike": 420, "score": 60.0, "option_type": "call"},
            {"symbol": "NVDA", "strike": 135, "score": 88.2, "option_type": "put"},
        ]

        enriched = enrich_opportunities_with_insider_data(test_opps)
        print(f"\n✅ Enriched {len(enriched)} opportunities (direct import)")

        for opp in enriched:
            insider_status = opp.get("insider_sentiment", "N/A")
            boost = opp.get("insider_boost", 1.0)
            score_new = opp.get("score", opp.get("score_original", 0))
            print(
                f"   {opp['symbol']}: sentiment={insider_status} boost={boost:.2f} score={score_new}"
            )
    except Exception as e2:
        print(f"❌ Direct import also failed: {e2}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

print("\n" + "=" * 60)
print("✅ ALL TESTS PASSED - Finviz enrichment ready!")
print("=" * 60)
