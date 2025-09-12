#!/usr/bin/env python3
"""
Performance testing script for squeeze-finder optimizations
Tests the efficiency of caching, async calls, and pre-filtering
"""

import asyncio
import time
import statistics
from typing import List, Dict
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from data.async_tradier import AsyncTradierClient
from data.screener_logic import OptionsScreener
from utils.helpers import get_market_data_batch, filter_symbols_by_market_criteria
from utils.config import Config


class PerformanceTester:
    def __init__(self):
        self.test_symbols = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'AMD',
            'NFLX', 'CRM', 'UBER', 'ZOOM', 'SQ', 'PYPL', 'SHOP', 'ROKU',
            'GME', 'AMC', 'BB', 'NOK', 'PLTR', 'SPCE', 'CLOV', 'WISH',
            'MVIS', 'CTRM', 'SNDL', 'NAKD', 'ZOM', 'CCIV'
        ]
        self.results = {}

    async def test_async_optionable_filtering(self, symbols: List[str], runs: int = 3) -> Dict:
        """Test async optionable symbol filtering performance"""
        print(f"\n🔍 Testing async optionable filtering with {len(symbols)} symbols...")
        
        times = []
        client = AsyncTradierClient(max_concurrent=15, rate_limit=0.05)
        
        try:
            for run in range(runs):
                start_time = time.time()
                
                # Test the optimized filtering
                optionable = await client.filter_optionable_symbols(symbols)
                
                end_time = time.time()
                duration = end_time - start_time
                times.append(duration)
                
                print(f"  Run {run + 1}: {duration:.2f}s, found {len(optionable)} optionable symbols")
                
                # Add some delay between runs
                if run < runs - 1:
                    await asyncio.sleep(1)
                    
        finally:
            await client.close()
        
        return {
            'avg_time': statistics.mean(times),
            'min_time': min(times),
            'max_time': max(times),
            'times': times
        }

    def test_market_data_prefiltering(self, symbols: List[str]) -> Dict:
        """Test market data pre-filtering performance"""
        print(f"\n📊 Testing market data pre-filtering with {len(symbols)} symbols...")
        
        # Time market data retrieval
        start_time = time.time()
        market_data = get_market_data_batch(symbols)
        market_time = time.time() - start_time
        
        print(f"  Market data retrieval: {market_time:.2f}s for {len(market_data)} symbols")
        
        # Time filtering
        start_time = time.time()
        filtered = filter_symbols_by_market_criteria(
            symbols,
            min_market_cap=100_000_000,
            min_avg_volume=500_000
        )
        filter_time = time.time() - start_time
        
        print(f"  Pre-filtering: {filter_time:.2f}s, {len(filtered)} symbols passed filters")
        print(f"  Reduction: {len(symbols) - len(filtered)} symbols ({((len(symbols) - len(filtered)) / len(symbols) * 100):.1f}%)")
        
        return {
            'market_data_time': market_time,
            'filter_time': filter_time,
            'total_time': market_time + filter_time,
            'symbols_filtered_out': len(symbols) - len(filtered),
            'reduction_percentage': (len(symbols) - len(filtered)) / len(symbols) * 100,
            'filtered_symbols': filtered
        }

    async def test_cache_efficiency(self, symbols: List[str]) -> Dict:
        """Test caching efficiency"""
        print(f"\n💾 Testing cache efficiency...")
        
        client = AsyncTradierClient(max_concurrent=10, rate_limit=0.1)
        
        try:
            # First run - cold cache
            print("  Cold cache run...")
            start_time = time.time()
            first_results = await client.filter_optionable_symbols(symbols[:10])
            first_time = time.time() - start_time
            
            # Second run - warm cache
            print("  Warm cache run...")
            start_time = time.time()
            second_results = await client.filter_optionable_symbols(symbols[:10])
            second_time = time.time() - start_time
            
            cache_speedup = first_time / second_time if second_time > 0 else float('inf')
            
            print(f"  Cold cache: {first_time:.2f}s")
            print(f"  Warm cache: {second_time:.2f}s")
            print(f"  Cache speedup: {cache_speedup:.2f}x")
            
            return {
                'cold_cache_time': first_time,
                'warm_cache_time': second_time,
                'speedup_factor': cache_speedup,
                'cache_hit_efficiency': (first_time - second_time) / first_time * 100
            }
            
        finally:
            await client.close()

    async def test_screening_performance(self, symbols: List[str]) -> Dict:
        """Test options screening performance"""
        print(f"\n⚡ Testing screening performance with {len(symbols)} symbols...")
        
        screener = OptionsScreener(use_async=True)
        
        # Test with limited symbols to avoid API rate limits
        test_symbols = symbols[:5]  # Use smaller set for testing
        
        try:
            start_time = time.time()
            
            # Test async screening with progress tracking
            results = await screener.screen_async(
                symbols=test_symbols,
                option_type="call",
                max_dte=7,
                min_volume=500,
                min_oi=100,
                min_whale_score=60
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"  Screening completed in {duration:.2f}s")
            print(f"  Found {len(results)} qualifying options")
            print(f"  Average time per symbol: {duration / len(test_symbols):.2f}s")
            
            return {
                'total_time': duration,
                'symbols_processed': len(test_symbols),
                'options_found': len(results),
                'avg_time_per_symbol': duration / len(test_symbols),
                'results': results[:3]  # Sample results
            }
            
        finally:
            await screener.close_async()

    async def run_all_tests(self):
        """Run all performance tests"""
        print("🚀 Starting Performance Testing Suite")
        print(f"📋 Test symbols: {len(self.test_symbols)} symbols")
        print("=" * 60)
        
        # Test 1: Market data pre-filtering
        self.results['prefiltering'] = self.test_market_data_prefiltering(self.test_symbols)
        
        # Use pre-filtered symbols for subsequent tests
        filtered_symbols = self.results['prefiltering']['filtered_symbols']
        
        # Test 2: Async optionable filtering
        self.results['async_filtering'] = await self.test_async_optionable_filtering(
            filtered_symbols[:15], runs=2  # Limit for API quotas
        )
        
        # Test 3: Cache efficiency
        self.results['caching'] = await self.test_cache_efficiency(filtered_symbols)
        
        # Test 4: Screening performance (limited set)
        self.results['screening'] = await self.test_screening_performance(filtered_symbols)
        
        # Summary
        self.print_summary()

    def print_summary(self):
        """Print performance test summary"""
        print("\n" + "=" * 60)
        print("📊 PERFORMANCE TEST SUMMARY")
        print("=" * 60)
        
        if 'prefiltering' in self.results:
            pf = self.results['prefiltering']
            print(f"🎯 Pre-filtering:")
            print(f"   • Reduced symbols by {pf['reduction_percentage']:.1f}%")
            print(f"   • Time: {pf['total_time']:.2f}s")
        
        if 'async_filtering' in self.results:
            af = self.results['async_filtering']
            print(f"⚡ Async filtering:")
            print(f"   • Average time: {af['avg_time']:.2f}s")
            print(f"   • Best time: {af['min_time']:.2f}s")
        
        if 'caching' in self.results:
            cache = self.results['caching']
            print(f"💾 Caching:")
            print(f"   • Speedup: {cache['speedup_factor']:.2f}x")
            print(f"   • Efficiency: {cache['cache_hit_efficiency']:.1f}%")
        
        if 'screening' in self.results:
            screen = self.results['screening']
            print(f"🔍 Screening:")
            print(f"   • Time per symbol: {screen['avg_time_per_symbol']:.2f}s")
            print(f"   • Options found: {screen['options_found']}")
        
        print("\n✅ Performance testing completed!")


async def main():
    """Main test runner"""
    tester = PerformanceTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    # Check if API key is available
    if not Config.TRADIER_API_KEY:
        print("❌ Error: TRADIER_API_KEY not found in secrets or environment")
        print("Please configure your API key before running performance tests")
        sys.exit(1)
    
    asyncio.run(main())