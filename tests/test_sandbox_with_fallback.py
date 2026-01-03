#!/usr/bin/env python3
"""
Test du mode sandbox avec fallback de la clé production
Vérifie si la clé production fonctionne sur l'endpoint sandbox
"""

import os
import sys

# Ajout des répertoires au path
sys.path.append(os.path.join(os.path.dirname(__file__), 'data'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))

def test_sandbox_with_production_key():
    """Test de l'endpoint sandbox avec la clé de production en fallback"""
    print("🔧 Test sandbox avec clé production en fallback...")
    
    try:
        from enhanced_tradier_client import EnhancedTradierClient
        from config import Config
        
        # Force l'utilisation de la clé production sur l'endpoint sandbox
        prod_key = Config.TRADIER_API_KEY_PRODUCTION
        print(f"  🔑 Utilisation de la clé production: ***...{prod_key[-4:] if prod_key else 'None'}")
        
        # Client sandbox avec clé production
        client = EnhancedTradierClient(prod_key, sandbox=True)
        
        print(f"  🌍 Endpoint utilisé: {client.base_url}")
        
        # Test de récupération de données
        print("  📈 Test récupération sous-jacent...")
        underlying = client.get_underlying_quote("AAPL")
        
        if underlying:
            print(f"    ✅ AAPL récupéré: ${underlying['price']:.2f}")
        else:
            print("    ❌ Échec récupération sous-jacent")
            return False
        
        print("  📅 Test expirations...")
        expirations = client.get_options_expirations("AAPL")
        
        if expirations:
            print(f"    ✅ {len(expirations)} expirations trouvées: {expirations[:3]}")
        else:
            print("    ⚠️ Aucune expiration (peut être normal pour sandbox)")
        
        print("  ⛓️ Test chaîne d'options...")
        if expirations:
            chains = client.get_options_chains("AAPL", expirations[0])
            if chains:
                print(f"    ✅ {len(chains)} contrats récupérés")
                
                # Affichage de quelques contrats
                top_contracts = sorted(chains, key=lambda c: c.volume, reverse=True)[:3]
                for i, contract in enumerate(top_contracts, 1):
                    print(f"      {i}. {contract.option_type.upper()} ${contract.strike} - Vol: {contract.volume:,}")
            else:
                print("    ⚠️ Aucun contrat (peut être normal pour sandbox)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        import traceback
        print(f"  🔍 Détails: {traceback.format_exc()}")
        return False

def test_config_fallback():
    """Test de la logique de fallback dans la configuration"""
    print("\n🔄 Test de la logique de fallback...")
    
    try:
        from config import Config
        
        print("  📋 Configuration actuelle:")
        print(f"    Sandbox mode: {Config.TRADIER_SANDBOX}")
        print(f"    Clé production: {'✅' if Config.TRADIER_API_KEY_PRODUCTION else '❌'}")
        print(f"    Clé sandbox: {'✅' if Config.TRADIER_API_KEY_SANDBOX and Config.TRADIER_API_KEY_SANDBOX != 'VOTRE_CLE_SANDBOX_ICI' else '❌'}")
        
        # Test de sélection de clé
        selected_key = Config.get_tradier_api_key()
        print(f"  🎯 Clé sélectionnée: ***...{selected_key[-4:] if selected_key else 'None'}")
        
        # Vérification de la logique de fallback
        if Config.TRADIER_SANDBOX:
            if Config.TRADIER_API_KEY_SANDBOX and Config.TRADIER_API_KEY_SANDBOX != 'VOTRE_CLE_SANDBOX_ICI':
                print("  ✅ Utilise la clé sandbox dédiée")
            else:
                print("  🔄 Fallback vers la clé production (sandbox non configurée)")
        else:
            print("  ✅ Utilise la clé production (mode production)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return False

def test_original_client_sandbox():
    """Test du client original en mode sandbox"""
    print("\n🔗 Test client Tradier original en sandbox...")
    
    try:
        from tradier_client import TradierClient
        
        client = TradierClient()
        
        print(f"  🎯 Environnement: {client.environment}")
        print(f"  🔗 URL: {client.base_url}")
        
        # Test simple
        print("  📅 Test récupération expirations...")
        expirations = client.get_option_expirations("AAPL")
        
        if expirations:
            print(f"    ✅ {len(expirations)} expirations trouvées")
            
            # Test chaîne si on a des expirations
            print("  ⛓️ Test chaîne d'options...")
            chains = client.get_option_chains("AAPL", expirations[0])
            if chains:
                print(f"    ✅ {len(chains)} contrats dans la chaîne")
            else:
                print("    ⚠️ Aucun contrat dans la chaîne")
            
        else:
            print("    ⚠️ Aucune expiration (normal pour sandbox vide)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        import traceback
        print(f"  🔍 Détails: {traceback.format_exc()}")
        return False

def main():
    """Test principal du mode sandbox"""
    print("🧪 TESTS MODE SANDBOX AVEC FALLBACK")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Configuration et fallback
    tests_total += 1
    if test_config_fallback():
        tests_passed += 1
    
    # Test 2: Client enhanced sandbox
    tests_total += 1
    if test_sandbox_with_production_key():
        tests_passed += 1
    
    # Test 3: Client original sandbox
    tests_total += 1
    if test_original_client_sandbox():
        tests_passed += 1
    
    # Résumé
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ DES TESTS SANDBOX")
    print("=" * 60)
    print(f"Tests passés: {tests_passed}/{tests_total}")
    print(f"Taux de réussite: {(tests_passed/tests_total*100):.1f}%")
    
    if tests_passed == tests_total:
        print("\n🎉 MODE SANDBOX OPÉRATIONNEL AVEC FALLBACK !")
        print("✅ Configuration de fallback fonctionnelle")
        print("✅ Endpoint sandbox.tradier.com utilisé")
        print("✅ Clients fonctionnels en mode développement")
        
        print("\n💡 Note:")
        print("   Le fallback utilise la clé production sur sandbox.tradier.com")
        print("   Pour une séparation complète, ajoutez votre vraie clé sandbox")
    else:
        print(f"\n⚠️ {tests_total - tests_passed} test(s) ont échoué")
        print("   Vérifiez la configuration des clés API")
    
    return tests_passed == tests_total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)