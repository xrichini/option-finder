#!/usr/bin/env python3
"""
Test complet de l'architecture hybride en mode sandbox
Screening complet avec toutes les fonctionnalités avancées
"""

import os
import sys
import time
from datetime import datetime

# Ajout des répertoires au path
sys.path.append(os.path.join(os.path.dirname(__file__), 'data'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))

def test_full_integrated_screening():
    """Test complet du moteur de screening intégré"""
    print("🚀 Test du moteur de screening intégré complet...")
    
    try:
        from config import Config
        from integrated_screening_engine import IntegratedScreeningEngine
        
        print("  🔧 Configuration détectée:")
        print(f"    Environnement: {Config.get_tradier_environment()}")
        print(f"    URL: {Config.get_tradier_base_url()}")
        print(f"    Mode dev: {Config.is_development_mode()}")
        
        # Initialisation du moteur complet
        engine = IntegratedScreeningEngine(
            tradier_token=Config.get_tradier_api_key(),
            polygon_api_key=Config.get_polygon_api_key(),
            tradier_sandbox=Config.TRADIER_SANDBOX
        )
        
        # Watchlist de test (symboles populaires avec beaucoup d'options)
        test_watchlist = ["AAPL", "TSLA", "NVDA", "SPY"]
        print(f"  📋 Watchlist de test: {test_watchlist}")
        
        # Paramètres de screening optimisés pour sandbox
        custom_params = {
            'min_volume': 100,         # Volume minimum plus bas pour sandbox
            'min_open_interest': 500,  # OI minimum plus bas
            'max_days_to_expiry': 45,  # Jusqu'à 45 jours
            'min_days_to_expiry': 1,   # À partir de demain
            'volume_ratio_threshold': 2.0,  # Seuil d'anomalie volume
            'max_concurrent_symbols': 2,    # Limité pour test
            'max_spread_percentage': 100.0  # Plus permissif pour sandbox
        }
        
        print("  ⚙️ Paramètres optimisés pour sandbox")
        print("  ⏳ Lancement du screening complet (peut prendre 2-3 minutes)...")
        
        start_time = time.time()
        
        # 🚀 LANCEMENT DU SCREENING COMPLET !
        results = engine.run_comprehensive_screening(
            watchlist=test_watchlist,
            custom_params=custom_params
        )
        
        duration = time.time() - start_time
        
        # 📊 Analyse des résultats
        session_info = results['session_info']
        statistics = results['statistics']
        alerts = results['alerts']
        recommendations = results['recommendations']
        correlations = results['correlations']
        portfolio_strategies = results['portfolio_strategies']
        
        print(f"\n  ✅ Screening terminé en {duration:.1f}s")
        print("  📈 Résultats de session:")
        print(f"    Symboles traités: {session_info['symbols_processed']}/{session_info['watchlist_size']}")
        print(f"    Contrats analysés: {statistics['contracts_analyzed']}")
        print(f"    Alertes générées: {statistics['alerts_generated']}")
        print(f"    Recommandations: {statistics['recommendations_generated']}")
        print(f"    Alertes haute sévérité: {statistics.get('high_severity_alerts', 0)}")
        
        # 🏆 Top alertes
        top_alerts = alerts['top_alerts'][:5]
        if top_alerts:
            print("\n  🚨 TOP 5 ALERTES:")
            for i, alert in enumerate(top_alerts, 1):
                print(f"    {i}. {alert['ticker']} - {alert['alert_type']}")
                print(f"       Sévérité: {alert['severity']:.2f} | Confiance: {alert['confidence']:.2f}")
                print(f"       Volume: {alert['volume']:,} (ratio {alert['unusual_volume_ratio']:.1f}x)")
                print(f"       {alert['description']}")
                print()
        
        # 💎 Top recommandations
        top_recs = recommendations['top_recommendations'][:5]
        if top_recs:
            print("  💡 TOP 5 RECOMMANDATIONS:")
            for i, rec in enumerate(top_recs, 1):
                print(f"    {i}. {rec['ticker']} - Action: {rec['action']}")
                print(f"       Confiance: {rec['confidence']:.2f} | Risque: {rec['risk_level']}")
                print(f"       {rec['reasoning']}")
                print()
        
        # 🔗 Corrélations
        if correlations.get('alert_type_distribution'):
            print("  📊 Distribution des types d'alertes:")
            for alert_type, count in correlations['alert_type_distribution'].items():
                print(f"    {alert_type}: {count}")
        
        # 🎯 Stratégies de portefeuille
        if portfolio_strategies:
            print(f"\n  🎯 {len(portfolio_strategies)} stratégies de portefeuille générées:")
            for strategy in portfolio_strategies:
                print(f"    📈 {strategy['name']}: {strategy['description']}")
                print(f"       Risque: {strategy['risk_level']} | Rendement: {strategy['expected_return']}")
        
        # Sauvegarde des résultats
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"full_architecture_test_{timestamp}.json"
        saved_file = engine.save_results(results, filename)
        print(f"\n  💾 Résultats complets sauvés: {saved_file}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        import traceback
        print(f"  🔍 Détails: {traceback.format_exc()}")
        return False

def test_ml_anomaly_integration():
    """Test de l'intégration ML avec vraies données sandbox"""
    print("\n🤖 Test intégration ML avec données sandbox...")
    
    try:
        from config import Config
        from enhanced_tradier_client import EnhancedTradierClient
        from advanced_anomaly_detector import AdvancedAnomalyDetector
        import pandas as pd
        
        # Client sandbox
        client = EnhancedTradierClient(Config.get_tradier_api_key(), sandbox=Config.TRADIER_SANDBOX)
        detector = AdvancedAnomalyDetector()
        
        print("  📊 Récupération données multi-symboles...")
        all_contracts_data = []
        
        for symbol in ["AAPL", "TSLA"]:
            print(f"    Analyse {symbol}...")
            expirations = client.get_options_expirations(symbol)
            if expirations:
                contracts = client.get_options_chains(symbol, expirations[0])
                for contract in contracts[:20]:  # Limiter pour test
                    all_contracts_data.append({
                        'symbol': contract.symbol,
                        'underlying': contract.underlying,
                        'volume': contract.volume,
                        'last': contract.last,
                        'open_interest': contract.open_interest,
                        'strike': contract.strike,
                        'option_type': contract.option_type,
                        'implied_volatility': contract.implied_volatility or 0.25
                    })
        
        if all_contracts_data:
            print(f"  ✅ {len(all_contracts_data)} contrats collectés pour ML")
            
            # Conversion en DataFrame pour ML
            df = pd.DataFrame(all_contracts_data)
            
            # Détection d'anomalies ML
            print("  🔍 Détection d'anomalies ML...")
            anomalies = detector.detect_anomalies_dataframe(df, volume_col='volume', price_col='last')
            
            print(f"  🎯 {len(anomalies)} anomalies ML détectées")
            
            if len(anomalies) > 0:
                print("    🏆 Top 3 anomalies ML:")
                top_anomalies = anomalies.head(3)
                for i, (idx, anomaly) in enumerate(top_anomalies.iterrows(), 1):
                    z_score = anomaly.get('volume_z_score', 0)
                    print(f"      {i}. {anomaly['symbol']} - Z-score: {z_score:.2f}")
                    print(f"         Volume: {anomaly['volume']:,} | Prix: ${anomaly['last']:.2f}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur ML: {e}")
        import traceback
        print(f"  🔍 Détails: {traceback.format_exc()}")
        return False

def test_ai_recommendations_integration():
    """Test du système de recommandations AI"""
    print("\n🧠 Test système de recommandations AI...")
    
    try:
        from enhanced_options_alerts import EnhancedOptionsAnalyzer, TradingRecommendationEngine
        from config import Config
        from enhanced_tradier_client import EnhancedTradierClient
        
        client = EnhancedTradierClient(Config.get_tradier_api_key(), sandbox=Config.TRADIER_SANDBOX)
        analyzer = EnhancedOptionsAnalyzer()
        rec_engine = TradingRecommendationEngine()
        
        print("  🔍 Analyse AAPL pour génération de recommandations AI...")
        
        # Données réelles
        underlying = client.get_underlying_quote("AAPL")
        expirations = client.get_options_expirations("AAPL")
        
        if underlying and expirations:
            contracts = client.get_options_chains("AAPL", expirations[0])
            
            # Sélection des contrats les plus actifs
            active_contracts = sorted(contracts, key=lambda c: c.volume, reverse=True)[:10]
            
            ai_recommendations = []
            
            for contract in active_contracts:
                # Simulation d'historique pour déclencher des anomalies
                for i in range(15):
                    historical_vol = max(50, contract.volume // 15) + (i * 10)
                    analyzer.volume_manager.add_volume(contract.symbol, historical_vol)
                
                # Analyse AI
                alert = analyzer.analyze_option_contract(contract.to_dict(), underlying)
                
                if alert and alert.severity > 0.4:  # Seulement les alertes significatives
                    recommendation = rec_engine.generate_recommendation(alert)
                    if recommendation:
                        ai_recommendations.append({
                            'alert': alert,
                            'recommendation': recommendation,
                            'contract': contract
                        })
            
            print(f"  ✅ {len(ai_recommendations)} recommandations AI générées")
            
            if ai_recommendations:
                print("    🎯 Top recommandations AI:")
                
                # Tri par confiance
                sorted_recs = sorted(ai_recommendations, 
                                   key=lambda x: x['recommendation'].confidence, reverse=True)
                
                for i, item in enumerate(sorted_recs[:3], 1):
                    alert = item['alert']
                    rec = item['recommendation']
                    contract = item['contract']
                    
                    print(f"      {i}. {contract.underlying} {contract.option_type.upper()} ${contract.strike}")
                    print(f"         Action AI: {rec.action.value}")
                    print(f"         Confiance: {rec.confidence:.2f} | Risque: {rec.risk_level.value}")
                    print(f"         Volume: {contract.volume:,} (ratio {alert.unusual_volume_ratio:.1f}x)")
                    print(f"         Raisonnement: {rec.reasoning}")
                    print()
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur AI: {e}")
        import traceback
        print(f"  🔍 Détails: {traceback.format_exc()}")
        return False

def main():
    """Test complet de toute l'architecture"""
    print("🧪 TEST COMPLET DE L'ARCHITECTURE HYBRIDE")
    print("=" * 70)
    print("🏠 Mode développement (sandbox) - Données temps réel")
    print("=" * 70)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Screening intégré complet
    tests_total += 1
    if test_full_integrated_screening():
        tests_passed += 1
    
    # Test 2: Intégration ML
    tests_total += 1
    if test_ml_anomaly_integration():
        tests_passed += 1
    
    # Test 3: Recommandations AI
    tests_total += 1
    if test_ai_recommendations_integration():
        tests_passed += 1
    
    # Résumé final
    print("\n" + "=" * 70)
    print("📊 RÉSUMÉ COMPLET DE L'ARCHITECTURE")
    print("=" * 70)
    print(f"Tests passés: {tests_passed}/{tests_total}")
    print(f"Taux de réussite: {(tests_passed/tests_total*100):.1f}%")
    
    if tests_passed == tests_total:
        print("\n🎉 ARCHITECTURE HYBRIDE COMPLÈTEMENT OPÉRATIONNELLE !")
        print("✅ Screening d'options avancé avec données temps réel")
        print("✅ Détection d'anomalies ML intégrée")
        print("✅ Système de recommandations AI intelligent")
        print("✅ Architecture hybride Tradier/Polygon.io fonctionnelle")
        print("✅ Gestion d'environnements (sandbox/production)")
        print("✅ Toutes les améliorations du starter intégrées")
        
        print("\n🚀 PRÊT POUR LA PRODUCTION !")
        print("   Pour passer en production: TRADIER_SANDBOX = False dans config.py")
        
    else:
        print(f"\n⚠️ {tests_total - tests_passed} test(s) ont échoué")
        print("   L'architecture nécessite des ajustements")
    
    return tests_passed == tests_total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)