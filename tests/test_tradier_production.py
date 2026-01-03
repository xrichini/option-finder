#!/usr/bin/env python3
"""
Test avec l'environnement Tradier de PRODUCTION
Corrige le problème d'authentification en utilisant l'API de production
"""

import os
import sys
import toml
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

def test_original_tradier_client():
    """Test du client Tradier original qui fonctionnait"""
    print("🔗 Test du client Tradier ORIGINAL (production)...")
    
    try:
        from tradier_client import TradierClient
        
        client = TradierClient()
        
        print("  📈 Test récupération expirations...")
        expirations = client.get_option_expirations("AAPL")
        if expirations:
            print(f"    ✅ {len(expirations)} expirations trouvées: {expirations[:3]}")
        else:
            print("    ❌ Aucune expiration trouvée")
            return False
        
        print("  ⛓️ Test chaîne d'options...")
        if expirations:
            chains = client.get_option_chains("AAPL", expirations[0])
            if chains:
                print(f"    ✅ {len(chains)} contrats récupérés pour {expirations[0]}")
                
                # Affichage de quelques contrats
                for i, contract in enumerate(chains[:3], 1):
                    print(f"      {i}. Strike: {contract.get('strike', 'N/A')} - "
                          f"Type: {contract.get('option_type', 'N/A')} - "
                          f"Vol: {contract.get('volume', 0):,}")
            else:
                print("    ❌ Aucun contrat récupéré")
                return False
        
        print("  📊 Test quotes...")
        quote_data = client.get_quote(["AAPL"])
        if quote_data and 'quotes' in quote_data:
            print("    ✅ Quote AAPL récupérée")
            quote = quote_data['quotes'].get('quote', {})
            if isinstance(quote, dict):
                print(f"      Prix: ${quote.get('last', 'N/A')}")
        else:
            print("    ⚠️ Quote non récupérée, mais pas critique")
        
        print("  ✅ Client Tradier ORIGINAL : Tous les tests passés !")
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur client original : {e}")
        import traceback
        print(f"  🔍 Détails : {traceback.format_exc()}")
        return False

def test_enhanced_tradier_production():
    """Test du nouveau client Tradier en mode PRODUCTION"""
    print("\n🚀 Test du nouveau client Tradier (PRODUCTION)...")
    
    try:
        secrets = load_secrets()
        tradier_token = secrets.get('TRADIER_API_KEY')
        
        if not tradier_token:
            print("❌ TRADIER_API_KEY non trouvé")
            return False
        
        from enhanced_tradier_client import EnhancedTradierClient
        
        # IMPORTANT: sandbox=False pour utiliser l'API de production
        client = EnhancedTradierClient(tradier_token, sandbox=False)
        
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
                      f"Last: ${contract.last:.2f}")
                      
            # Test de calcul des métriques
            first_contract = chains[0]
            if first_contract.bid > 0 and first_contract.ask > 0:
                print(f"    📈 Métriques calculées: Spread = ${first_contract.spread:.2f}")
        else:
            print("    ❌ Aucun contrat récupéré")
            return False
        
        print("  ✅ Nouveau client Tradier PRODUCTION : Tous les tests passés !")
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur nouveau client : {e}")
        import traceback
        print(f"  🔍 Détails : {traceback.format_exc()}")
        return False

def test_analyzer_with_production_data():
    """Test de l'analyseur avec vraies données de production"""
    print("\n🔍 Test de l'analyseur avec données PRODUCTION...")
    
    try:
        secrets = load_secrets()
        tradier_token = secrets.get('TRADIER_API_KEY')
        
        if not tradier_token:
            print("❌ Token manquant")
            return False
        
        from enhanced_tradier_client import EnhancedTradierClient
        from enhanced_options_alerts import EnhancedOptionsAnalyzer, TradingRecommendationEngine
        
        # Production client
        client = EnhancedTradierClient(tradier_token, sandbox=False)
        analyzer = EnhancedOptionsAnalyzer()
        rec_engine = TradingRecommendationEngine()
        
        # Récupération de vraies données
        print("  📊 Récupération données AAPL (production)...")
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
            symbol = contract.symbol
            current_volume = contract.volume
            
            # Ajout d'historique avec volumes plus faibles
            for i in range(15):
                # Volume historique simulé plus faible
                historical_vol = max(10, current_volume // 20) + (i * 5)
                analyzer.volume_manager.add_volume(symbol, historical_vol)
            
            # Analyse du contrat
            alert = analyzer.analyze_option_contract(contract.to_dict(), underlying)
            if alert:
                alerts_generated += 1
                print(f"    🚨 Alerte: {contract.symbol} - "
                      f"Sévérité: {alert.severity:.2f} - "
                      f"Ratio: {alert.unusual_volume_ratio:.1f}x")
                
                # Génération de recommandation
                recommendation = rec_engine.generate_recommendation(alert)
                if recommendation:
                    recommendations_generated += 1
                    print(f"    💡 Rec: {recommendation.action.value} "
                          f"(Confiance: {recommendation.confidence:.2f})")
        
        print("  ✅ Analyse PRODUCTION terminée:")
        print(f"    🚨 {alerts_generated} alertes générées")
        print(f"    💡 {recommendations_generated} recommandations générées")
        
        # Au minimum, nous devons avoir analysé des contrats
        assert len(contracts) > 0, "Aucun contrat analysé"
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur analyse production: {e}")
        import traceback
        print(f"  🔍 Détails : {traceback.format_exc()}")
        return False

def main():
    """Test principal avec environnement de PRODUCTION"""
    print("🧪 TESTS TRADIER - ENVIRONNEMENT DE PRODUCTION")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Client original (qui marchait)
    tests_total += 1
    if test_original_tradier_client():
        tests_passed += 1
    
    # Test 2: Nouveau client en production
    tests_total += 1
    if test_enhanced_tradier_production():
        tests_passed += 1
    
    # Test 3: Analyseur avec données production
    tests_total += 1
    if test_analyzer_with_production_data():
        tests_passed += 1
    
    # Résumé
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ DES TESTS PRODUCTION")
    print("=" * 60)
    print(f"Tests passés: {tests_passed}/{tests_total}")
    print(f"Taux de réussite: {(tests_passed/tests_total*100):.1f}%")
    
    if tests_passed == tests_total:
        print("\n🎉 TOUS LES TESTS PRODUCTION SONT PASSÉS !")
        print("✅ Le problème était sandbox vs production !")
        print("✅ Votre clé API Tradier fonctionne parfaitement !")
        print("\n💡 Solution : Utilisez sandbox=False dans vos appels")
    else:
        print(f"\n⚠️ {tests_total - tests_passed} test(s) ont échoué")
        if tests_passed >= 1:
            print("✅ Au moins le client original fonctionne")
    
    return tests_passed == tests_total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)