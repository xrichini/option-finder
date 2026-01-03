#!/usr/bin/env python3
"""
Test complet avec les vraies clés API
Utilise les tokens du fichier secrets.toml pour tester toutes les fonctionnalités
"""

import os
import sys
import time
import toml
from datetime import datetime
from typing import Dict
import logging

# Ajout du répertoire data au path
sys.path.append(os.path.join(os.path.dirname(__file__), 'data'))

# Configuration logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_secrets() -> Dict[str, str]:
    """Charge les secrets depuis le fichier .streamlit/secrets.toml"""
    secrets_path = os.path.join(os.path.dirname(__file__), '.streamlit', 'secrets.toml')
    
    if os.path.exists(secrets_path):
        with open(secrets_path, 'r') as f:
            secrets = toml.load(f)
        return secrets
    else:
        logger.warning("Fichier secrets.toml non trouvé")
        return {}

def test_enhanced_tradier_with_real_api():
    """Test du client Tradier avec vraie API"""
    print("🔗 Test du client Tradier avec vraie API...")
    
    try:
        secrets = load_secrets()
        tradier_token = secrets.get('TRADIER_API_KEY')
        
        if not tradier_token:
            print("❌ TRADIER_API_KEY non trouvé dans secrets.toml")
            return False
        
        # Import du client
        from enhanced_tradier_client import EnhancedTradierClient
        
        # Initialisation (sandbox pour les tests)
        client = EnhancedTradierClient(tradier_token, sandbox=True)
        
        print("  📈 Test récupération sous-jacent...")
        underlying = client.get_underlying_quote("AAPL")
        if underlying:
            print(f"    ✅ AAPL: ${underlying['price']:.2f} ({underlying['change']:+.2f})")
        else:
            print("    ❌ Échec récupération sous-jacent")
            return False
        
        print("  📅 Test expirations...")
        expirations = client.get_options_expirations("AAPL")
        if expirations:
            print(f"    ✅ {len(expirations)} expirations trouvées: {expirations[:3]}")
        else:
            print("    ❌ Aucune expiration trouvée")
            return False
        
        print("  ⛓️ Test chaînes d'options...")
        chains = client.get_options_chains("AAPL", expirations[0])
        if chains:
            print(f"    ✅ {len(chains)} contrats récupérés pour {expirations[0]}")
            
            # Affichage de quelques contrats intéressants
            high_volume_contracts = sorted(chains, key=lambda c: c.volume, reverse=True)[:3]
            print("    📊 Top 3 volumes:")
            for i, contract in enumerate(high_volume_contracts, 1):
                print(f"      {i}. {contract.option_type.upper()} ${contract.strike} - "
                      f"Vol: {contract.volume:,} - OI: {contract.open_interest:,} - "
                      f"Prix: ${contract.last:.2f}")
        else:
            print("    ❌ Aucun contrat récupéré")
            return False
        
        print("  ✅ Client Tradier : Tous les tests passés !")
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur : {e}")
        return False

def test_integrated_screening_with_real_api():
    """Test du moteur intégré avec vraie API"""
    print("\n🚀 Test du moteur de screening intégré avec vraie API...")
    
    try:
        secrets = load_secrets()
        tradier_token = secrets.get('TRADIER_API_KEY')
        polygon_key = secrets.get('POLYGON_API_KEY')
        
        if not tradier_token:
            print("❌ TRADIER_API_KEY non trouvé")
            return False
        
        # Import du moteur
        from integrated_screening_engine import IntegratedScreeningEngine
        
        print("  🔧 Initialisation du moteur...")
        engine = IntegratedScreeningEngine(
            tradier_token=tradier_token,
            polygon_api_key=polygon_key,
            tradier_sandbox=True  # Sandbox pour éviter les frais
        )
        
        # Test avec une petite watchlist
        test_watchlist = ["AAPL", "TSLA"]
        print(f"  📋 Test avec watchlist: {test_watchlist}")
        
        # Paramètres de test allégés
        test_params = {
            'min_volume': 50,
            'min_open_interest': 250,
            'max_days_to_expiry': 45,
            'max_concurrent_symbols': 2
        }
        
        print("  ⏳ Lancement du screening (peut prendre 30-60s)...")
        start_time = time.time()
        
        results = engine.run_comprehensive_screening(
            watchlist=test_watchlist,
            custom_params=test_params
        )
        
        duration = time.time() - start_time
        
        # Analyse des résultats
        stats = results['statistics']
        alerts = results['alerts']
        recommendations = results['recommendations']
        
        print(f"  ✅ Screening terminé en {duration:.1f}s")
        print(f"    📈 Symboles analysés: {stats['symbols_analyzed']}")
        print(f"    📋 Contrats analysés: {stats['contracts_analyzed']}")
        print(f"    🚨 Alertes générées: {stats['alerts_generated']}")
        print(f"    💡 Recommandations: {stats['recommendations_generated']}")
        
        # Affichage des meilleures alertes
        top_alerts = alerts['top_alerts'][:3]
        if top_alerts:
            print("    🏆 Top 3 alertes:")
            for i, alert in enumerate(top_alerts, 1):
                print(f"      {i}. {alert.get('ticker')} - {alert.get('alert_type')} "
                      f"(Sévérité: {alert.get('severity', 0):.2f})")
        
        # Affichage des meilleures recommandations
        top_recs = recommendations['top_recommendations'][:3]
        if top_recs:
            print("    💎 Top 3 recommandations:")
            for i, rec in enumerate(top_recs, 1):
                print(f"      {i}. {rec.get('ticker')} - {rec.get('action')} "
                      f"(Confiance: {rec.get('confidence', 0):.2f})")
        
        # Sauvegarde des résultats
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"real_api_screening_results_{timestamp}.json"
        saved_file = engine.save_results(results, filename)
        print(f"    💾 Résultats sauvés: {saved_file}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur : {e}")
        import traceback
        print(f"  🔍 Détails : {traceback.format_exc()}")
        return False

