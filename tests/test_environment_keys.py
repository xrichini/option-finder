#!/usr/bin/env python3
"""
Test de gestion des environnements avec clés API distinctes
Démontre l'utilisation correcte de sandbox.tradier.com vs api.tradier.com
"""

import os
import sys

# Ajout des répertoires au path
sys.path.append(os.path.join(os.path.dirname(__file__), 'data'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))

def test_config_key_selection():
    """Test de sélection automatique des clés selon l'environnement"""
    print("🔑 Test de sélection des clés API...")
    
    try:
        from config import Config
        
        # Configuration actuelle
        print("  📋 Configuration actuelle:")
        print(f"    🌍 Environnement: {Config.get_tradier_environment()}")
        print(f"    🔗 URL: {Config.get_tradier_base_url()}")
        print(f"    🔑 Clé production: {'✅' if Config.TRADIER_API_KEY_PRODUCTION else '❌'}")
        print(f"    🔑 Clé sandbox: {'✅' if Config.TRADIER_API_KEY_SANDBOX else '❌'}")
        
        # Clé sélectionnée
        selected_key = Config.get_tradier_api_key()
        if selected_key:
            # Masque les caractères sauf les 4 derniers pour sécurité
            masked_key = f"***...{selected_key[-4:]}" if len(selected_key) >= 4 else "***"
            print(f"    🎯 Clé sélectionnée: {masked_key}")
        else:
            print(f"    ❌ Aucune clé disponible pour l'environnement {Config.get_tradier_environment()}")
        
        return bool(selected_key)
        
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return False

def test_environment_endpoints():
    """Test des endpoints selon l'environnement"""
    print("\n🌐 Test des endpoints par environnement...")
    
    try:
        from config import Config
        
        current_env = Config.get_tradier_environment()
        current_url = Config.get_tradier_base_url()
        
        print(f"  📡 Environnement actuel: {current_env}")
        print(f"  🔗 URL actuelle: {current_url}")
        
        # Vérification de l'URL correcte
        if current_env == "sandbox":
            expected_url = "https://sandbox.tradier.com/v1"
        else:
            expected_url = "https://api.tradier.com/v1"
        
        if current_url == expected_url:
            print(f"  ✅ URL correcte pour l'environnement {current_env}")
        else:
            print(f"  ❌ URL incorrecte. Attendue: {expected_url}, Actuelle: {current_url}")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return False

def test_client_with_environment():
    """Test du client avec l'environnement configuré"""
    print("\n🔗 Test du client Tradier...")
    
    try:
        from tradier_client import TradierClient
        
        client = TradierClient()
        
        print(f"  🎯 Client initialisé en mode: {client.environment}")
        print(f"  🔗 URL utilisée: {client.base_url}")
        
        # Test simple si nous avons une clé
        if client.api_key and client.api_key != "VOTRE_CLE_SANDBOX_ICI":
            print("  📅 Test récupération expirations AAPL...")
            expirations = client.get_option_expirations("AAPL")
            
            if expirations:
                print(f"    ✅ {len(expirations)} expirations trouvées")
                print(f"    📋 Premières: {expirations[:3]}")
            else:
                if client.environment == "sandbox":
                    print("    ⚠️ Pas de données (normal pour sandbox sans données de test)")
                else:
                    print("    ❌ Pas de données en production (problème possible)")
        else:
            print("  ⚠️ Clé API manquante ou par défaut - sautez le test de données")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        import traceback
        print(f"  🔍 Détails: {traceback.format_exc()}")
        return False

def demonstrate_environment_switching():
    """Guide pour basculer d'environnement"""
    print("\n🔄 Guide de basculement d'environnement...")
    
    print("  💡 Pour utiliser l'environnement SANDBOX:")
    print("    1. Obtenez votre clé sandbox de https://sandbox.tradier.com")
    print("    2. Mettez-la dans secrets.toml: TRADIER_API_KEY_SANDBOX = \"votre_cle\"")
    print("    3. Changez: TRADIER_SANDBOX = true")
    print("    4. L'app utilisera automatiquement sandbox.tradier.com")
    
    print("\n  🚀 Pour utiliser l'environnement PRODUCTION:")
    print("    1. Votre clé production est déjà configurée")
    print("    2. Changez: TRADIER_SANDBOX = false")
    print("    3. L'app utilisera automatiquement api.tradier.com")
    
    print("\n  🛡️ Avantages de cette approche:")
    print("    ✅ Deux clés distinctes pour sécurité")
    print("    ✅ Endpoints corrects automatiquement")
    print("    ✅ Basculement simple par configuration")
    print("    ✅ Pas de risque de mélanger les environnements")
    
    return True

def show_current_configuration():
    """Affiche la configuration actuelle"""
    print("\n📋 Configuration actuelle détaillée...")
    
    try:
        from config import Config
        
        print("  🔧 Paramètres:")
        print(f"    TRADIER_SANDBOX = {Config.TRADIER_SANDBOX}")
        print(f"    Environment = {Config.get_tradier_environment()}")
        print(f"    Base URL = {Config.get_tradier_base_url()}")
        print(f"    Development Mode = {Config.is_development_mode()}")
        
        print("\n  🔑 Clés disponibles:")
        prod_key = Config.TRADIER_API_KEY_PRODUCTION
        sandbox_key = Config.TRADIER_API_KEY_SANDBOX
        
        print(f"    Production: {'✅ Configurée' if prod_key and prod_key != 'VOTRE_CLE_SANDBOX_ICI' else '❌ Manquante'}")
        print(f"    Sandbox: {'✅ Configurée' if sandbox_key and sandbox_key != 'VOTRE_CLE_SANDBOX_ICI' else '❌ Manquante/Par défaut'}")
        
        selected_key = Config.get_tradier_api_key()
        key_source = "sandbox" if Config.TRADIER_SANDBOX else "production"
        print(f"    Sélectionnée: {key_source} ({'✅' if selected_key else '❌'})")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return False

def main():
    """Test principal de gestion des environnements avec clés distinctes"""
    print("🧪 TESTS GESTION ENVIRONNEMENTS + CLÉS DISTINCTES")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 0
    
    # Configuration actuelle
    show_current_configuration()
    
    # Test 1: Sélection des clés
    tests_total += 1
    if test_config_key_selection():
        tests_passed += 1
    
    # Test 2: Endpoints
    tests_total += 1
    if test_environment_endpoints():
        tests_passed += 1
    
    # Test 3: Client avec environnement
    tests_total += 1
    if test_client_with_environment():
        tests_passed += 1
    
    # Guide d'utilisation
    demonstrate_environment_switching()
    
    # Résumé
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ DES TESTS")
    print("=" * 60)
    print(f"Tests passés: {tests_passed}/{tests_total}")
    print(f"Taux de réussite: {(tests_passed/tests_total*100):.1f}%")
    
    if tests_passed == tests_total:
        print("\n🎉 SYSTÈME DE GESTION MULTI-ENVIRONNEMENT OPÉRATIONNEL !")
        print("✅ Configuration des clés distinctes")
        print("✅ Endpoints automatiques (sandbox.tradier.com / api.tradier.com)")
        print("✅ Basculement par simple configuration")
    else:
        print(f"\n⚠️ {tests_total - tests_passed} test(s) ont échoué")
    
    # Conseil final
    print("\n💡 Action requise:")
    print("   Remplacez 'VOTRE_CLE_SANDBOX_ICI' par votre vraie clé sandbox")
    print("   dans .streamlit/secrets.toml")
    
    return tests_passed == tests_total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)