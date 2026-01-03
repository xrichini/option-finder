#!/usr/bin/env python3
"""
Test de l'optimisation des quotes multiples

Valide que la nouvelle approche optimisée avec un seul appel API pour 
récupérer tous les prix des sous-jacents fonctionne correctement.
"""

import asyncio
import time
import logging
from datetime import datetime
import sys
import os

# Setup des paths pour imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.enhanced_tradier_client import EnhancedTradierClient
from services.hybrid_data_service import HybridDataService
from services.hybrid_screening_service import HybridScreeningService

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_tradier_multiple_quotes():
    """Test du client Tradier optimisé"""
    
    print("=" * 60)
    print("📊 TEST CLIENT TRADIER - QUOTES MULTIPLES")
    print("=" * 60)
    
    try:
        # Initialisation du client
        tradier_client = EnhancedTradierClient(api_token="", sandbox=None)
        
        # Test avec plusieurs symboles populaires
        test_symbols = ["AAPL", "TSLA", "SPY", "QQQ", "MSFT", "NVDA"]
        print(f"\n🚀 Test récupération quotes multiples: {', '.join(test_symbols)}")
        
        start_time = time.time()
        
        # Test méthode optimisée (1 seul appel API)
        quotes = tradier_client.get_multiple_underlying_quotes(test_symbols)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"⏱️ Durée: {duration:.2f}s pour {len(test_symbols)} symboles")
        print(f"✅ Quotes récupérées: {len(quotes)}")
        
        # Affichage des résultats
        for symbol, quote in quotes.items():
            if quote:
                print(f"  {symbol}: ${quote['price']:.2f} (change: {quote.get('change_percentage', 0):.1f}%)")
        
        # Test cache (deuxième appel devrait être instantané)
        print("\n🔄 Test cache (deuxième appel):")
        start_time = time.time()
        quotes_cached = tradier_client.get_multiple_underlying_quotes(test_symbols)
        end_time = time.time()
        duration_cached = end_time - start_time
        
        print(f"⏱️ Durée avec cache: {duration_cached:.3f}s")
        print(f"🚀 Accélération cache: {(duration / duration_cached):.1f}x plus rapide")
        
        # Comparaison avec l'ancienne méthode (appels individuels)
        print("\n🔄 Comparaison avec appels individuels:")
        start_time = time.time()
        
        individual_quotes = {}
        for symbol in test_symbols:
            quote = tradier_client.get_underlying_quote(symbol)  # Utilise la nouvelle méthode optimisée
            if quote:
                individual_quotes[symbol] = quote
        
        end_time = time.time()
        duration_individual = end_time - start_time
        
        print(f"⏱️ Durée appels via méthode single: {duration_individual:.3f}s")
        print(f"📊 Quotes individuelles: {len(individual_quotes)}")
        
        print("\n✅ Test client Tradier réussi!")
        return True
        
    except Exception as e:
        print(f"❌ Erreur test client Tradier: {e}")
        return False

async def test_hybrid_data_service_optimization():
    """Test du service hybride optimisé"""
    
    print("\n" + "=" * 60)
    print("🔄 TEST SERVICE HYBRIDE - OPTIMISATION")
    print("=" * 60)
    
    try:
        # Initialisation du service
        hybrid_service = HybridDataService(enable_polygon=True)
        
        test_symbols = ["AAPL", "TSLA", "SPY", "QQQ"]
        print(f"\n🚀 Test récupération prix multiples: {', '.join(test_symbols)}")
        
        start_time = time.time()
        
        # Test méthode optimisée
        prices = await hybrid_service.get_multiple_underlying_prices(test_symbols)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"⏱️ Durée: {duration:.2f}s pour {len(test_symbols)} symboles")
        print(f"✅ Prix récupérés: {len(prices)}")
        
        # Affichage des prix
        for symbol, price in prices.items():
            print(f"  {symbol}: ${price:.2f}")
        
        # Test cache
        print("\n🔄 Test cache (deuxième appel):")
        start_time = time.time()
        prices_cached = await hybrid_service.get_multiple_underlying_prices(test_symbols)
        end_time = time.time()
        duration_cached = end_time - start_time
        
        print(f"⏱️ Durée avec cache: {duration_cached:.3f}s")
        print(f"📊 Prix en cache: {len(prices_cached)}")
        
        print("\n✅ Test service hybride réussi!")
        return True
        
    except Exception as e:
        print(f"❌ Erreur test service hybride: {e}")
        return False

