# test_final_integration.py - Test final de l'intégration Polygon.io avec configuration complète
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import toml
from datetime import datetime
from data.polygon_client import create_polygon_client
from data.advanced_anomaly_detector import AdvancedAnomalyDetector
from data.enhanced_screener_v2 import EnhancedScreenerV2
import asyncio

def setup_config():
    """Configure l'environnement de test"""
    try:
        # Charger secrets.toml
        with open('.streamlit/secrets.toml', 'r') as f:
            secrets = toml.load(f)
        
        # Simuler st.secrets pour les tests
        class MockSecrets:
            def __init__(self, secrets_dict):
                self._secrets = secrets_dict
            
            def get(self, key, default=None):
                return self._secrets.get(key, default)
        
        st.secrets = MockSecrets(secrets)
        
        return secrets
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return None

def test_polygon_client_integration():
    """Test du client Polygon.io avec votre configuration"""
    print("🔗 Testing Polygon.io Client Integration")
    print("=" * 50)
    
    # Récupérer la configuration
    config = setup_config()
    if not config:
        return False
    
    polygon_api_key = config.get('POLYGON_API_KEY')
    
    if not polygon_api_key or polygon_api_key == "YOUR_POLYGON_API_KEY_HERE":
        print("❌ Polygon.io API key not configured!")
        print("Please set POLYGON_API_KEY in .streamlit/secrets.toml")
        return False
    
    try:
        # Créer le client
        client = create_polygon_client(polygon_api_key)
        
        # Test 1: Market Status
        print("\n1. Testing market status...")
        status = client.get_market_status()
        print(f"   Market: {status['market']}")
        print("   ✅ Market status OK")
        
        # Test 2: Stock Aggregates
        print("\n2. Testing stock aggregates...")
        bars = client.get_stock_aggregates('SPY')
        if bars:
            latest_bar = bars[-1]
            print(f"   SPY latest: ${latest_bar.close:.2f}, Volume: {latest_bar.volume:,}")
            print(f"   ✅ Retrieved {len(bars)} bars")
        else:
            print("   ⚠️ No stock data retrieved")
        
        # Test 3: Unusual Volume Analysis
        print("\n3. Testing unusual volume analysis...")
        tickers = ['SPY', 'QQQ', 'TSLA']
        unusual_results = client.analyze_unusual_volume(tickers, days_back=15)
        
        if unusual_results:
            print(f"   ✅ Found unusual activity in {len(unusual_results)} tickers:")
            for ticker, data in list(unusual_results.items())[:3]:
                print(f"      {ticker}: Volume Z-score {data['volume_z_score']:.2f}")
        else:
            print("   📊 No unusual volume detected (normal market conditions)")
        
        return True
        
    except Exception as e:
        print(f"❌ Client test failed: {e}")
        return False

