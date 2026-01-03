#!/usr/bin/env python3
"""
Script pour examiner le JSON brut de l'API Tradier de production
et comprendre la structure des données Greeks et IV
"""

# Chargement des variables d'environnement
from dotenv import load_dotenv
load_dotenv()

import requests
import json
from utils.config import Config

def test_raw_api():
    """Test direct de l'API Tradier sans parsing"""
    
    print("🔍 Examen du JSON brut de l'API Tradier production")
    print("=" * 60)
    
    # Configuration
    api_key = Config.get_tradier_api_key()
    base_url = Config.get_tradier_base_url()
    
    print(f"🌐 Environnement: {Config.get_tradier_environment()}")
    print(f"🔗 URL: {base_url}")
    print(f"🔑 Clé: {api_key[:10]}...")
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Accept': 'application/json'
    }
    
    # Test avec AAPL
    symbol = "AAPL"
    
    print(f"\n📊 Test avec {symbol}")
    print("-" * 40)
    
    # 1. Récupération des expirations
    print("\n1️⃣ EXPIRATIONS:")
    exp_url = f"{base_url}/markets/options/expirations"
    exp_params = {'symbol': symbol}
    
    try:
        exp_response = requests.get(exp_url, headers=headers, params=exp_params)
        exp_response.raise_for_status()
        exp_data = exp_response.json()
        
        print(f"Status: {exp_response.status_code}")
        print("Raw JSON:")
        print(json.dumps(exp_data, indent=2))
        
        # Extraire la première expiration
        expirations = []
        if 'expirations' in exp_data and exp_data['expirations'] and 'date' in exp_data['expirations']:
            dates = exp_data['expirations']['date']
            if isinstance(dates, str):
                dates = [dates]
            expirations = dates
        
        if not expirations:
            print("❌ Aucune expiration trouvée")
            return
            
        expiration = expirations[0]
        print(f"\n✅ Utilisation de l'expiration: {expiration}")
        
    except Exception as e:
        print(f"❌ Erreur récupération expirations: {e}")
        return
    
    # 2. Récupération de la chaîne d'options avec Greeks
    print(f"\n2️⃣ CHAÎNE D'OPTIONS AVEC GREEKS ({expiration}):")
    chain_url = f"{base_url}/markets/options/chains"
    chain_params = {
        'symbol': symbol,
        'expiration': expiration,
        'greeks': 'true'  # IMPORTANT: demander les Greeks
    }
    
    try:
        chain_response = requests.get(chain_url, headers=headers, params=chain_params)
        chain_response.raise_for_status()
        chain_data = chain_response.json()
        
        print(f"Status: {chain_response.status_code}")
        print("Structure générale:")
        print(f"Keys: {list(chain_data.keys())}")
        
        if 'options' in chain_data and chain_data['options'] and 'option' in chain_data['options']:
            options_list = chain_data['options']['option']
            if not isinstance(options_list, list):
                options_list = [options_list]
            
            print(f"\nNombre d'options: {len(options_list)}")
            
            # Examiner les 3 premiers contrats en détail
            print("\n🔬 EXAMEN DÉTAILLÉ DES 3 PREMIERS CONTRATS:")
            for i, option in enumerate(options_list[:3]):
                print(f"\n--- CONTRAT {i+1} ---")
                print(f"Symbole: {option.get('symbol', 'N/A')}")
                print(f"Description: {option.get('description', 'N/A')}")
                print(f"Strike: {option.get('strike', 'N/A')}")
                print(f"Type: {option.get('option_type', 'N/A')}")
                print(f"Bid: {option.get('bid', 'N/A')}")
                print(f"Ask: {option.get('ask', 'N/A')}")
                print(f"Last: {option.get('last', 'N/A')}")
                print(f"Volume: {option.get('volume', 'N/A')}")
                print(f"Open Interest: {option.get('open_interest', 'N/A')}")
                
                # FOCUS: Examiner l'objet greeks
                print("\n🧮 GREEKS:")
                if 'greeks' in option:
                    greeks = option['greeks']
                    print(f"Type de l'objet greeks: {type(greeks)}")
                    print("Contenu complet des greeks:")
                    print(json.dumps(greeks, indent=4))
                    
                    if isinstance(greeks, dict):
                        print("\nGreeks individuels:")
                        for key, value in greeks.items():
                            print(f"  {key}: {value} (type: {type(value)})")
                else:
                    print("❌ Pas d'objet 'greeks' trouvé")
                
                print("\n" + "="*50)
            
            # Chercher des contrats ATM
            underlying_response = requests.get(f"{base_url}/markets/quotes", 
                                             headers=headers, 
                                             params={'symbols': symbol})
            if underlying_response.status_code == 200:
                underlying_data = underlying_response.json()
                if 'quotes' in underlying_data and 'quote' in underlying_data['quotes']:
                    price = underlying_data['quotes']['quote']['last']
                    print(f"\n💰 Prix du sous-jacent: ${price}")
                    
                    # Trouver des contrats ATM
                    print(f"\n🎯 CONTRATS ATM (proche de ${price}):")
                    atm_contracts = []
                    for option in options_list:
                        strike = option.get('strike', 0)
                        if strike and abs(float(strike) - float(price)) <= float(price) * 0.02:  # ±2%
                            atm_contracts.append(option)
                    
                    for contract in atm_contracts[:5]:  # Top 5
                        print(f"\n{contract.get('description', 'N/A')}")
                        if 'greeks' in contract and contract['greeks']:
                            greeks = contract['greeks']
                            print(f"  Delta: {greeks.get('delta', 'N/A')}")
                            print(f"  Gamma: {greeks.get('gamma', 'N/A')}")
                            print(f"  Theta: {greeks.get('theta', 'N/A')}")
                            print(f"  Vega: {greeks.get('vega', 'N/A')}")
                            print(f"  Rho: {greeks.get('rho', 'N/A')}")
                            print(f"  Bid IV: {greeks.get('bid_iv', 'N/A')}")
                            print(f"  Mid IV: {greeks.get('mid_iv', 'N/A')}")
                            print(f"  Ask IV: {greeks.get('ask_iv', 'N/A')}")
        else:
            print("❌ Structure d'options inattendue")
            print("Raw JSON complet:")
            print(json.dumps(chain_data, indent=2))
        
    except Exception as e:
        print(f"❌ Erreur récupération chaîne: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_raw_api()