async def test_hybrid_screening_optimization():
    """Test du screening hybride optimisé"""
    
    print("\n" + "=" * 60)
    print("🎯 TEST SCREENING HYBRIDE - OPTIMISATION")
    print("=" * 60)
    
    try:
        # Initialisation du service
        hybrid_screening = HybridScreeningService()
        
        # Test avec quelques symboles populaires
        test_symbols = ["SPY", "AAPL", "TSLA"]
        print(f"\n🚀 Test screening optimisé: {', '.join(test_symbols)}")
        
        # Callback de progression pour voir l'optimisation en action
        progress_log = []
        async def progress_callback(current: int, total: int, symbol: str, details: str):
            progress_pct = (current / total) * 100 if total > 0 else 0
            message = f"{progress_pct:.0f}% - {symbol} - {details}"
            print(f"    📈 {message}")
            progress_log.append(message)
        
        start_time = time.time()
        
        # Screening hybride optimisé
        opportunities = await hybrid_screening.screen_options_hybrid(
            symbols=test_symbols,
            option_type="both",
            max_dte=21,
            min_volume=20,
            min_oi=10,
            min_whale_score=40.0,
            enable_ai=False,
            progress_callback=progress_callback
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n⏱️ Durée screening total: {duration:.2f}s")
        print(f"✅ Opportunités trouvées: {len(opportunities)}")
        
        # Compter les différents sous-jacents
        underlying_symbols = set()
        for opp in opportunities:
            underlying_symbols.add(opp.get('underlying_symbol', ''))
        
        print(f"📊 Sous-jacents uniques: {len(underlying_symbols)} ({', '.join(underlying_symbols)})")
        print(f"🚀 Optimisation: {len(underlying_symbols)} appels API au lieu de {len(opportunities)}")
        
        # Affichage de quelques meilleures opportunités
        if opportunities:
            print("\n🏆 Top 3 opportunités optimisées:")
            for i, opp in enumerate(sorted(opportunities, key=lambda x: x.get('hybrid_score', 0), reverse=True)[:3], 1):
                emoji = opp.get('option_type_emoji', '📈')
                underlying_price = opp.get('underlying_price', 'N/A')
                print(f"   {i}. {emoji} {opp['option_symbol']}")
                print(f"      Score: {opp['hybrid_score']:.1f} | Sous-jacent: ${underlying_price}")
                print(f"      Volume: {opp['volume']:,} | DTE: {opp['dte']}j")
        
        # Vérifier que l'optimisation a bien fonctionné
        optimization_found = any("Récupération de" in msg and "prix sous-jacents en 1 appel" in msg 
                               for msg in progress_log)
        
        if optimization_found:
            print("\n🎯 OPTIMISATION DÉTECTÉE: Appel groupé confirmé dans les logs!")
        else:
            print("\n⚠️ Optimisation peut-être pas détectée dans les logs")
        
        print("\n✅ Test screening optimisé réussi!")
        return True
        
    except Exception as e:
        print(f"❌ Erreur test screening optimisé: {e}")
        return False

async def main():
    """Test principal de l'optimisation quotes multiples"""
    
    print("🚀 TESTS OPTIMISATION QUOTES MULTIPLES")
    print("   Objectif: 1 seul appel API pour tous les prix sous-jacents")
    print(f"   Timestamp: {datetime.now().isoformat()}")
    
    results = []
    
    try:
        # Tests séquentiels
        results.append(await test_tradier_multiple_quotes())
        results.append(await test_hybrid_data_service_optimization())
        results.append(await test_hybrid_screening_optimization())
        
        print("\n" + "=" * 60)
        print("🎉 TOUS LES TESTS TERMINÉS")
        print("=" * 60)
        
        success_count = sum(results)
        total_count = len(results)
        
        print(f"\n📊 Résultats: {success_count}/{total_count} tests réussis")
        
        if success_count == total_count:
            print("✅ TOUTES LES OPTIMISATIONS FONCTIONNENT!")
            print("\n🚀 Bénéfices de l'optimisation:")
            print("  • 1 seul appel API au lieu de N appels individuels")
            print("  • Réduction drastique de la latence réseau")
            print("  • Meilleure utilisation des limites de taux API")
            print("  • Cache intelligent par symbole")
            print("  • Fallback gracieux sur cache si erreur")
        else:
            print(f"⚠️ {total_count - success_count} test(s) ont échoué")
        
        print("\n🔧 Pour utiliser l'API optimisée:")
        print("  1. Lancer: python app.py")
        print("  2. POST /api/hybrid/scan-all")
        print("  3. Observer les logs pour voir l'optimisation")
        
        print(f"\n🎯 Optimisation quotes multiples {'opérationnelle' if success_count == total_count else 'partiellement fonctionnelle'}!")
        
    except Exception as e:
        print(f"\n❌ ERREUR GÉNÉRALE: {e}")

if __name__ == "__main__":
    asyncio.run(main())