def test_advanced_anomaly_detector():
    """Test du détecteur d'anomalies avec données réelles"""
    print("\n" + "=" * 50)
    print("🔍 Testing Advanced Anomaly Detector")
    print("=" * 50)
    
    config = setup_config()
    if not config:
        return False
    
    polygon_api_key = config.get('POLYGON_API_KEY')
    
    if not polygon_api_key or polygon_api_key == "YOUR_POLYGON_API_KEY_HERE":
        print("❌ Using simulated data (no API key)")
        polygon_api_key = None  # Will use mock data
    
    try:
        # Créer le détecteur
        detector = AdvancedAnomalyDetector(polygon_api_key=polygon_api_key)
        
        # Test avec tickers ultra-liquides
        test_tickers = ['SPY', 'QQQ']  # Réduire pour éviter rate limits
        
        print(f"\nBuilding baseline for {len(test_tickers)} tickers...")
        detector.build_historical_baseline(test_tickers, days_back=20)
        
        if detector.lookup_table:
            total_data = sum(len(dates) for dates in detector.lookup_table.values())
            print(f"✅ Baseline built: {total_data} data points")
            
            # Scan d'anomalies
            print("\nRunning anomaly scan...")
            today = datetime.now().strftime('%Y-%m-%d')
            results = detector.comprehensive_anomaly_scan(test_tickers, today)
            
            print("📊 Scan results:")
            print(f"   Volume anomalies: {len(results['volume_anomalies'])}")
            print(f"   Trades anomalies: {len(results['trades_anomalies'])}")
            print(f"   Combined anomalies: {len(results['combined_anomalies'])}")
            
            # Afficher top anomalies
            if results['volume_anomalies']:
                print("\n🔥 Top volume anomaly:")
                top = results['volume_anomalies'][0]
                print(f"   {top.ticker}: Z-score {top.z_score:.2f}, Severity {top.severity_score:.1f}")
            
            return True
        else:
            print("❌ No baseline data loaded")
            return False
            
    except Exception as e:
        print(f"❌ Anomaly detector test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_enhanced_screener_v2():
    """Test du screener enhanced V2 avec toutes les intégrations"""
    print("\n" + "=" * 50)
    print("🚀 Testing Enhanced Screener V2")
    print("=" * 50)
    
    config = setup_config()
    if not config:
        return False
    
    # Vérifier les clés API
    polygon_key = config.get('POLYGON_API_KEY')
    openai_key = config.get('OPENAI_API_KEY')
    perplexity_key = config.get('PERPLEXITY_API_KEY')
    
    print("API Keys available:")
    print(f"   Polygon.io: {'✅' if polygon_key and polygon_key != 'YOUR_POLYGON_API_KEY_HERE' else '❌'}")
    print(f"   OpenAI: {'✅' if openai_key else '❌'}")
    print(f"   Perplexity: {'✅' if perplexity_key else '❌'}")
    
    try:
        # Créer le screener
        screener = EnhancedScreenerV2(
            enable_ai=bool(openai_key or perplexity_key),
            enable_anomaly_detection=bool(polygon_key and polygon_key != 'YOUR_POLYGON_API_KEY_HERE'),
            polygon_api_key=polygon_key if polygon_key != 'YOUR_POLYGON_API_KEY_HERE' else None
        )
        
        # Test screening complet
        test_tickers = ['SPY', 'QQQ']  # Limiter pour les tests
        
        def progress_callback(progress, message):
            print(f"[{progress*100:5.1f}%] {message}")
        
        print("\nRunning comprehensive screening...")
        
        # Paramètres permissifs pour avoir des résultats
        screening_params = {
            'max_dte': 45,
            'min_volume': 500,
            'min_oi': 300,
            'min_whale_score': 40
        }
        
        results = await screener.comprehensive_screening(
            tickers=test_tickers,
            screening_params=screening_params,
            enable_ai_analysis=True,
            enable_anomaly_detection=True,
            progress_callback=progress_callback
        )
        
        # Analyser les résultats
        print("\n📊 Comprehensive Screening Results:")
        print(f"   Tickers analyzed: {len(results['tickers_scanned'])}")
        print(f"   Market anomalies: {len(results['market_anomalies'].get('volume_anomalies', []))}")
        print(f"   Traditional screening: {len(results['traditional_screening'].get('all', []))}")
        print(f"   AI enhanced: {len(results['ai_enhanced_results'])}")
        print(f"   Combined signals: {len(results['combined_signals'])}")
        
        if results['combined_signals']:
            top_signal = results['combined_signals'][0]
            print(f"\n⭐ Top Signal: {top_signal['ticker']} (Score: {top_signal['total_score']:.1f})")
        
        # Sauvegarder les résultats
        screener.save_results(results)
        
        return True
        
    except Exception as e:
        print(f"❌ Enhanced Screener test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_integration_tests():
    """Lance tous les tests d'intégration"""
    print("🚀 FINAL INTEGRATION TESTS")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        'polygon_client': False,
        'anomaly_detector': False,
        'enhanced_screener': False
    }
    
    # Test 1: Client Polygon.io
    print("\nTEST 1/3: Polygon.io Client")
    results['polygon_client'] = test_polygon_client_integration()
    
    # Test 2: Advanced Anomaly Detector
    print("\nTEST 2/3: Advanced Anomaly Detector") 
    results['anomaly_detector'] = test_advanced_anomaly_detector()
    
    # Test 3: Enhanced Screener V2 (async)
    print("\nTEST 3/3: Enhanced Screener V2")
    results['enhanced_screener'] = asyncio.run(test_enhanced_screener_v2())
    
    # Résumé final
    print("\n" + "=" * 80)
    print("📊 FINAL RESULTS")
    print("=" * 80)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name.replace('_', ' ').title():<25}: {status}")
    
    print(f"\nOverall Success Rate: {passed}/{total} ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
        print("🚀 Your squeeze-finder is fully operational with:")
        print("   ✅ Professional-grade Polygon.io data")
        print("   ✅ ML-based anomaly detection") 
        print("   ✅ AI-powered analysis")
        print("   ✅ Multi-source signal fusion")
        print("\n🎯 Ready for production use!")
        
    elif passed >= 2:
        print("\n⚠️ PARTIAL SUCCESS - Core functionality working")
        print("Check configuration for failed components")
        
    else:
        print("\n❌ MULTIPLE FAILURES")
        print("Please verify API keys and connectivity")
    
    print("\n📋 Next Steps:")
    if results['polygon_client']:
        print("1. ✅ Polygon.io integration ready")
    else:
        print("1. ❌ Configure Polygon.io API key in secrets.toml")
    
    if results['anomaly_detector']:
        print("2. ✅ ML anomaly detection operational")
    else:
        print("2. ❌ Check anomaly detection setup")
    
    if results['enhanced_screener']:
        print("3. ✅ Full screener pipeline working")
    else:
        print("3. ❌ Review screener configuration")
    
    print("\n🚀 Launch UI with: streamlit run ui/dashboard.py")

if __name__ == "__main__":
    run_integration_tests()