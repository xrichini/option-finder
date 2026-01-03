#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.getcwd())

from utils.config import Config
import requests

def main():
    print('🔗 Test endpoint options chains sandbox...')
    
    api_key = Config.get_tradier_api_key()
    base_url = Config.get_tradier_base_url()
    
    headers = {
        'Authorization': f'Bearer {api_key}', 
        'Accept': 'application/json'
    }
    
    # Test avec SPY (très populaire)
    symbol = 'SPY'
    
    # 1. Test sans paramètres spécifiques
    print(f'\n📊 Test 1: Chains sans paramètres ({symbol})')
    url = f'{base_url}/markets/options/chains'
    params = {'symbol': symbol}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        print(f'Status: {response.status_code}')
        if response.status_code == 200:
            data = response.json()
            print(f'✅ Succès! Preview: {str(data)[:150]}...')
        else:
            print(f'❌ Erreur {response.status_code}')
            print(f'Response: {response.text[:300]}')
    except Exception as e:
        print(f'❌ Exception: {e}')
    
    # 2. Test avec expiration spécifique
    print('\n📅 Test 2: Avec expiration spécifique')
    
    # Récupérer d'abord les expirations disponibles
    exp_url = f'{base_url}/markets/options/expirations'
    exp_params = {'symbol': symbol}
    
    try:
        exp_response = requests.get(exp_url, headers=headers, params=exp_params)
        if exp_response.status_code == 200:
            exp_data = exp_response.json()
            expirations = exp_data.get('expirations', {}).get('date', [])
            if expirations:
                # Prendre la première expiration
                expiration = expirations[0]
                print(f'Expiration choisie: {expiration}')
                
                # Test avec expiration
                params_with_exp = {
                    'symbol': symbol,
                    'expiration': expiration
                }
                
                response = requests.get(url, headers=headers, params=params_with_exp)
                print(f'Status: {response.status_code}')
                if response.status_code == 200:
                    data = response.json()
                    print('✅ Succès avec expiration!')
                    
                    # Analyser la structure des données
                    if 'options' in data:
                        options = data['options']
                        if 'option' in options:
                            option_list = options['option']
                            if isinstance(option_list, list):
                                print(f'📊 Trouvé {len(option_list)} contrats')
                                # Montrer quelques exemples
                                for i, opt in enumerate(option_list[:3]):
                                    print(f'  Exemple {i+1}: {opt.get("symbol", "N/A")} - Strike: {opt.get("strike", "N/A")} - Volume: {opt.get("volume", "N/A")}')
                            else:
                                print(f'📊 Trouvé 1 contrat: {option_list.get("symbol", "N/A")}')
                        else:
                            print(f'❌ Structure inattendue: {list(options.keys())}')
                    else:
                        print(f'❌ Pas de clé "options": {list(data.keys())}')
                        
                else:
                    print(f'❌ Erreur {response.status_code}')
                    print(f'Response: {response.text[:300]}')
            else:
                print('❌ Aucune expiration trouvée')
    except Exception as e:
        print(f'❌ Exception: {e}')
    
    # 3. Test avec d'autres symboles
    print('\n🔄 Test 3: Autres symboles populaires')
    test_symbols = ['AAPL', 'TSLA', 'QQQ']
    
    for test_symbol in test_symbols:
        print(f'  Test {test_symbol}...')
        params = {'symbol': test_symbol}
        
        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                print(f'    ✅ {test_symbol}: OK')
            else:
                print(f'    ❌ {test_symbol}: {response.status_code}')
        except Exception as e:
            print(f'    ❌ {test_symbol}: Exception {e}')

if __name__ == "__main__":
    main()