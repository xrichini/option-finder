#!/usr/bin/env python3
"""
Test des endpoints FastAPI pour vérifier les données IV et Greeks
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"

def test_endpoint(endpoint, method="GET", data=None, params=None):
    """Helper pour tester un endpoint"""
    print(f"\n{'='*60}")
    print(f"🧪 TEST {method} {endpoint}")
    print(f"{'='*60}")
    
    try:
        url = f"{BASE_URL}{endpoint}"
        
        if method == "GET":
            response = requests.get(url, params=params)
        elif method == "POST":
            response = requests.post(url, json=data, params=params)
        else:
            print(f"❌ Méthode {method} non supportée")
            return None
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Succès - Taille réponse: {len(json.dumps(result))}")
            return result
        else:
            print(f"❌ Erreur: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return None

def test_data_sources():
    """Test de l'endpoint des sources de données"""
    return test_endpoint("/api/hybrid/data-sources")

def test_config():
    """Test de l'endpoint de configuration"""
    return test_endpoint("/api/config")

def test_screening_with_aapl():
    """Test du screening avec AAPL pour voir les données IV/Greeks"""
    params = {
        "option_type": "call",  # Focus sur les calls
        "max_dte": 30,          # 30 jours
        "min_volume": 1,        # Volume minimal très bas
        "min_oi": 1,            # OI minimal très bas 
        "min_whale_score": 1,   # Score minimal très bas
        "enable_ai": False
    }
    
    data = {
        "symbols": ["AAPL"]
    }
    
    result = test_endpoint("/api/hybrid/screen", method="POST", data=data, params=params)
    
    if result and 'opportunities' in result:
        opportunities = result['opportunities']
        print("\n📊 ANALYSE DES RÉSULTATS:")
        print(f"   Opportunités trouvées: {len(opportunities)}")
        
        if opportunities:
            print("\n🔍 DÉTAILS DES 3 PREMIERS CONTRATS:")
            
            for i, opp in enumerate(opportunities[:3]):
                print(f"\n   📝 CONTRAT #{i+1}:")
                print(f"      Symbole: {opp.get('symbol', 'N/A')}")
                print(f"      Strike: ${opp.get('strike', 'N/A')}")
                print(f"      Type: {opp.get('option_type', 'N/A')}")
                print(f"      Expiration: {opp.get('expiration', 'N/A')}")
                print(f"      Volume: {opp.get('volume', 'N/A')}")
                print(f"      Open Interest: {opp.get('open_interest', 'N/A')}")
                
                # POINT CLÉ: IV et Greeks !
                print(f"      💎 IV: {opp.get('implied_volatility', 'N/A')}")
                print(f"      🔬 Delta: {opp.get('delta', 'N/A')}")
                print(f"      🔬 Gamma: {opp.get('gamma', 'N/A')}")
                print(f"      🔬 Theta: {opp.get('theta', 'N/A')}")
                print(f"      🔬 Vega: {opp.get('vega', 'N/A')}")
                print(f"      🔬 Rho: {opp.get('rho', 'N/A')}")
                
                # Prix
                print(f"      💰 Prix: ${opp.get('last_price', 'N/A')}")
                print(f"      💰 Bid: ${opp.get('bid', 'N/A')}")
                print(f"      💰 Ask: ${opp.get('ask', 'N/A')}")
                
                # Score
                print(f"      🐋 Whale Score: {opp.get('whale_score', 'N/A')}")
        else:
            print("   ❌ Aucune opportunité trouvée - Paramètres peut-être trop restrictifs")
    
    return result

