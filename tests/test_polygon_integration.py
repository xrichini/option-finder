# test_polygon_integration.py - Test d'intégration avec Polygon.io
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.advanced_anomaly_detector import AdvancedAnomalyDetector
from datetime import datetime
import streamlit as st
import toml

def load_config():
    """Charge la configuration depuis secrets.toml"""
    try:
        # Charger le fichier secrets.toml
        with open('.streamlit/secrets.toml', 'r') as f:
            secrets = toml.load(f)
        
        # Simuler st.secrets pour les tests
        class MockSecrets:
            def __init__(self, secrets_dict):
                self._secrets = secrets_dict
            
            def get(self, key, default=None):
                return self._secrets.get(key, default)
            
            def __getitem__(self, key):
                return self._secrets[key]
        
        # Remplacer temporairement st.secrets
        original_secrets = getattr(st, 'secrets', None)
        st.secrets = MockSecrets(secrets)
        
        return secrets
    except Exception as e:
        print(f"❌ Erreur chargement config: {e}")
        return {}

def test_polygon_connection(api_key):
    """Test de base de la connexion Polygon.io"""
    print("🔗 Testing Polygon.io connection...")
    
    import requests
    
    # Test simple avec l'endpoint de status
    try:
        url = "https://api.polygon.io/v1/marketstatus/now"
        params = {'apikey': api_key}
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('status') == 'OK':
            print("✅ Polygon.io API connection successful")
            
            market_status = data.get('market', 'unknown')
            print(f"   Market status: {market_status}")
            
            return True
        else:
            print(f"❌ API Error: {data}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_polygon_aggregates(api_key):
    """Test de récupération de données agrégées"""
    print("\n📊 Testing aggregates data retrieval...")
    
    import requests
    from datetime import datetime, timedelta
    
    # Test avec SPY pour les 5 derniers jours
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)  # 7 jours pour s'assurer d'avoir 5 jours de trading
    
    try:
        url = f"https://api.polygon.io/v2/aggs/ticker/SPY/range/1/day/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"
        params = {'apikey': api_key}
        
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('status') == 'OK' and data.get('results'):
            results = data['results']
            print(f"✅ Retrieved {len(results)} days of SPY data")
            
            # Afficher un échantillon
            latest = results[-1]
            volume = latest.get('v', 0)
            close = latest.get('c', 0)
            transactions = latest.get('n', 0)
            
            print(f"   Latest day: Volume {volume:,}, Close ${close:.2f}, Transactions {transactions:,}")
            
            return True
        else:
            print(f"❌ No data or error: {data.get('status', 'Unknown')}")
            return False
            
    except Exception as e:
        print(f"❌ Error retrieving aggregates: {e}")
        return False

