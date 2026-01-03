# test_ai_features.py - Test des fonctionnalités IA avec paramètres permissifs
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
from data.enhanced_screener import EnhancedOptionsScreener
from data.ai_analysis_manager import AIAnalysisManager
from utils.helpers import get_high_short_interest_symbols

async def test_ai_features():
    print("🧠 TEST DES FONCTIONNALITÉS IA")
    print("=" * 50)
    
    # 1. Vérifier la configuration AI
    print("🔧 VÉRIFICATION CONFIGURATION AI...")
    enhanced_screener = EnhancedOptionsScreener()
    ai_status = enhanced_screener.get_ai_capabilities_status()
    
    print(f"📊 IA Activée: {ai_status['ai_enabled']}")
    print(f"🤖 OpenAI Disponible: {ai_status['openai_available']}")  
    print(f"🔍 Perplexity Disponible: {ai_status['perplexity_available']}")
    print(f"⚙️  AI Manager: {ai_status['has_ai_manager']}")
    
    if not ai_status['ai_enabled']:
        print("⚠️  IA non configurée. Créez un fichier .streamlit/secrets.toml avec vos clés API")
        print("📝 Consultez AI_SETUP_GUIDE.md pour les instructions")
    
    print()
    
    # 2. Charger des symboles
    print("📋 CHARGEMENT DES SYMBOLES...")
    try:
        symbols = get_high_short_interest_symbols(
            enable_prefiltering=True,
            min_market_cap=50_000_000,
            min_avg_volume=100_000
        )
        test_symbols = symbols[:3]  # Limiter pour le test
        print(f"✅ Symboles de test: {test_symbols}")
    except Exception as e:
        print(f"❌ Erreur chargement symboles: {e}")
        return
    
    # 3. Test screening avec IA (paramètres permissifs)
    print("\n🔍 TEST SCREENING AVEC IA...")
    
    def progress_callback(progress, message):
        print(f"📊 {progress*100:.0f}% - {message}")
    
    try:
        results = await enhanced_screener.screen_with_ai_analysis(
            symbols=test_symbols,
            option_type="call",
            max_dte=30,           # Plus long 
            min_volume=10,        # Très bas
            min_oi=10,           # Très bas
            min_whale_score=30,   # Permissif  
            enable_ai_for_top_n=3,  # Analyser top 3 avec IA
            progress_callback=progress_callback
        )
        
        print(f"\n✅ RÉSULTATS: {len(results)} options trouvées")
        
        if results:
            print("🏆 TOP OPTIONS:")
            for i, result in enumerate(results[:5], 1):
                has_ai = hasattr(result, '_ai_analysis') and result._ai_analysis
                ai_indicator = "🧠" if has_ai else "📊"
                
                print(f"  {i}. {ai_indicator} {result.symbol} {result.option_symbol}")
                print(f"     Score: {result.whale_score:.1f} | Vol: {result.volume_1d} | Vol/OI: {result.vol_oi_ratio:.2f}")
                
                if has_ai:
                    # Afficher les résumés AI
                    ai_analysis = result._ai_analysis
                    
                    if 'fundamental' in ai_analysis:
                        fund = ai_analysis['fundamental']
                        print(f"     🧠 Fondamental: {fund.summary[:100]}...")
                    
                    if 'sentiment' in ai_analysis:
                        sentiment = ai_analysis['sentiment']
                        score = sentiment.detailed_analysis.get('sentiment_score', 50)
                        print(f"     🎭 Sentiment: {score}/100")
                    
                    if 'catalysts' in ai_analysis:
                        catalysts = ai_analysis['catalysts']
                        catalyst_count = len(catalysts.detailed_analysis.get('catalysts', []))
                        print(f"     📰 Catalyseurs: {catalyst_count} détectés")
                
                print()
        
        else:
            print("ℹ️  Aucune option trouvée avec ces paramètres")
            print("💡 Essayez de réduire encore plus les seuils dans l'app Streamlit")
    
    except Exception as e:
        print(f"❌ Erreur screening avec IA: {e}")
        import traceback
        traceback.print_exc()
    
    # 4. Test direct AI Analysis Manager
    if ai_status['ai_enabled']:
        print("\n🤖 TEST DIRECT AI ANALYSIS MANAGER...")
        ai_manager = AIAnalysisManager()
        
        # Test données fictives d'option
        test_option_data = {
            'whale_score': 75.5,
            'vol_oi_ratio': 2.5,
            'volume_1d': 5000,
            'open_interest': 2000,
            'strike': 150,
            'expiration': '2025-09-26',
            'side': 'call',
            'dte': 7
        }
        
        print(f"🎯 Test analyse AI pour ticker: {test_symbols[0] if test_symbols else 'AAPL'}")
        
        try:
            ai_results = await ai_manager.comprehensive_analysis(
                ticker=test_symbols[0] if test_symbols else 'AAPL',
                option_data=test_option_data
            )
            
            print(f"📊 Analyses reçues: {list(ai_results.keys())}")
            
            for analysis_type, analysis in ai_results.items():
                print(f"\n📈 {analysis_type.title()}:")
                print(f"   Confiance: {analysis.confidence_score}%")
                print(f"   Résumé: {analysis.summary}")
                
                if analysis.recommendations:
                    print(f"   Recommandations: {'; '.join(analysis.recommendations[:2])}")
        
        except Exception as e:
            print(f"❌ Erreur test direct AI: {e}")
    
    print("\n✅ TEST AI TERMINÉ")
    print("💡 Pour voir l'IA en action dans Streamlit:")
    print("   1. Configurez vos clés API dans .streamlit/secrets.toml")  
    print("   2. Dans l'app, réduisez les paramètres:")
    print("      - Min Volume: 10")
    print("      - Min Whale Score: 30") 
    print("      - Max DTE: 30")
    print("   3. Activez 'Activer l'analyse AI' dans la sidebar")
    print("   4. Activez 'Afficher détails AI' pour voir les analyses complètes")

if __name__ == "__main__":
    asyncio.run(test_ai_features())