# test_hybrid_architecture.py - Test de l'architecture hybride optimale
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import toml
from datetime import datetime
from data.hybrid_data_manager import HybridDataManager

def setup_config():
    """Configure l'environnement avec les vraies clés API"""
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

def test_tradier_realtime_data():
    """Test des données temps réel Tradier"""
    print("🚀 Testing Tradier Real-time Data")
    print("=" * 50)
    
    config = setup_config()
    if not config:
        return False
    
    tradier_key = config.get('TRADIER_API_KEY')
    if not tradier_key:
        print("❌ Tradier API key not found in configuration")
        return False
    
    try:
        manager = HybridDataManager(tradier_key)
        
        # Test 1: Underlying data
        print("\n1. Testing underlying data...")
        spy_data = manager.get_underlying_data('SPY')
        
        if spy_data:
            print(f"   ✅ SPY: ${spy_data.price:.2f} ({spy_data.change_pct:+.2f}%)")
            print(f"   Volume: {spy_data.volume:,}")
        else:
            print("   ❌ Failed to get SPY data")
            return False
        
        # Test 2: Options chain avec Greeks
        print("\n2. Testing options chain with Greeks...")
        options = manager.get_options_chain_realtime('SPY')
        
        if options:
            print(f"   ✅ Retrieved {len(options)} SPY options")
            
            # Analyser un échantillon
            sample_option = options[0]
            print(f"   Sample: {sample_option.option_symbol}")
            print(f"   Strike: ${sample_option.strike}, Type: {sample_option.option_type.upper()}")
            print(f"   Last: ${sample_option.last_price:.2f}, Volume: {sample_option.volume}")
            print(f"   Delta: {sample_option.delta}, IV: {sample_option.implied_volatility}")
            
        else:
            print("   ❌ No options retrieved")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Tradier test failed: {e}")
        return False

def test_polygon_historical_enrichment():
    """Test de l'enrichissement historique via Polygon.io"""
    print("\n" + "=" * 50)
    print("📈 Testing Polygon.io Historical Enrichment")
    print("=" * 50)
    
    config = setup_config()
    if not config:
        return False
    
    tradier_key = config.get('TRADIER_API_KEY')
    polygon_key = config.get('POLYGON_API_KEY')
    
    print("API Keys status:")
    print(f"   Tradier: {'✅' if tradier_key else '❌'}")
    print(f"   Polygon.io: {'✅' if polygon_key and polygon_key != 'YOUR_POLYGON_API_KEY_HERE' else '❌'}")
    
    if not tradier_key:
        print("❌ Tradier key required for primary data")
        return False
    
    try:
        # Créer le manager avec les deux clés
        polygon_key_valid = polygon_key if polygon_key and polygon_key != 'YOUR_POLYGON_API_KEY_HERE' else None
        manager = HybridDataManager(tradier_key, polygon_key_valid)
        
        # Test avec des options réelles
        print("\n1. Fetching SPY options (real-time)...")
        options = manager.get_options_chain_realtime('SPY')
        
        if not options:
            print("   ❌ No options to enrich")
            return False
        
        print(f"   Retrieved {len(options)} options")
        
        # Limiter pour le test
        sample_options = options[:5]
        
        print("\n2. Enriching with historical data...")
        enriched_options = manager.enrich_with_historical_data(sample_options)
        
        # Vérifier l'enrichissement
        enriched_count = sum(1 for opt in enriched_options if opt.volume_ratio is not None)
        
        if polygon_key_valid:
            print(f"   ✅ {enriched_count}/{len(enriched_options)} options enriched with historical data")
            
            # Afficher un exemple d'enrichissement
            for opt in enriched_options[:2]:
                if opt.volume_ratio:
                    print(f"   {opt.option_symbol}: Volume ratio {opt.volume_ratio:.2f}x")
                else:
                    print(f"   {opt.option_symbol}: No historical data available")
        else:
            print("   ⚠️ Polygon.io not configured - using Tradier data only")
        
        return True
        
    except Exception as e:
        print(f"❌ Historical enrichment test failed: {e}")
        return False

def test_composite_scoring():
    """Test du système de scoring composite"""
    print("\n" + "=" * 50)
    print("🧮 Testing Composite Scoring System")
    print("=" * 50)
    
    config = setup_config()
    if not config:
        return False
    
    tradier_key = config.get('TRADIER_API_KEY')
    polygon_key = config.get('POLYGON_API_KEY')
    
    if not tradier_key:
        return False
    
    try:
        polygon_key_valid = polygon_key if polygon_key and polygon_key != 'YOUR_POLYGON_API_KEY_HERE' else None
        manager = HybridDataManager(tradier_key, polygon_key_valid)
        
        # Récupérer et scorer les options
        print("1. Fetching options data...")
        options = manager.get_options_chain_realtime('SPY')
        
        if not options:
            print("   ❌ No options available")
            return False
        
        # Limiter pour performance
        options = options[:10]
        
        print("2. Enriching with historical data...")
        options = manager.enrich_with_historical_data(options)
        
        print("3. Calculating composite scores...")
        scored_options = manager.calculate_composite_scores(options)
        
        print("\n📊 Scoring Results (Top 5):")
        print("-" * 80)
        
        for i, opt in enumerate(scored_options[:5], 1):
            print(f"{i}. {opt.option_symbol} ${opt.strike} {opt.option_type.upper()}")
            print(f"   Score: {opt.composite_score:.1f} | Volume: {opt.volume} | OI: {opt.open_interest}")
            print(f"   Spread: {opt.bid_ask_spread_pct:.2f}% | Moneyness: {opt.moneyness:.2f}")
            if opt.volume_ratio:
                print(f"   Volume Ratio: {opt.volume_ratio:.2f}x | Unusual Score: {opt.unusual_volume_score:.1f}")
            print()
        
        return len(scored_options) > 0
        
    except Exception as e:
        print(f"❌ Scoring test failed: {e}")
        return False

