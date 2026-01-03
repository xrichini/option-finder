#!/usr/bin/env python3
"""
Test unitaire direct de l'API Tradier pour diagnostiquer les Greeks et IV
"""

import os
import sys
import json
import logging
from datetime import datetime

# Ajouter le répertoire racine au path pour importer les modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.enhanced_tradier_client import EnhancedTradierClient

# Configuration des logs pour voir tout
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_tradier_options_chain():
    """Test direct de l'API Tradier get_options_chains avec diagnostics complets"""
    
    print("=" * 80)
    print("🧪 TEST UNITAIRE: API Tradier Options Chain")
    print("=" * 80)
    
    try:
        # Configuration automatique depuis Config
        print("📋 Configuration du client Tradier...")
        client = EnhancedTradierClient(api_token="", sandbox=None)  # Auto-configuré
        
        print(f"   Environment: {'Sandbox' if client.sandbox else 'Production'}")
        print(f"   Base URL: {client.base_url}")
        print(f"   API Token: {client.api_token[:10]}..." if client.api_token else "   ❌ Pas de token")
        
        # Test avec un symbole simple et liquide
        test_symbol = "AAPL"
        print(f"\n🔍 Test avec le symbole: {test_symbol}")
        
        # 1. Récupérer les expirations disponibles
        print("\n📅 ÉTAPE 1: Récupération des expirations...")
        expirations = client.get_options_expirations(test_symbol)
        print(f"   Expirations trouvées: {len(expirations)}")
        for i, exp in enumerate(expirations[:5]):  # Afficher les 5 premières
            print(f"   [{i}] {exp}")
        
        if not expirations:
            print("❌ Aucune expiration trouvée - Arrêt du test")
            return False
        
        # 2. Utiliser la première expiration
        target_expiration = expirations[0]
        print(f"\n🎯 ÉTAPE 2: Test avec l'expiration {target_expiration}")
        
        # 3. Récupérer la chaîne d'options avec Greeks
        print("\n⛓️ ÉTAPE 3: Récupération de la chaîne d'options...")
        contracts = client.get_options_chains(test_symbol, target_expiration)
        
        print(f"   Contrats récupérés: {len(contracts)}")
        
        if not contracts:
            print("❌ Aucun contrat trouvé - Arrêt du test")
            return False
        
        # 4. Analyse détaillée de quelques contrats
        print("\n🔬 ÉTAPE 4: Analyse détaillée des contrats")
        
        # Trier par strike et prendre les premiers
        contracts.sort(key=lambda x: x.strike)
        sample_contracts = contracts[:3]  # 3 premiers contrats
        
        for i, contract in enumerate(sample_contracts):
            print(f"\n   📊 CONTRAT #{i+1}: {contract.symbol}")
            print(f"      Type: {contract.option_type.upper()}")
            print(f"      Strike: ${contract.strike}")
            print(f"      Expiration: {contract.expiration}")
            print(f"      Bid/Ask: ${contract.bid}/${contract.ask}")
            print(f"      Last: ${contract.last}")
            print(f"      Volume: {contract.volume:,}")
            print(f"      OI: {contract.open_interest:,}")
            
            # 🔍 FOCUS SUR LES GREEKS ET IV
            print("      *** GREEKS ***")
            print(f"      Delta: {contract.delta}")
            print(f"      Gamma: {contract.gamma}")
            print(f"      Theta: {contract.theta}")
            print(f"      Vega: {contract.vega}")
            print(f"      Rho: {contract.rho}")
            print("      *** IMPLIED VOLATILITY ***")
            print(f"      IV: {contract.implied_volatility}")
            
            # Conversion en dict pour voir la structure complète
            contract_dict = contract.to_dict()
            
            # Vérifier si les Greeks sont présents et non-null
            greeks_present = any([
                contract.delta != 0,
                contract.gamma != 0,
                contract.theta != 0,
                contract.vega != 0,
                contract.rho != 0,
                contract.implied_volatility != 0.25  # 0.25 = fallback
            ])
            
            print("      *** STATUS ***")
            print(f"      Greeks présents: {'✅ OUI' if greeks_present else '❌ NON'}")
            print(f"      IV valide: {'✅ OUI' if contract.implied_volatility != 0.25 else '❌ NON (fallback)'}")
        
        # 5. Test de requête brute à l'API
        print("\n🌐 ÉTAPE 5: Test de requête brute à l'API Tradier")
        test_raw_api_call(client, test_symbol, target_expiration)
        
        # 6. Résumé statistique
        print("\n📈 RÉSUMÉ STATISTIQUE:")
        
        contracts_with_greeks = [c for c in contracts if any([c.delta != 0, c.gamma != 0, c.theta != 0, c.vega != 0, c.rho != 0])]
        contracts_with_iv = [c for c in contracts if c.implied_volatility != 0.25]
        
        print(f"   Total contrats: {len(contracts)}")
        print(f"   Contrats avec Greeks: {len(contracts_with_greeks)} ({len(contracts_with_greeks)/len(contracts)*100:.1f}%)")
        print(f"   Contrats avec IV valide: {len(contracts_with_iv)} ({len(contracts_with_iv)/len(contracts)*100:.1f}%)")
        
        # 7. Recommandations
        if len(contracts_with_greeks) == 0:
            print("\n⚠️ PROBLÈME DÉTECTÉ: Aucun Greek trouvé")
            print("   Causes possibles:")
            print("   - Mode Sandbox sans données Greeks complètes")
            print("   - Paramètre 'greeks=true' non pris en compte")
            print("   - Contrats trop peu liquides")
            print("   - Problème de parsing des réponses API")
        
        if len(contracts_with_iv) == 0:
            print("\n⚠️ PROBLÈME DÉTECTÉ: Aucune IV valide trouvée")
            print("   Toutes les IV sont à 0.25 (valeur de fallback)")
        
        print("\n✅ Test terminé!")
        return True
        
    except Exception as e:
        print(f"❌ ERREUR DURANT LE TEST: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_raw_api_call(client, symbol, expiration):
    """Test d'appel brut à l'API pour voir la réponse JSON complète"""
    
    try:
        print(f"      Appel brut: GET {client.base_url}/markets/options/chains")
        print(f"      Params: symbol={symbol}, expiration={expiration}, greeks=true")
        
        # Faire l'appel direct
        url = f"{client.base_url}/markets/options/chains"
        params = {
            'symbol': symbol,
            'expiration': expiration,
            'greeks': 'true'
        }
        
        response = client.session.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        print(f"      Status: {response.status_code}")
        print("      Réponse JSON (extraits):")
        
        # Afficher la structure de la réponse
        if 'options' in data and data['options'] and 'option' in data['options']:
            options_list = data['options']['option']
            if isinstance(options_list, list) and len(options_list) > 0:
                first_option = options_list[0]
                print(f"      Premier contrat: {json.dumps(first_option, indent=8)}")
                
                # Vérifier spécifiquement les Greeks
                if 'greeks' in first_option:
                    print(f"      ✅ Objet 'greeks' présent: {first_option['greeks']}")
                else:
                    print("      ❌ Pas d'objet 'greeks' dans la réponse")
            else:
                print("      ❌ Format de réponse inattendu")
        else:
            print("      ❌ Structure 'options.option' non trouvée")
            print(f"      Clés disponibles: {list(data.keys())}")
    
    except Exception as e:
        print(f"      ❌ Erreur appel brut: {e}")

if __name__ == "__main__":
    print(f"Démarrage du test à {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    success = test_tradier_options_chain()
    if success:
        print("🎉 Test réussi!")
    else:
        print("💥 Test échoué!")