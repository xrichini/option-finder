# test_liquid_tickers.py - Test avec les tickers les plus liquides pour maximiser les résultats
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
from data.enhanced_screener import EnhancedOptionsScreener
from data.screener_logic import OptionsScreener

# Tickers ultra-liquides avec forte activité options
LIQUID_TICKERS = ['SPY', 'QQQ', 'TSLA', 'NVDA', 'AAPL', 'MSFT', 'AMZN', 'META']

async def test_liquid_tickers():
    print("🚀 TEST AVEC TICKERS ULTRA-LIQUIDES")
    print("=" * 60)
    
    # Utiliser les tickers les plus actifs
    test_symbols = LIQUID_TICKERS[:4]  # SPY, QQQ, TSLA, NVDA
    print(f"🎯 Tickers testés: {test_symbols}")
    print("💡 Ces tickers ont généralement beaucoup d'activité options même hors heures de marché")
    print()
    
    # Vérifier configuration IA
    print("🔧 VÉRIFICATION IA...")
    enhanced_screener = EnhancedOptionsScreener()
    ai_status = enhanced_screener.get_ai_capabilities_status()
    
    print(f"🧠 IA Activée: {ai_status['ai_enabled']}")
    print(f"🤖 OpenAI: {ai_status['openai_available']}")
    print(f"🔍 Perplexity: {ai_status['perplexity_available']}")
    
    if ai_status['ai_enabled']:
        print("✅ IA configurée - test complet avec analyse")
    else:
        print("⚠️  IA non configurée - test screening classique")
    print()
    
    # Test avec paramètres très permissifs pour maximiser les résultats
    test_params = {
        'max_dte': 45,           # Plus long pour plus d'options
        'min_volume': 1,         # Minimum absolu
        'min_oi': 1,            # Minimum absolu  
        'min_whale_score': 10,   # Très permissif
        'enable_ai_for_top_n': 3 if ai_status['ai_enabled'] else 0
    }
    
    print(f"📊 Paramètres de test: {test_params}")
    print()
    
    # Test CALLS
    print("📈 TEST CALLS SUR TICKERS LIQUIDES...")
    
    def progress_callback(progress, message):
        print(f"   📊 {progress*100:.0f}% - {message}")
    
    try:
        if ai_status['ai_enabled']:
            # Test avec IA
            print("🧠 Utilisation du screener avec IA...")
            results = await enhanced_screener.screen_with_ai_analysis(
                symbols=test_symbols,
                option_type="call",
                progress_callback=progress_callback,
                **{k: v for k, v in test_params.items() if k != 'enable_ai_for_top_n'},
                enable_ai_for_top_n=test_params['enable_ai_for_top_n']
            )
        else:
            # Test classique
            print("📊 Utilisation du screener classique...")
            screener = OptionsScreener()
            results = screener.screen_big_calls(
                symbols=test_symbols,
                **{k: v for k, v in test_params.items() if k != 'enable_ai_for_top_n'}
            )
        
        print(f"\n✅ RÉSULTATS CALLS: {len(results)} options trouvées")
        
        if results:
            print("\n🏆 TOP 10 CALLS:")
            for i, result in enumerate(results[:10], 1):
                has_ai = hasattr(result, '_ai_analysis') and result._ai_analysis
                ai_indicator = "🧠" if has_ai else "📊"
                
                print(f"  {i:2d}. {ai_indicator} {result.symbol:4s} {result.option_symbol}")
                print(f"      Score: {result.whale_score:5.1f} | Vol: {result.volume_1d:8,} | Vol/OI: {result.vol_oi_ratio:5.2f} | DTE: {result.dte:2d}")
                
                if has_ai:
                    ai_analysis = result._ai_analysis
                    summaries = []
                    
                    if 'fundamental' in ai_analysis:
                        conf = ai_analysis['fundamental'].confidence_score
                        summaries.append(f"Fund:{conf}%")
                    
                    if 'sentiment' in ai_analysis:
                        score = ai_analysis['sentiment'].detailed_analysis.get('sentiment_score', 50)
                        summaries.append(f"Sent:{score}/100")
                    
                    if 'catalysts' in ai_analysis:
                        cat_count = len(ai_analysis['catalysts'].detailed_analysis.get('catalysts', []))
                        summaries.append(f"Cat:{cat_count}")
                    
                    if summaries:
                        print(f"      🧠 IA: {' | '.join(summaries)}")
                
                print()
        
        else:
            print("⚠️ Aucun call trouvé - essayez de réduire encore min_whale_score")
    
    except Exception as e:
        print(f"❌ Erreur test calls: {e}")
        import traceback
        traceback.print_exc()
    
    # Test PUTS
    print("\n📉 TEST PUTS SUR TICKERS LIQUIDES...")
    
    try:
        if ai_status['ai_enabled']:
            # Test avec IA
            results_puts = await enhanced_screener.screen_with_ai_analysis(
                symbols=test_symbols,
                option_type="put",
                progress_callback=progress_callback,
                **{k: v for k, v in test_params.items() if k != 'enable_ai_for_top_n'},
                enable_ai_for_top_n=test_params['enable_ai_for_top_n']
            )
        else:
            # Test classique
            screener = OptionsScreener()
            results_puts = screener.screen_big_puts(
                symbols=test_symbols,
                **{k: v for k, v in test_params.items() if k != 'enable_ai_for_top_n'}
            )
        
        print(f"\n✅ RÉSULTATS PUTS: {len(results_puts)} options trouvées")
        
        if results_puts:
            print("\n🏆 TOP 5 PUTS:")
            for i, result in enumerate(results_puts[:5], 1):
                has_ai = hasattr(result, '_ai_analysis') and result._ai_analysis
                ai_indicator = "🧠" if has_ai else "📊"
                
                print(f"  {i}. {ai_indicator} {result.symbol:4s} {result.option_symbol}")
                print(f"     Score: {result.whale_score:5.1f} | Vol: {result.volume_1d:8,} | Vol/OI: {result.vol_oi_ratio:5.2f}")
                
                if has_ai and result.ai_summary_display != "N/A":
                    print(f"     🧠 {result.ai_summary_display[:80]}...")
                print()
        
    except Exception as e:
        print(f"❌ Erreur test puts: {e}")
    
    # Test détaillé sur le ticker le plus actif
    print(f"\n🔍 ANALYSE DÉTAILLÉE: {test_symbols[0]} (SPY)")
    
    try:
        screener = OptionsScreener()
        
        # Stats sur SPY
        expirations = screener.client.get_option_expirations('SPY')
        print(f"📅 Expirations SPY disponibles: {len(expirations) if expirations else 0}")
        
        if expirations:
            print(f"   Prochaines: {expirations[:5]}")
            
            # Test sur première expiration
            exp = expirations[0]
            chain_data = screener.client.get_option_chains('SPY', exp)
            
            if chain_data:
                calls = [opt for opt in chain_data if opt["option_type"].lower() == "call"]
                puts = [opt for opt in chain_data if opt["option_type"].lower() == "put"]
                
                print(f"⛓️  Expiration {exp}:")
                print(f"   📈 Calls: {len(calls)}")
                print(f"   📉 Puts: {len(puts)}")
                
                # Analyser les volumes
                if calls:
                    volumes = [opt.get('volume', 0) for opt in calls]
                    active_calls = [opt for opt in calls if opt.get('volume', 0) > 100]
                    
                    print(f"   🔥 Calls avec volume > 100: {len(active_calls)}")
                    
                    if active_calls:
                        # Top 3 par volume
                        top_by_volume = sorted(active_calls, key=lambda x: x.get('volume', 0), reverse=True)[:3]
                        print("   📊 Top calls par volume:")
                        for opt in top_by_volume:
                            print(f"      {opt['symbol']} Vol:{opt.get('volume', 0):,} OI:{opt.get('open_interest', 0):,}")
    
    except Exception as e:
        print(f"❌ Erreur analyse SPY: {e}")
    
    # Vérifier base de données
    print("\n💾 VÉRIFICATION BASE DE DONNÉES...")
    
    try:
        import sqlite3
        db_path = os.path.join('data', 'options_history.db')
        
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM option_history')
            total_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM option_history WHERE scan_date = date("now")')
            today_count = cursor.fetchone()[0]
            
            print(f"📊 Total records: {total_count}")
            print(f"📊 Records today: {today_count}")
            
            if today_count > 0:
                cursor.execute('''
                    SELECT underlying, COUNT(*) as count 
                    FROM option_history 
                    WHERE scan_date = date("now") 
                    GROUP BY underlying 
                    ORDER BY count DESC 
                    LIMIT 5
                ''')
                
                top_symbols = cursor.fetchall()
                print("📈 Top symboles aujourd'hui:")
                for symbol, count in top_symbols:
                    print(f"   {symbol}: {count} options")
            
            conn.close()
    
    except Exception as e:
        print(f"❌ Erreur vérification DB: {e}")
    
    print("\n✅ TEST TERMINÉ")
    print("💡 Pour voir plus de résultats dans l'app Streamlit:")
    print("   1. Utilisez ces mêmes paramètres dans la sidebar")
    print("   2. Testez pendant les heures de marché (9:30-16:00 EST)")
    print("   3. Ajoutez d'autres tickers liquides: AAPL, MSFT, AMZN, META")

if __name__ == "__main__":
    asyncio.run(test_liquid_tickers())