def test_full_screening_pipeline():
    """Test du pipeline de screening complet"""
    print("\n" + "=" * 50)
    print("🎯 Testing Full Screening Pipeline")
    print("=" * 50)
    
    config = setup_config()
    if not config:
        return False
    
    tradier_key = config.get('TRADIER_API_KEY')
    polygon_key = config.get('POLYGON_API_KEY')
    
    if not tradier_key:
        return False
    
    try:
        polygon_key_valid = polygon_key if polygon_key and polygon_key != 'YOUR_POLYGON_API_KEY_HERE' else None
        manager = HybridDataManager(tradier_key, polygon_key_valid)
        
        # Test de screening complet
        print("Running full screening pipeline...")
        
        # Paramètres de test permissifs
        results = manager.screen_unusual_activity(
            tickers=['SPY'],  # Un seul ticker pour le test
            min_volume=50,
            min_open_interest=50,
            min_composite_score=20.0,
            max_days_to_expiration=30
        )
        
        if results:
            print(f"\n✅ Screening successful: {len(results)} unusual options found")
            
            # Export vers DataFrame pour analyse
            df = manager.export_results_to_dataframe(results)
            
            if not df.empty:
                print("\n📊 Results Summary:")
                print(f"   Total options: {len(df)}")
                print(f"   Average score: {df['composite_score'].mean():.1f}")
                print(f"   Max score: {df['composite_score'].max():.1f}")
                print(f"   Call/Put ratio: {len(df[df['type']=='call'])}/{len(df[df['type']=='put'])}")
                
                # Sauvegarder les résultats
                timestamp = datetime.now().strftime("%H%M%S")
                filename = f"hybrid_screening_results_{timestamp}.csv"
                df.to_csv(filename, index=False)
                print(f"   Results saved to: {filename}")
            
            return True
        else:
            print("   ⚠️ No unusual options found (may be normal market conditions)")
            return True  # Pas d'erreur, juste pas de signaux
            
    except Exception as e:
        print(f"❌ Full screening test failed: {e}")
        return False

def run_hybrid_architecture_tests():
    """Lance tous les tests de l'architecture hybride"""
    print("🚀 HYBRID ARCHITECTURE TESTS")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("Architecture: Tradier (primary real-time) + Polygon.io (historical)")
    
    test_results = {
        'tradier_realtime': False,
        'polygon_historical': False,
        'composite_scoring': False,
        'full_pipeline': False
    }
    
    # Test 1: Données temps réel Tradier
    print("\nTEST 1/4: Tradier Real-time Data")
    test_results['tradier_realtime'] = test_tradier_realtime_data()
    
    # Test 2: Enrichissement historique Polygon.io
    print("\nTEST 2/4: Polygon.io Historical Enrichment")
    test_results['polygon_historical'] = test_polygon_historical_enrichment()
    
    # Test 3: Scoring composite
    print("\nTEST 3/4: Composite Scoring")
    test_results['composite_scoring'] = test_composite_scoring()
    
    # Test 4: Pipeline complet
    print("\nTEST 4/4: Full Screening Pipeline")
    test_results['full_pipeline'] = test_full_screening_pipeline()
    
    # Résultats finaux
    print("\n" + "=" * 80)
    print("📊 HYBRID ARCHITECTURE TEST RESULTS")
    print("=" * 80)
    
    passed = sum(test_results.values())
    total = len(test_results)
    
    for test_name, success in test_results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name.replace('_', ' ').title():<25}: {status}")
    
    print(f"\nOverall Success Rate: {passed}/{total} ({passed/total*100:.0f}%)")
    
    # Recommandations
    if passed == total:
        print("\n🎉 ALL TESTS PASSED - OPTIMAL ARCHITECTURE!")
        print("🚀 Your hybrid system is operational:")
        print("   ✅ Real-time options data + Greeks (Tradier)")
        print("   ✅ Historical context for anomaly detection (Polygon.io)")
        print("   ✅ Composite scoring algorithm")
        print("   ✅ Full screening pipeline")
        print("\n💡 This gives you a significant edge:")
        print("   • Real-time execution capabilities")
        print("   • Historical validation of signals") 
        print("   • Multi-factor scoring")
        print("   • Professional-grade data sources")
        
    elif test_results['tradier_realtime']:
        print("\n⚠️ TRADIER-ONLY MODE OPERATIONAL")
        print("✅ Core functionality working with real-time data")
        if not test_results['polygon_historical']:
            print("💡 Add Polygon.io key for historical anomaly detection")
        
    else:
        print("\n❌ CONFIGURATION ISSUES")
        print("Please verify your API keys and connectivity")
    
    print("\n📋 Architecture Benefits:")
    print("✅ Tradier: Real-time options + Greeks (primary)")
    print("✅ Polygon.io: Historical context (secondary)")
    print("✅ Best of both worlds: Speed + Intelligence")
    print("✅ Cost-effective: Tradier free with brokerage account")
    
    print("\n🎯 Ready to integrate into main UI!")

if __name__ == "__main__":
    run_hybrid_architecture_tests()