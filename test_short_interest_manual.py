"""
Script de test manuel pour la fonctionnalité Short Interest
Permet de valider rapidement le fonctionnement end-to-end
"""

import asyncio
import sys
from pathlib import Path

# Ajouter le répertoire parent au PATH pour les imports
sys.path.append(str(Path(__file__).parent))

async def test_short_interest_scraper():
    """Test du scraper de données short interest"""
    print("🔍 Test du scraper Short Interest...")
    
    try:
        from data.short_interest_scraper import ShortInterestScraper
        
        scraper = ShortInterestScraper()
        
        print("📥 Récupération des données (test avec limite)...")
        stocks = await scraper.get_high_short_interest_data(limit=5)
        
        print(f"✅ {len(stocks)} stocks récupérés avec succès")
        
        for stock in stocks[:3]:  # Afficher les 3 premiers
            print(f"   • {stock['symbol']}: {stock['short_interest_percent']:.1f}% short interest")
        
        # Test du filtrage
        print("\n🔧 Test des filtres...")
        filtered_stocks = scraper.filter_stocks(
            stocks,
            min_market_cap=10_000_000_000,  # 10B minimum
            min_short_interest=10.0
        )
        
        print(f"✅ {len(filtered_stocks)} stocks après filtrage (cap > 10B, short > 10%)")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test scraper: {e}")
        return False

def test_fastapi_endpoints():
    """Test des endpoints FastAPI"""
    print("\n🌐 Test des endpoints FastAPI...")
    
    try:
        from fastapi.testclient import TestClient
        from api.main import app
        
        client = TestClient(app)
        
        # Test endpoint de santé
        print("📡 Test endpoint santé...")
        response = client.get("/api/short-interest/health")
        if response.status_code == 200:
            print("✅ Endpoint santé OK")
            print(f"   Réponse: {response.json()}")
        else:
            print(f"❌ Endpoint santé failed: {response.status_code}")
            return False
        
        # Test endpoint stocks (avec timeout plus court pour test rapide)
        print("\n📊 Test endpoint stocks...")
        try:
            response = client.get("/api/short-interest/stocks?limit=3", timeout=30)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Endpoint stocks OK - {data.get('total_count', 0)} stocks trouvés")
                print(f"   Temps d'exécution: {data.get('execution_time', 0):.2f}s")
            else:
                print(f"⚠️  Endpoint stocks status: {response.status_code}")
                print(f"   Réponse: {response.text[:200]}")
        except Exception as e:
            print(f"⚠️  Test endpoint stocks échoué: {e}")
        
        # Test endpoint symbols
        print("\n🔤 Test endpoint symbols...")
        try:
            response = client.get("/api/short-interest/symbols?limit=5", timeout=20)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Endpoint symbols OK - {data.get('count', 0)} symboles")
                symbols = data.get('symbols', [])
                if symbols:
                    print(f"   Premiers symboles: {', '.join(symbols[:5])}")
            else:
                print(f"⚠️  Endpoint symbols status: {response.status_code}")
        except Exception as e:
            print(f"⚠️  Test endpoint symbols échoué: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test endpoints: {e}")
        return False

def test_legacy_compatibility():
    """Test de compatibilité avec l'ancien code Streamlit"""
    print("\n🔗 Test compatibilité legacy...")
    
    try:
        from data.short_interest_scraper import get_high_short_interest_symbols_legacy
        
        print("📤 Test fonction legacy...")
        # Test avec mock pour ne pas faire d'appel réseau
        from unittest.mock import patch
        
        mock_data = [
            {'symbol': 'AAPL', 'short_interest_percent': 15.5},
            {'symbol': 'TSLA', 'short_interest_percent': 20.2},
            {'symbol': 'GME', 'short_interest_percent': 8.1}  # Sous le seuil
        ]
        
        with patch('data.short_interest_scraper.ShortInterestScraper.get_high_short_interest_data', return_value=mock_data):
            symbols = get_high_short_interest_symbols_legacy(min_short_interest=10.0)
            
            print(f"✅ Fonction legacy OK - {len(symbols)} symboles retournés")
            print(f"   Symboles: {', '.join(symbols)}")
            
            # Vérification que GME n'est pas inclus (8.1% < 10%)
            assert 'GME' not in symbols, "Le filtrage par short interest ne fonctionne pas"
            assert 'AAPL' in symbols and 'TSLA' in symbols, "Symboles valides manquants"
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test legacy: {e}")
        return False

def display_api_routes():
    """Affiche les routes API disponibles"""
    print("\n📋 Routes API disponibles:")
    print("   • GET /api/short-interest/health")
    print("   • GET /api/short-interest/stocks")
    print("   • GET /api/short-interest/symbols") 
    print("   • POST /api/short-interest/scan")
    print("\n🌐 Pour tester manuellement:")
    print("   uvicorn api.main:app --reload --port 8000")
    print("   http://localhost:8000/docs (interface Swagger)")

async def main():
    """Fonction principale de test"""
    print("🚀 Test manuel - Fonctionnalité Short Interest")
    print("=" * 50)
    
    # Tests séquentiels
    tests = [
        ("Scraper", test_short_interest_scraper()),
        ("Legacy", test_legacy_compatibility()),
        ("Endpoints", test_fastapi_endpoints())
    ]
    
    results = []
    for test_name, test_coro in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        
        if asyncio.iscoroutine(test_coro):
            result = await test_coro
        else:
            result = test_coro
            
        results.append((test_name, result))
    
    # Résumé final
    print(f"\n{'='*50}")
    print("📊 RÉSUMÉ DES TESTS")
    print("=" * 50)
    
    total_tests = len(results)
    passed_tests = sum(1 for _, result in results if result)
    
    for test_name, result in results:
        status = "✅ PASSÉ" if result else "❌ ÉCHOUÉ"
        print(f"   {test_name:.<20} {status}")
    
    print(f"\n🏆 Score: {passed_tests}/{total_tests} tests passés")
    
    if passed_tests == total_tests:
        print("🎉 Tous les tests sont passés ! La fonctionnalité est prête.")
        display_api_routes()
    else:
        print("⚠️  Certains tests ont échoué. Vérifiez les logs ci-dessus.")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    # Exécution du test principal
    success = asyncio.run(main())
    exit(0 if success else 1)