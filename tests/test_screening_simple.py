#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.getcwd())

from data.screener_logic import OptionsScreener
from utils.config import Config

def main():
    print("🧪 TEST SCREENING AVEC PARAMÈTRES SANDBOX")
    print("=" * 60)
    
    # Configuration
    params = Config.get_screening_parameters()
    print("\n🔧 Paramètres actifs:")
    for key, value in params.items():
        print(f"    {key}: {value}")
    
    # Test simple screening
    screener = OptionsScreener(use_async=False, enable_historical=False)
    
    # Test avec SPY uniquement (plus rapide)
    test_symbols = ['SPY']
    print(f"\n🎯 Test screening sur {test_symbols}")
    
    # Screening calls
    print("\n📈 Screening CALLS...")
    try:
        calls_results = screener._screen_options(
            symbols=test_symbols,
            option_type='call',
            max_dte=7,
            min_volume=Config.get_min_volume_threshold(),
            min_oi=Config.get_min_open_interest_threshold(),
            min_whale_score=Config.get_min_whale_score()
        )
        
        print(f"✅ {len(calls_results)} CALLS trouvés")
        
        # Afficher les meilleurs
        if calls_results:
            calls_results.sort(key=lambda x: x.volume_1d, reverse=True)
            print("\n🏆 TOP 5 CALLS:")
            for i, result in enumerate(calls_results[:5], 1):
                print(f"  {i}. {result.symbol} ${result.strike} - "
                      f"Vol: {result.volume_1d:,} | OI: {result.open_interest:,} | "
                      f"Score: {result.whale_score:.1f}")
        
    except Exception as e:
        print(f"❌ Erreur screening calls: {e}")
    
    # Screening puts
    print("\n📉 Screening PUTS...")
    try:
        puts_results = screener._screen_options(
            symbols=test_symbols,
            option_type='put',
            max_dte=7,
            min_volume=Config.get_min_volume_threshold(),
            min_oi=Config.get_min_open_interest_threshold(),
            min_whale_score=Config.get_min_whale_score()
        )
        
        print(f"✅ {len(puts_results)} PUTS trouvés")
        
        # Afficher les meilleurs
        if puts_results:
            puts_results.sort(key=lambda x: x.volume_1d, reverse=True)
            print("\n🏆 TOP 5 PUTS:")
            for i, result in enumerate(puts_results[:5], 1):
                print(f"  {i}. {result.symbol} ${result.strike} - "
                      f"Vol: {result.volume_1d:,} | OI: {result.open_interest:,} | "
                      f"Score: {result.whale_score:.1f}")
        
    except Exception as e:
        print(f"❌ Erreur screening puts: {e}")
    
    total_results = len(calls_results) + len(puts_results) if 'calls_results' in locals() and 'puts_results' in locals() else 0
    
    print(f"\n{'=' * 60}")
    print("📊 RÉSUMÉ")
    print(f"{'=' * 60}")
    print(f"Environnement: {Config.get_tradier_environment()}")
    print(f"Symboles testés: {len(test_symbols)}")
    print(f"Total résultats: {total_results}")
    print(f"Mode sandbox: {Config.is_development_mode()}")
    
    if total_results > 0:
        print("\n🎉 SUCCÈS! L'interface devrait maintenant afficher ces résultats!")
    else:
        print("\n⚠️  Aucun résultat - vérifiez les paramètres ou les données")

if __name__ == "__main__":
    main()