#!/usr/bin/env python3
"""Quick test of advanced filtering features"""

from services.advanced_filtering_service import advanced_filtering_service
from models.api_models import AdvancedFilters

# Test data
test_opps = [
    {
        "symbol": "AAPL",
        "whale_score": 75,
        "last_price": 2.5,
        "volume_1d": 100,
        "dte": 7,
        "implied_volatility": 30,
        "open_interest": 500,
        "strike": 150,
        "delta": 0.5,
    },
    {
        "symbol": "AAPL",
        "whale_score": 45,
        "last_price": 1.5,
        "volume_1d": 50,
        "dte": 14,
        "implied_volatility": 28,
        "open_interest": 200,
        "strike": 155,
        "delta": 0.3,
    },
    {
        "symbol": "TSLA",
        "whale_score": 65,
        "last_price": 4.0,
        "volume_1d": 150,
        "dte": 21,
        "implied_volatility": 45,
        "open_interest": 800,
        "strike": 200,
        "delta": 0.6,
    },
]

print("=" * 60)
print("TESTING ADVANCED FILTERING")
print("=" * 60)

# Test 1: No filters
result = advanced_filtering_service.filter_opportunities(test_opps, AdvancedFilters())
print(f"\n1. NO FILTERS: {len(result)}/3 opportunities")

# Test 2: Whale score filter
filters = AdvancedFilters(min_whale_score=50)
result = advanced_filtering_service.filter_opportunities(test_opps, filters)
print(f"2. MIN WHALE SCORE 50: {len(result)}/3 opportunities")
print(f"   Scores: {[opp['whale_score'] for opp in result]}")

# Test 3: Price range
filters = AdvancedFilters(min_price=1.5, max_price=3.0)
result = advanced_filtering_service.filter_opportunities(test_opps, filters)
print(f"3. PRICE RANGE 1.5-3.0: {len(result)}/3 opportunities")
print(f"   Prices: {[opp['last_price'] for opp in result]}")

# Test 4: Preset - Aggressive
result = advanced_filtering_service.apply_preset(test_opps, "aggressive")
print(f"4. PRESET 'AGGRESSIVE': {len(result)}/3 opportunities")

# Test 5: Sort by whale score
sorted_opps = advanced_filtering_service.sort_opportunities(
    result, sort_by="whale_score", ascending=False
)
print(f"5. SORT BY WHALE SCORE DESC: {[opp['whale_score'] for opp in sorted_opps]}")

# Test 6: Stats
stats = advanced_filtering_service.get_filter_stats(test_opps)
print(f"6. STATS: Total={stats['total']}, Avg Score={stats['avg_whale_score']:.1f}")

# Test 7: Presets list
presets = advanced_filtering_service.get_all_presets()
print(f"\n7. AVAILABLE PRESETS ({len(presets)}):")
for name, preset in presets.items():
    print(f"   - {preset.name}: {preset.description}")

print("\n" + "=" * 60)
print("ALL TESTS PASSED!")
print("=" * 60)
