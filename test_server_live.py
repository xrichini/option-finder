#!/usr/bin/env python3
"""
Test des endpoints avec serveur en marche
"""

import requests
import sys

BASE_URL = "http://127.0.0.1:8001"  # Port utilisé précédemment

def check_server_health():
    """Vérifier si le serveur est en marche"""
    try:
        response = requests.get(f"{BASE_URL}/api/short-interest/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def test_health_endpoint():
    """Test endpoint health"""
    print("1. Test Health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/short-interest/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Status: {data['status']}")
            print(f"   Service: {data['service']}")
            return True
        else:
            print(f"   ❌ Status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_symbols_endpoint():
    """Test endpoint symbols avec timeout plus long"""
    print("2. Test Symbols endpoint (peut prendre du temps - scraping réel)...")
    try:
        response = requests.get(
            f"{BASE_URL}/api/short-interest/symbols?exchange=nasdaq&min_market_cap=100000000&enable_prefiltering=true", 
            timeout=60  # Timeout plus long pour scraping + enrichissement
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Symbols retrieved: {data['count']}")
            print(f"   Execution time: {data['execution_time_seconds']:.2f}s")
            print(f"   Filtering applied: {data['filtering_applied']}")
            if data['symbols']:
                print(f"   First 5 symbols: {', '.join(data['symbols'][:5])}")
            return True
        else:
            print(f"   ❌ Status code: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            return False
    except requests.RequestException as e:
        print(f"   ❌ Request error: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return False

def test_stocks_endpoint():
    """Test endpoint stocks avec données détaillées"""
    print("3. Test Stocks endpoint (détails complets - peut prendre du temps)...")
    try:
        response = requests.get(
            f"{BASE_URL}/api/short-interest/stocks?exchange=nasdaq&min_market_cap=100000000&min_short_interest=20.0&enable_prefiltering=true", 
            timeout=90  # Timeout encore plus long pour enrichissement complet
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Stocks filtered: {data['filtered_count']}/{data['total_count']}")
            print(f"   Execution time: {data['execution_time_seconds']:.2f}s")
            
            if data['stocks']:
                print("   Top 3 stocks by short interest:")
                for i, stock in enumerate(data['stocks'][:3], 1):
                    print(f"   {i}. {stock['symbol']}: {stock['short_interest_pct']:.1f}%")
                    if stock.get('market_cap'):
                        print(f"      Market cap: ${stock['market_cap']:,}")
                    if stock.get('sector'):
                        print(f"      Sector: {stock['sector']}")
            return True
        else:
            print(f"   ❌ Status code: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            return False
    except requests.RequestException as e:
        print(f"   ❌ Request error: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return False

def main():
    """Test principal avec serveur en marche"""
    print("🚀 Test des endpoints Short Interest avec serveur live")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print()
    
    # Vérifier si le serveur est en marche
    print("Vérification du serveur...")
    if not check_server_health():
        print("❌ Serveur non accessible!")
        print("   Veuillez démarrer le serveur avec:")
        print("   python -m uvicorn api.main:app --host 127.0.0.1 --port 8001")
        return 1
    print("✅ Serveur accessible")
    print()
    
    # Tests
    success_count = 0
    total_tests = 3
    
    if test_health_endpoint():
        success_count += 1
    print()
    
    if test_symbols_endpoint():
        success_count += 1
    print()
    
    if test_stocks_endpoint():
        success_count += 1
    print()
    
    # Résultats
    print("=" * 60)
    print(f"🏁 Tests terminés: {success_count}/{total_tests} réussis")
    
    if success_count == total_tests:
        print("🎉 Tous les tests ont réussi!")
        return 0
    else:
        print("⚠️ Certains tests ont échoué")
        return 1

if __name__ == "__main__":
    sys.exit(main())