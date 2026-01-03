#!/usr/bin/env python3
"""
Test du scan-all endpoint hybride pour vérifier les opportunités Call/Put
"""

import requests
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"

def test_scan_all():
    """Test du scan-all complet avec paramètres optimisés"""
    print("🔍 TEST SCAN-ALL HYBRIDE")
    print(f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 URL: {BASE_URL}/api/hybrid/scan-all")
    
    # Test avec des paramètres très permissifs
    data = {
        "symbols": ["AAPL", "TSLA", "SPY", "QQQ", "NVDA"],
        "max_dte": 60,
        "min_volume": 0,     # Aucun minimum
        "min_oi": 0,         # Aucun minimum
        "min_whale_score": 0 # Aucun minimum
    }
    
    print("📋 Paramètres:")
    print(f"   Symboles: {data['symbols']}")
    print(f"   Max DTE: {data['max_dte']}")
    print(f"   Min Volume: {data['min_volume']}")
    print(f"   Min OI: {data['min_oi']}")
    print(f"   Min Whale Score: {data['min_whale_score']}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/hybrid/scan-all", 
            json=data, 
            timeout=30
        )
        
        print("\n📊 RÉSULTAT:")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            # Accès aux données selon le format de l'endpoint
            opportunities = result.get('opportunities', [])
            total_count = result.get('total_count', 0)
            
            print("✅ Succès!")
            print(f"Total opportunités: {total_count}")
            
            if opportunities:
                # Analyser les types d'options
                calls = [o for o in opportunities if o.get('option_type') == 'CALL']
                puts = [o for o in opportunities if o.get('option_type') == 'PUT']
                
                print(f"📈 CALLS: {len(calls)}")
                print(f"📉 PUTS: {len(puts)}")
                
                # Afficher quelques exemples
                print("\n🎯 TOP 5 OPPORTUNITÉS:")
                for i, opp in enumerate(opportunities[:5]):
                    symbol = opp.get('underlying_symbol', 'N/A')
                    option_type = opp.get('option_type', 'N/A')
                    strike = opp.get('strike', 'N/A')
                    expiration = opp.get('expiration', 'N/A')
                    volume = opp.get('volume', 0)
                    oi = opp.get('open_interest', 0)
                    hybrid_score = opp.get('hybrid_score', 0)
                    
                    print(f"   {i+1}. {symbol} {option_type} ${strike} exp:{expiration}")
                    print(f"      Vol: {volume}, OI: {oi}, Score: {hybrid_score:.1f}")
                
                # Statistiques détaillées si disponibles
                detailed_results = result.get('detailed_results', {})
                if detailed_results:
                    stats = detailed_results.get('statistics', {})
                    print("\n📊 STATISTIQUES:")
                    
                    call_stats = stats.get('calls', {})
                    put_stats = stats.get('puts', {})
                    
                    print(f"   Calls - Compte: {call_stats.get('count', 0)}, Score moyen: {call_stats.get('avg_hybrid_score', 0):.1f}")
                    print(f"   Puts - Compte: {put_stats.get('count', 0)}, Score moyen: {put_stats.get('avg_hybrid_score', 0):.1f}")
                    
                    # Meilleure opportunité
                    best = stats.get('best_overall')
                    if best:
                        print(f"   🏆 Meilleure: {best.get('underlying_symbol')} {best.get('option_type')} (Score: {best.get('hybrid_score', 0):.1f})")
                
            else:
                print("❌ Aucune opportunité trouvée")
                
                # Diagnostic des paramètres
                screening_params = result.get('screening_params', {})
                print("\n🔍 DIAGNOSTIC:")
                print(f"   Symboles traités: {screening_params.get('symbols_count', 'N/A')}")
                print(f"   Option type: {screening_params.get('option_type', 'N/A')}")
                
                data_sources = result.get('data_sources', {})
                print("   Sources actives:")
                for source, active in data_sources.items():
                    print(f"     - {source}: {'✅' if active else '❌'}")
        
        else:
            print(f"❌ Erreur HTTP {response.status_code}")
            print(f"Réponse: {response.text}")
    
    except Exception as e:
        print(f"❌ Exception: {e}")

def test_simple_scan():
    """Test simple avec un seul symbole"""
    print("\n" + "="*60)
    print("🔍 TEST SIMPLE - Un seul symbole")
    
    data = {
        "symbols": ["SPY"],  # ETF très liquide
        "max_dte": 21,
        "min_volume": 10,
        "min_oi": 10, 
        "min_whale_score": 10
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/hybrid/scan-all", 
            json=data, 
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            opportunities = result.get('opportunities', [])
            
            print(f"✅ Opportunités SPY: {len(opportunities)}")
            
            if opportunities:
                print("🎯 Exemples SPY:")
                for i, opp in enumerate(opportunities[:3]):
                    print(f"   {i+1}. {opp.get('option_type')} ${opp.get('strike')} - Score: {opp.get('hybrid_score', 0):.1f}")
        else:
            print(f"❌ Erreur: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    # Vérifier serveur
    try:
        response = requests.get(f"{BASE_URL}/api/status", timeout=5)
        if response.status_code != 200:
            print("❌ Serveur FastAPI non disponible")
            exit(1)
    except:
        print("❌ Serveur FastAPI non disponible")
        exit(1)
    
    print("✅ Serveur détecté")
    
    # Tests
    test_scan_all()
    test_simple_scan()
    
    print("\n" + "="*60)
    print("✅ Tests terminés")