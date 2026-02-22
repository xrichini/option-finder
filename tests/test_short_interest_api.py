#!/usr/bin/env python3
"""
Test des endpoints API Short Interest
"""

import requests

BASE_URL = "http://127.0.0.1:8001"

def test_health():
    """Test endpoint health"""
    try:
        response = requests.get(f"{BASE_URL}/api/short-interest/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check: {data['status']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_symbols_endpoint():
    """Test endpoint symbols"""
    try:
        print("📋 Test endpoint /api/short-interest/symbols...")
        response = requests.get(f"{BASE_URL}/api/short-interest/symbols?exchange=nasdaq&min_market_cap=100000000&enable_prefiltering=true")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Symbols retrieved: {data['count']} symboles")
            print(f"   Execution time: {data['execution_time_seconds']:.2f}s")
            if data['symbols']:
                print(f"   First 5 symbols: {', '.join(data['symbols'][:5])}")
            return True
        else:
            print(f"❌ Symbols endpoint failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Symbols endpoint error: {e}")
        return False

def test_stocks_endpoint():
    """Test endpoint stocks with detailed data"""
    try:
        print("📊 Test endpoint /api/short-interest/stocks...")
        response = requests.get(f"{BASE_URL}/api/short-interest/stocks?exchange=nasdaq&min_market_cap=100000000&min_short_interest=20.0&enable_prefiltering=true")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Stocks retrieved: {data['filtered_count']}/{data['total_count']} stocks")
            print(f"   Execution time: {data['execution_time_seconds']:.2f}s")
            
            if data['stocks']:
                print("   Top 3 stocks by short interest:")
                for i, stock in enumerate(data['stocks'][:3], 1):
                    print(f"   {i}. {stock['symbol']}: {stock['short_interest_pct']:.1f}% SI")
                    if stock['market_cap']:
                        print(f"      Market cap: ${stock['market_cap']:,}")
            return True
        else:
            print(f"❌ Stocks endpoint failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Stocks endpoint error: {e}")
        return False

def main():
    """Test principal"""
    print("🚀 Test des endpoints Short Interest API")
    print("=" * 50)
    
    # Test health first
    if not test_health():
        print("❌ Health check failed, arrêt des tests")
        return
        
    print()
    
    # Test symbols endpoint
    test_symbols_endpoint()
    
    print()
    
    # Test stocks endpoint 
    test_stocks_endpoint()
    
    print()
    print("🏁 Tests terminés")

if __name__ == "__main__":
    main()