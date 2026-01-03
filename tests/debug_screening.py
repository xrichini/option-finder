# debug_screening.py - Diagnostic du screening d'options
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.screener_logic import OptionsScreener
from utils.helpers import get_high_short_interest_symbols
from datetime import datetime, time
import pytz

def is_market_open():
    """Vérifie si les marchés US sont ouverts"""
    try:
        eastern = pytz.timezone('US/Eastern')
        now = datetime.now(eastern)
        current_time = now.time()
        
        # Marchés ouverts de 9h30 à 16h EST, lundi-vendredi
        market_open = time(9, 30)
        market_close = time(16, 0)
        
        is_weekend = now.weekday() >= 5  # 5=Samedi, 6=Dimanche
        is_trading_hours = market_open <= current_time <= market_close
        
        return not is_weekend and is_trading_hours, now
    except:
        return False, None

def debug_screening():
    print("🔍 DIAGNOSTIC DU SCREENING D'OPTIONS")
    print("=" * 50)
    
    # 1. Vérifier l'état du marché
    market_open, current_time = is_market_open()
    print(f"⏰ Heure actuelle: {datetime.now()}")
    if current_time:
        print(f"🏛️ Heure EST: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"📈 Marchés ouverts: {'✅ OUI' if market_open else '❌ NON'}")
    
    if not market_open:
        print("⚠️  ATTENTION: Les marchés sont fermés. Les volumes peuvent être très faibles.")
    
    print()
    
    # 2. Charger quelques symboles de test
    print("📋 CHARGEMENT DES SYMBOLES...")
    try:
        symbols = get_high_short_interest_symbols(
            enable_prefiltering=True,
            min_market_cap=50_000_000,  # Plus permissif
            min_avg_volume=100_000      # Plus permissif
        )
        print(f"✅ {len(symbols)} symboles chargés: {symbols[:10]}...")
    except Exception as e:
        print(f"❌ Erreur chargement symboles: {e}")
        return
    
    # 3. Test avec paramètres très permissifs
    print("\n🔬 TEST AVEC PARAMÈTRES PERMISSIFS...")
    screener = OptionsScreener()
    
    test_params = {
        'max_dte': 30,           # Plus long
        'min_volume': 10,        # Très bas
        'min_oi': 10,           # Très bas  
        'min_whale_score': 30   # Très bas
    }
    
    print(f"📊 Paramètres: {test_params}")
    
    # Test sur quelques symboles seulement
    test_symbols = symbols[:5] if len(symbols) > 5 else symbols
    print(f"🎯 Test sur {len(test_symbols)} symboles: {test_symbols}")
    
    # 4. Test screening calls
    print("\n📈 TEST SCREENING CALLS...")
    try:
        calls_results = screener.screen_big_calls(
            symbols=test_symbols,
            **test_params
        )
        print(f"📊 Résultats calls: {len(calls_results)} trouvés")
        
        if calls_results:
            for result in calls_results[:3]:
                print(f"  ✅ {result.symbol} {result.option_symbol} - Score: {result.whale_score:.1f}")
        
    except Exception as e:
        print(f"❌ Erreur screening calls: {e}")
        import traceback
        traceback.print_exc()
    
    # 5. Test screening puts
    print("\n📉 TEST SCREENING PUTS...")
    try:
        puts_results = screener.screen_big_puts(
            symbols=test_symbols,
            **test_params
        )
        print(f"📊 Résultats puts: {len(puts_results)} trouvés")
        
        if puts_results:
            for result in puts_results[:3]:
                print(f"  ✅ {result.symbol} {result.option_symbol} - Score: {result.whale_score:.1f}")
                
    except Exception as e:
        print(f"❌ Erreur screening puts: {e}")
        import traceback
        traceback.print_exc()
    
    # 6. Test détaillé sur un symbole
    print(f"\n🔍 TEST DÉTAILLÉ SUR {test_symbols[0]}...")
    try:
        symbol = test_symbols[0]
        
        # Obtenir les expirations
        expirations = screener.client.get_option_expirations(symbol)
        print(f"📅 Expirations disponibles: {len(expirations) if expirations else 0}")
        
        if expirations:
            print(f"   Premières expirations: {expirations[:3]}")
            
            # Filtrer par DTE
            filtered_exps = screener.client.filter_expirations_by_dte(expirations, test_params['max_dte'])
            print(f"📊 Expirations <= {test_params['max_dte']} DTE: {len(filtered_exps)}")
            
            if filtered_exps:
                # Test sur première expiration
                exp = filtered_exps[0]
                print(f"🎯 Test sur expiration: {exp}")
                
                chain_data = screener.client.get_option_chains(symbol, exp)
                print(f"⛓️  Options dans la chaîne: {len(chain_data) if chain_data else 0}")
                
                if chain_data:
                    # Analyser les options disponibles
                    calls = [opt for opt in chain_data if opt["option_type"].lower() == "call"]
                    puts = [opt for opt in chain_data if opt["option_type"].lower() == "put"]
                    
                    print(f"📈 Calls disponibles: {len(calls)}")
                    print(f"📉 Puts disponibles: {len(puts)}")
                    
                    # Vérifier les volumes
                    if calls:
                        volumes = [opt.get('volume', 0) for opt in calls]
                        max_vol = max(volumes) if volumes else 0
                        print(f"📊 Volume max calls: {max_vol}")
                        
                        # Options avec volume > 0
                        active_calls = [opt for opt in calls if opt.get('volume', 0) > 0]
                        print(f"🔥 Calls avec volume > 0: {len(active_calls)}")
                        
                        if active_calls:
                            for opt in active_calls[:3]:
                                print(f"   📈 {opt['symbol']} Vol:{opt.get('volume', 0)} OI:{opt.get('open_interest', 0)}")
    
    except Exception as e:
        print(f"❌ Erreur test détaillé: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ DIAGNOSTIC TERMINÉ")
    print("💡 Si aucune option trouvée, essayez:")
    print("   - Réduire min_volume à 1")
    print("   - Réduire min_oi à 1") 
    print("   - Réduire min_whale_score à 10")
    print("   - Augmenter max_dte à 45")
    print("   - Tester pendant les heures de marché")

if __name__ == "__main__":
    debug_screening()