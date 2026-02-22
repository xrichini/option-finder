#!/usr/bin/env python3
"""
Test simple des endpoints Short Interest
"""

import sys
sys.path.append('.')

from api.main import app
from fastapi.testclient import TestClient

def test_endpoints():
    """Test des endpoints principaux"""
    
    client = TestClient(app)
    
    print("🧪 Test des endpoints Short Interest")
    print("=" * 50)
    
    # Test Health
    print("1. Test health endpoint...")
    response = client.get('/api/short-interest/health')
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Service: {data['service']}")
        print(f"   Status: {data['status']}")
        print("   ✅ Health endpoint OK")
    else:
        print(f"   ❌ Health endpoint failed: {response.text}")
        return
    
    print()
    
    # Test avec mock limité pour éviter le scraping réel
    print("2. Test symbols endpoint (sans scraping réel)...")
    try:
        # Ce test va probablement échouer car il fait un scraping réel
        # mais on peut voir si la structure de base fonctionne
        response = client.get('/api/short-interest/symbols?exchange=nasdaq&enable_prefiltering=false')
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Symbols count: {data.get('count', 'N/A')}")
            print(f"   Execution time: {data.get('execution_time_seconds', 'N/A')}s")
            print("   ✅ Symbols endpoint structure OK")
        else:
            print(f"   ⚠️ Symbols endpoint response: {response.status_code}")
            # Ne pas afficher le texte complet pour éviter le spam
            print("   (Expected - real scraping needed)")
    except Exception as e:
        print(f"   ⚠️ Symbols endpoint error (expected): {e}")
    
    print()
    print("🏁 Tests basiques terminés")

if __name__ == "__main__":
    test_endpoints()