def test_advanced_anomaly_detector_with_polygon(api_key):
    """Test du détecteur d'anomalies avec vraies données Polygon.io"""
    print("\n🔍 Testing Advanced Anomaly Detector with Polygon.io...")
    
    try:
        # Initialiser le détecteur avec votre clé API
        detector = AdvancedAnomalyDetector(polygon_api_key=api_key)
        
        # Tickers de test ultra-liquides
        test_tickers = ['SPY', 'QQQ', 'TSLA']
        
        print(f"Building baseline for {len(test_tickers)} tickers...")
        
        # Construire la baseline avec vraies données
        detector.build_historical_baseline(test_tickers, days_back=30)
        
        # Vérifier que des données ont été chargées
        if detector.lookup_table:
            total_entries = sum(len(dates) for dates in detector.lookup_table.values())
            print(f"✅ Baseline built: {total_entries} data points across {len(detector.lookup_table)} tickers")
            
            # Test de détection d'anomalies
            today = datetime.now().strftime('%Y-%m-%d')
            results = detector.comprehensive_anomaly_scan(test_tickers, today)
            
            print("\n📈 Anomaly scan results:")
            print(f"   Volume anomalies: {len(results['volume_anomalies'])}")
            print(f"   Trades anomalies: {len(results['trades_anomalies'])}")
            print(f"   Combined anomalies: {len(results['combined_anomalies'])}")
            
            # Afficher les top anomalies
            if results['volume_anomalies']:
                print("\n🔥 Top volume anomalies:")
                for i, anomaly in enumerate(results['volume_anomalies'][:3], 1):
                    print(f"   {i}. {anomaly.ticker}: Z-score {anomaly.z_score:.2f}, "
                          f"Severity {anomaly.severity_score:.1f}")
            
            if results['trades_anomalies']:
                print("\n📊 Top trades anomalies:")
                for i, anomaly in enumerate(results['trades_anomalies'][:3], 1):
                    print(f"   {i}. {anomaly.ticker}: Z-score {anomaly.z_score:.2f}, "
                          f"Severity {anomaly.severity_score:.1f}")
            
            return True
        else:
            print("❌ No data loaded into lookup table")
            return False
            
    except Exception as e:
        print(f"❌ Error in anomaly detection test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_rate_limits(api_key):
    """Test des limites de taux pour compte free"""
    print("\n⏱️ Testing API rate limits (free tier)...")
    
    import requests
    import time
    
    # Le plan free de Polygon.io a généralement 5 requests/minute
    print("Making 3 requests in quick succession...")
    
    success_count = 0
    
    for i in range(3):
        try:
            url = "https://api.polygon.io/v1/marketstatus/now"
            params = {'apikey': api_key}
            
            start_time = time.time()
            response = requests.get(url, params=params, timeout=10)
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                success_count += 1
                print(f"   Request {i+1}: ✅ ({elapsed:.2f}s)")
            elif response.status_code == 429:
                print(f"   Request {i+1}: ❌ Rate limited")
                break
            else:
                print(f"   Request {i+1}: ❌ Status {response.status_code}")
            
            # Petit délai entre les requêtes
            if i < 2:
                time.sleep(1)
                
        except Exception as e:
            print(f"   Request {i+1}: ❌ Error: {e}")
    
    print(f"Rate limit test: {success_count}/3 requests successful")
    return success_count > 0

def main():
    """Fonction principale de test"""
    print("🚀 POLYGON.IO INTEGRATION TEST")
    print("=" * 50)
    
    # 1. Charger la configuration
    config = load_config()
    
    if not config:
        print("❌ Could not load configuration")
        return
    
    # 2. Récupérer la clé API
    polygon_api_key = config.get('POLYGON_API_KEY')
    
    if not polygon_api_key or polygon_api_key == "YOUR_POLYGON_API_KEY_HERE":
        print("❌ Polygon.io API key not configured!")
        print("Please add your API key to .streamlit/secrets.toml")
        print("POLYGON_API_KEY = \"your_actual_api_key_here\"")
        return
    
    print(f"✅ Polygon.io API key loaded: {polygon_api_key[:8]}...{polygon_api_key[-4:]}")
    
    # 3. Tests séquentiels
    tests_passed = 0
    total_tests = 4
    
    print("\n" + "="*50)
    print("RUNNING TESTS")
    print("="*50)
    
    # Test 1: Connexion de base
    if test_polygon_connection(polygon_api_key):
        tests_passed += 1
    
    # Test 2: Données agrégées
    if test_polygon_aggregates(polygon_api_key):
        tests_passed += 1
    
    # Test 3: Limites de taux
    if test_rate_limits(polygon_api_key):
        tests_passed += 1
    
    # Test 4: Détecteur d'anomalies complet
    if test_advanced_anomaly_detector_with_polygon(polygon_api_key):
        tests_passed += 1
    
    # 4. Résumé final
    print("\n" + "="*50)
    print("TEST RESULTS")
    print("="*50)
    
    print(f"Tests passed: {tests_passed}/{total_tests} ({tests_passed/total_tests*100:.0f}%)")
    
    if tests_passed == total_tests:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Polygon.io integration is fully functional")
        print("\nNext steps:")
        print("1. Your anomaly detection system is ready to use")
        print("2. You can now run the enhanced screener with real data")
        print("3. The ML-based anomaly detection will work with live market data")
    elif tests_passed >= total_tests/2:
        print("⚠️ PARTIAL SUCCESS")
        print("Some tests passed, but there may be configuration issues")
        print("Check the error messages above for details")
    else:
        print("❌ MULTIPLE FAILURES")
        print("Please check your API key and network connectivity")
    
    print("\n📋 Your Polygon.io plan limits:")
    print("   Free tier: ~5 requests/minute")
    print("   Consider upgrading for higher throughput if needed")

if __name__ == "__main__":
    main()