def test_screening_aggressive():
    """Test avec des paramètres très permissifs pour avoir plus de résultats"""
    print("\n🚀 TEST AGRESSIF - Paramètres très permissifs")
    
    params = {
        "option_type": "both",   # Calls et puts
        "max_dte": 60,           # Jusqu'à 60 jours
        "min_volume": 0,         # Pas de minimum de volume
        "min_oi": 0,             # Pas de minimum d'OI
        "min_whale_score": 0,    # Pas de minimum de score
        "enable_ai": False
    }
    
    data = {
        "symbols": ["AAPL", "MSFT"]  # Deux symboles liquides
    }
    
    result = test_endpoint("/api/hybrid/screen", method="POST", data=data, params=params)
    
    if result and 'opportunities' in result:
        opportunities = result['opportunities']
        print("\n📊 RÉSULTATS MODE AGRESSIF:")
        print(f"   Total opportunités: {len(opportunities)}")
        
        # Analyser les IV disponibles
        iv_contracts = [o for o in opportunities if o.get('implied_volatility', 0) > 0]
        print(f"   Contrats avec IV > 0: {len(iv_contracts)}")
        
        if iv_contracts:
            print("\n🎯 EXEMPLES AVEC IV VALIDE:")
            for i, opp in enumerate(iv_contracts[:5]):
                iv = opp.get('implied_volatility', 0)
                delta = opp.get('delta', 0)
                symbol = opp.get('symbol', 'N/A')
                strike = opp.get('strike', 'N/A')
                option_type = opp.get('option_type', 'N/A')
                
                print(f"   {i+1}. {symbol} {option_type.upper()} ${strike} - IV: {iv:.1f}% - Delta: {delta:.3f}")
        else:
            print("   ❌ Aucun contrat avec IV valide trouvé")
    
    return result

def main():
    print("🧪 TEST DES ENDPOINTS FASTAPI")
    print(f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 URL de base: {BASE_URL}")
    
    # Vérifier si le serveur est en cours d'exécution
    try:
        response = requests.get(f"{BASE_URL}/api/status", timeout=5)
        if response.status_code != 200:
            print("❌ Serveur FastAPI non disponible. Lancez d'abord:")
            print("   python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000")
            return
    except:
        print("❌ Serveur FastAPI non disponible. Lancez d'abord:")
        print("   python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000")
        return
    
    print("✅ Serveur FastAPI détecté")
    
    # Test 1: Sources de données
    print(f"\n{'🔹'*20} TEST 1: Sources de données {'🔹'*20}")
    data_sources = test_data_sources()
    
    # Test 2: Configuration
    print(f"\n{'🔹'*20} TEST 2: Configuration {'🔹'*20}")
    config = test_config()
    
    # Test 3: Screening avec AAPL (paramètres normaux)
    print(f"\n{'🔹'*20} TEST 3: Screening AAPL {'🔹'*20}")
    screening_result = test_screening_with_aapl()
    
    # Test 4: Screening agressif (paramètres permissifs)
    print(f"\n{'🔹'*20} TEST 4: Screening agressif {'🔹'*20}")
    aggressive_result = test_screening_aggressive()
    
    # Résumé
    print(f"\n{'='*80}")
    print("📋 RÉSUMÉ DES TESTS")
    print(f"{'='*80}")
    print(f"✅ Sources de données: {'OK' if data_sources else 'ERREUR'}")
    print(f"✅ Configuration: {'OK' if config else 'ERREUR'}")
    print(f"✅ Screening AAPL: {'OK' if screening_result else 'ERREUR'}")
    print(f"✅ Screening agressif: {'OK' if aggressive_result else 'ERREUR'}")
    
    if screening_result and aggressive_result:
        normal_count = len(screening_result.get('opportunities', []))
        aggressive_count = len(aggressive_result.get('opportunities', []))
        print("\n📊 Comparaison des résultats:")
        print(f"   Paramètres normaux: {normal_count} opportunités")
        print(f"   Paramètres agressifs: {aggressive_count} opportunités")
        
        # Vérifier les IV
        if aggressive_result.get('opportunities'):
            iv_count = len([o for o in aggressive_result['opportunities'] if o.get('implied_volatility', 0) > 0])
            print(f"   Contrats avec IV valide: {iv_count}/{aggressive_count}")
            
            if iv_count > 0:
                print("✅ Les données IV remontent bien depuis l'API !")
            else:
                print("❌ Aucune donnée IV détectée - problème dans la chaîne de traitement")

if __name__ == "__main__":
    main()