def test_options_analyzer_with_real_data():
    """Test de l'analyseur avec des vraies données"""
    print("\n🔍 Test de l'analyseur avec vraies données...")
    
    try:
        secrets = load_secrets()
        tradier_token = secrets.get('TRADIER_API_KEY')
        
        if not tradier_token:
            print("❌ Token manquant")
            return False
        
        from enhanced_tradier_client import EnhancedTradierClient
        from enhanced_options_alerts import EnhancedOptionsAnalyzer, TradingRecommendationEngine
        
        # Client et analyseur
        client = EnhancedTradierClient(tradier_token, sandbox=True)
        analyzer = EnhancedOptionsAnalyzer()
        rec_engine = TradingRecommendationEngine()
        
        # Récupération de vraies données
        print("  📊 Récupération données AAPL...")
        underlying = client.get_underlying_quote("AAPL")
        expirations = client.get_options_expirations("AAPL")
        
        if not underlying or not expirations:
            print("  ❌ Impossible de récupérer les données")
            return False
        
        # Chaîne d'options
        contracts = client.get_options_chains("AAPL", expirations[0])
        if not contracts:
            print("  ❌ Aucun contrat trouvé")
            return False
        
        print(f"  ✅ {len(contracts)} contrats analysés")
        
        # Analyse des contrats avec le plus de volume
        high_volume_contracts = sorted(contracts, key=lambda c: c.volume, reverse=True)[:5]
        
        alerts_generated = 0
        recommendations_generated = 0
        
        print("  🔍 Analyse des contrats à fort volume...")
        for contract in high_volume_contracts:
            # Simulation d'historique pour déclencher des alertes
            for i in range(10):
                analyzer.volume_manager.add_volume(contract.symbol, contract.volume // 10 + i * 10)
            
            # Analyse du contrat
            alert = analyzer.analyze_option_contract(contract.to_dict(), underlying)
            if alert:
                alerts_generated += 1
                print(f"    🚨 Alerte: {contract.symbol} - Sévérité: {alert.severity:.2f}")
                
                # Génération de recommandation
                recommendation = rec_engine.generate_recommendation(alert)
                if recommendation:
                    recommendations_generated += 1
                    print(f"    💡 Rec: {recommendation.action.value} (Confiance: {recommendation.confidence:.2f})")
        
        print(f"  ✅ Analyse terminée: {alerts_generated} alertes, {recommendations_generated} recommandations")
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur : {e}")
        return False

def main():
    """Test principal avec vraies APIs"""
    print("🧪 TESTS COMPLETS AVEC VRAIES APIs")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Client Tradier
    tests_total += 1
    if test_enhanced_tradier_with_real_api():
        tests_passed += 1
    
    # Test 2: Analyseur avec vraies données
    tests_total += 1
    if test_options_analyzer_with_real_data():
        tests_passed += 1
    
    # Test 3: Moteur intégré (plus long)
    tests_total += 1
    if test_integrated_screening_with_real_api():
        tests_passed += 1
    
    # Résumé
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ DES TESTS AVEC VRAIES APIs")
    print("=" * 60)
    print(f"Tests passés: {tests_passed}/{tests_total}")
    print(f"Taux de réussite: {(tests_passed/tests_total*100):.1f}%")
    
    if tests_passed == tests_total:
        print("\n🎉 TOUS LES TESTS AVEC VRAIES APIs SONT PASSÉS !")
        print("✅ Votre architecture hybride fonctionne parfaitement !")
        print("✅ Les améliorations du starter sont opérationnelles !")
    else:
        print(f"\n⚠️ {tests_total - tests_passed} test(s) ont échoué")
    
    return tests_passed == tests_total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)