#!/usr/bin/env python3
"""
Test de gestion des environnements Tradier (sandbox vs production)
Démontre le basculement automatique basé sur la configuration
"""

import os
import sys

# Ajout des répertoires au path
sys.path.append(os.path.join(os.path.dirname(__file__), 'data'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))

def test_environment_detection():
    """Test de la détection automatique d'environnement"""
    print("🔍 Test de détection d'environnement...")
    
    try:
        from config import Config
        
        print("  📋 Configuration détectée:")
        print(f"    🔑 Clé API: {'✅' if Config.TRADIER_API_KEY else '❌'}")
        print(f"    🌍 Environnement: {Config.get_tradier_environment()}")
        print(f"    🔗 URL de base: {Config.get_tradier_base_url()}")
        print(f"    🛠️  Mode développement: {Config.is_development_mode()}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return False

def test_original_client_with_config():
    """Test du client original avec configuration automatique"""
    print("\n🔗 Test client Tradier original (config automatique)...")
    
    try:
        from tradier_client import TradierClient
        
        client = TradierClient()
        
        # Test simple
        print("  📅 Test récupération expirations...")
        expirations = client.get_option_expirations("AAPL")
        
        if expirations:
            print(f"    ✅ {len(expirations)} expirations trouvées")
            print(f"    🎯 Environnement utilisé: {client.environment}")
        else:
            print("    ⚠️ Aucune expiration (normal si sandbox sans données)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return False

def test_enhanced_client_auto_detection():
    """Test du client enhanced avec détection automatique"""
    print("\n🚀 Test client Enhanced (détection auto)...")
    
    try:
        from enhanced_tradier_client import EnhancedTradierClient
        from config import Config
        
        # Test avec détection automatique (pas de paramètre sandbox)
        client = EnhancedTradierClient(Config.TRADIER_API_KEY)
        
        print("  📈 Test récupération sous-jacent...")
        underlying = client.get_underlying_quote("AAPL")
        
        if underlying:
            print(f"    ✅ AAPL: ${underlying['price']:.2f}")
        else:
            print("    ⚠️ Pas de données (normal si sandbox)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        import traceback
        print(f"  🔍 Détails: {traceback.format_exc()}")
        return False

def test_explicit_environment_override():
    """Test avec surcharge explicite d'environnement"""
    print("\n🎭 Test surcharge explicite d'environnement...")
    
    try:
        from enhanced_tradier_client import EnhancedTradierClient
        from config import Config
        
        # Force production même si config dit sandbox
        print("  🔧 Force environnement production...")
        prod_client = EnhancedTradierClient(Config.TRADIER_API_KEY, sandbox=False)
        
        # Force sandbox même si config dit production
        print("  🔧 Force environnement sandbox...")
        sandbox_client = EnhancedTradierClient(Config.TRADIER_API_KEY, sandbox=True)
        
        print(f"    ✅ Client production URL: {prod_client.base_url}")
        print(f"    ✅ Client sandbox URL: {sandbox_client.base_url}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return False

def demonstrate_environment_switching():
    """Démontre comment basculer facilement d'environnement"""
    print("\n🔄 Démonstration basculement d'environnements...")
    
    print("  💡 Pour basculer d'environnement, modifiez dans .streamlit/secrets.toml:")
    print("     TRADIER_SANDBOX = true   # Pour développement/test")
    print("     TRADIER_SANDBOX = false  # Pour production")
    
    print("\n  🎯 Avantages de cette approche:")
    print("    ✅ Configuration centralisée")
    print("    ✅ Pas de code à modifier pour basculer")
    print("    ✅ Détection automatique de l'environnement")
    print("    ✅ Possibilité de surcharge explicite")
    print("    ✅ Logs clairs sur l'environnement utilisé")
    
    return True

def main():
    """Test principal de gestion d'environnement"""
    print("🧪 TESTS DE GESTION D'ENVIRONNEMENT TRADIER")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Détection d'environnement
    tests_total += 1
    if test_environment_detection():
        tests_passed += 1
    
    # Test 2: Client original avec config
    tests_total += 1
    if test_original_client_with_config():
        tests_passed += 1
    
    # Test 3: Client enhanced auto-détection
    tests_total += 1
    if test_enhanced_client_auto_detection():
        tests_passed += 1
    
    # Test 4: Surcharge explicite
    tests_total += 1
    if test_explicit_environment_override():
        tests_passed += 1
    
    # Démonstration
    demonstrate_environment_switching()
    
    # Résumé
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ DES TESTS D'ENVIRONNEMENT")
    print("=" * 60)
    print(f"Tests passés: {tests_passed}/{tests_total}")
    print(f"Taux de réussite: {(tests_passed/tests_total*100):.1f}%")
    
    if tests_passed == tests_total:
        print("\n🎉 SYSTÈME DE GESTION D'ENVIRONNEMENT OPÉRATIONNEL !")
        print("✅ Configuration centralisée fonctionnelle")
        print("✅ Détection automatique d'environnement")
        print("✅ Possibilité de surcharge pour les tests")
    else:
        print(f"\n⚠️ {tests_total - tests_passed} test(s) ont échoué")
    
    return tests_passed == tests_total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)