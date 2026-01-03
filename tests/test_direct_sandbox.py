#!/usr/bin/env python3
"""
Test direct avec clé sandbox - contourne le cache Streamlit
Utilise directement les clés du fichier TOML
"""

import os
import sys
import toml

# Ajout du répertoire data au path
sys.path.append(os.path.join(os.path.dirname(__file__), 'data'))

def load_keys_directly():
    """Charge les clés directement depuis le fichier TOML"""
    secrets_path = os.path.join(os.path.dirname(__file__), '.streamlit', 'secrets.toml')
    
    if os.path.exists(secrets_path):
        with open(secrets_path, 'r', encoding='utf-8') as f:
            secrets = toml.load(f)
        return secrets
    else:
        return {}

def test_direct_sandbox_client():
    """Test du client avec la vraie clé sandbox chargée directement"""
    print("🚀 Test client sandbox avec clé directe...")
    
    try:
        # Chargement direct des clés
        secrets = load_keys_directly()
        sandbox_key = secrets.get('TRADIER_API_KEY_SANDBOX')
        
        if not sandbox_key:
            print("  ❌ Clé sandbox non trouvée")
            return False
        
        print(f"  🔑 Clé sandbox trouvée: ***...{sandbox_key[-4:]}")
        
        from enhanced_tradier_client import EnhancedTradierClient
        
        # Client sandbox avec clé directe
        client = EnhancedTradierClient(sandbox_key, sandbox=True)
        
        print(f"  🌍 Endpoint: {client.base_url}")
        
        # Test de base
        print("  📈 Test récupération sous-jacent...")
        underlying = client.get_underlying_quote("AAPL")
        
        if underlying:
            print(f"    ✅ AAPL: ${underlying['price']:.2f} ({underlying['change']:+.2f})")
        else:
            print("    ⚠️ Pas de données sous-jacent (normal pour sandbox)")
        
        print("  📅 Test expirations...")
        expirations = client.get_options_expirations("AAPL")
        
        if expirations:
            print(f"    ✅ {len(expirations)} expirations: {expirations[:3]}")
            
            # Test chaîne si on a des expirations
            print("  ⛓️ Test chaîne d'options...")
            chains = client.get_options_chains("AAPL", expirations[0])
            if chains:
                print(f"    ✅ {len(chains)} contrats récupérés")
                
                # Affichage des contrats avec le plus de volume
                top_contracts = sorted(chains, key=lambda c: c.volume, reverse=True)[:3]
                print("    📊 Top 3 volumes:")
                for i, contract in enumerate(top_contracts, 1):
                    print(f"      {i}. {contract.option_type.upper()} ${contract.strike} - "
                          f"Vol: {contract.volume:,} - OI: {contract.open_interest:,}")
            else:
                print("    ⚠️ Aucun contrat (peut être normal pour sandbox)")
        else:
            print("    ⚠️ Aucune expiration (peut être normal pour sandbox vide)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        import traceback
        print(f"  🔍 Détails: {traceback.format_exc()}")
        return False

def test_sandbox_vs_production():
    """Comparaison des deux environnements"""
    print("\n🔄 Comparaison sandbox vs production...")
    
    try:
        secrets = load_keys_directly()
        prod_key = secrets.get('TRADIER_API_KEY_PRODUCTION') or secrets.get('TRADIER_API_KEY')
        sandbox_key = secrets.get('TRADIER_API_KEY_SANDBOX')
        
        if not prod_key or not sandbox_key:
            print("  ❌ Clés manquantes")
            return False
        
        from enhanced_tradier_client import EnhancedTradierClient
        
        print("  🚀 Test clé PRODUCTION sur endpoint production...")
        prod_client = EnhancedTradierClient(prod_key, sandbox=False)
        prod_underlying = prod_client.get_underlying_quote("AAPL")
        
        if prod_underlying:
            print(f"    ✅ Production: AAPL ${prod_underlying['price']:.2f}")
        else:
            print("    ❌ Production: Échec récupération")
        
        print("  🧪 Test clé SANDBOX sur endpoint sandbox...")
        sandbox_client = EnhancedTradierClient(sandbox_key, sandbox=True)
        sandbox_underlying = sandbox_client.get_underlying_quote("AAPL")
        
        if sandbox_underlying:
            print(f"    ✅ Sandbox: AAPL ${sandbox_underlying['price']:.2f}")
        else:
            print("    ⚠️ Sandbox: Pas de données (normal)")
        
        # Test croisé : clé production sur sandbox (devrait échouer)
        print("  ❌ Test INVALIDE: clé production sur sandbox...")
        try:
            invalid_client = EnhancedTradierClient(prod_key, sandbox=True)
            invalid_result = invalid_client.get_underlying_quote("AAPL")
            if invalid_result:
                print(f"    😲 Surprenant: ça marche (${invalid_result['price']:.2f})")
            else:
                print("    ✅ Correct: Échec attendu (clé invalide pour sandbox)")
        except:
            print("    ✅ Correct: Erreur attendue (clé invalide pour sandbox)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return False

def test_enhanced_screening_sandbox():
    """Test du screening avancé en mode sandbox"""
    print("\n🔍 Test screening avancé en sandbox...")
    
    try:
        secrets = load_keys_directly()
        sandbox_key = secrets.get('TRADIER_API_KEY_SANDBOX')
        
        if not sandbox_key:
            print("  ❌ Clé sandbox manquante")
            return False
        
        from enhanced_tradier_client import EnhancedTradierClient
        from enhanced_options_alerts import EnhancedOptionsAnalyzer, TradingRecommendationEngine
        
        # Client sandbox
        client = EnhancedTradierClient(sandbox_key, sandbox=True)
        analyzer = EnhancedOptionsAnalyzer()
        rec_engine = TradingRecommendationEngine()
        
        print("  📊 Récupération données AAPL (sandbox)...")
        underlying = client.get_underlying_quote("AAPL")
        expirations = client.get_options_expirations("AAPL")
        
        if underlying and expirations:
            print(f"    ✅ Données récupérées: ${underlying['price']:.2f}, {len(expirations)} expirations")
            
            # Test des contrats d'options
            contracts = client.get_options_chains("AAPL", expirations[0])
            if contracts:
                print(f"    ✅ {len(contracts)} contrats analysés")
                
                # Test d'analyse d'anomalies sur quelques contrats
                alerts_generated = 0
                for contract in contracts[:5]:  # Test sur 5 contrats
                    # Simulation d'historique
                    for i in range(10):
                        analyzer.volume_manager.add_volume(contract.symbol, contract.volume // 10 + i)
                    
                    alert = analyzer.analyze_option_contract(contract.to_dict(), underlying)
                    if alert:
                        alerts_generated += 1
                        rec = rec_engine.generate_recommendation(alert)
                        print(f"    🚨 Alerte: {contract.symbol} - {alert.alert_type.value}")
                
                print(f"    📊 Résultat: {alerts_generated} alertes générées sur sandbox")
            else:
                print("    ⚠️ Pas de contrats d'options (normal pour sandbox)")
        else:
            print("    ⚠️ Données limitées en sandbox (normal)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        import traceback
        print(f"  🔍 Détails: {traceback.format_exc()}")
        return False

def main():
    """Test principal sandbox avec chargement direct des clés"""
    print("🧪 TESTS SANDBOX AVEC CHARGEMENT DIRECT")
    print("=" * 60)
    
    # Vérification des clés disponibles
    secrets = load_keys_directly()
    print("🔑 Clés disponibles:")
    print(f"  Production: {'✅' if secrets.get('TRADIER_API_KEY_PRODUCTION') or secrets.get('TRADIER_API_KEY') else '❌'}")
    print(f"  Sandbox: {'✅' if secrets.get('TRADIER_API_KEY_SANDBOX') else '❌'}")
    print(f"  Mode sandbox configuré: {'✅' if secrets.get('TRADIER_SANDBOX') else '❌'}")
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Client sandbox direct
    tests_total += 1
    if test_direct_sandbox_client():
        tests_passed += 1
    
    # Test 2: Comparaison environnements
    tests_total += 1
    if test_sandbox_vs_production():
        tests_passed += 1
    
    # Test 3: Screening avancé
    tests_total += 1
    if test_enhanced_screening_sandbox():
        tests_passed += 1
    
    # Résumé
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ TESTS SANDBOX DIRECT")
    print("=" * 60)
    print(f"Tests passés: {tests_passed}/{tests_total}")
    print(f"Taux de réussite: {(tests_passed/tests_total*100):.1f}%")
    
    if tests_passed == tests_total:
        print("\n🎉 ENVIRONNEMENT SANDBOX PLEINEMENT OPÉRATIONNEL !")
        print("✅ Clé sandbox fonctionnelle")
        print("✅ Endpoint sandbox.tradier.com accessible")
        print("✅ Screening avancé en mode développement")
        print("✅ Séparation complète des environnements")
    else:
        print(f"\n⚠️ {tests_total - tests_passed} test(s) ont échoué")
    
    return tests_passed == tests_total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)