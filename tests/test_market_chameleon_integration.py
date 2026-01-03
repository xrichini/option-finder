# test_market_chameleon_integration.py - Test d'intégration Market Chameleon
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.market_chameleon_scraper import MarketChameleonScraper, MarketChameleonEnhancer
from data.enhanced_screener import EnhancedOptionsScreener
from datetime import datetime
import pandas as pd

def test_market_chameleon_basic():
    """Test basique du scraper Market Chameleon"""
    print("=" * 60)
    print("🧪 TEST BASIQUE MARKET CHAMELEON SCRAPER")
    print("=" * 60)
    
    scraper = MarketChameleonScraper()
    
    # Test de scraping général
    print("\n1. Test de scraping général...")
    try:
        all_data = scraper.scrape_unusual_volume_data(limit=20)
        
        if all_data:
            print(f"✅ {len(all_data)} enregistrements récupérés")
            
            # Afficher un échantillon
            print("\nÉchantillon des données:")
            for i, data in enumerate(all_data[:3], 1):
                print(f"  {i}. {data.symbol} {data.option_type.upper()} ${data.strike:.2f}")
                print(f"      Volume: {data.volume:,} (Ratio: {data.volume_ratio:.2f}x)")
                print(f"      Exp: {data.expiration}, DTE: {data.dte}")
                print()
        else:
            print("⚠️ Aucune donnée récupérée - Possibles causes:")
            print("   - Site nécessite une authentification")
            print("   - Structure HTML a changé")
            print("   - Blocage anti-bot")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")

def test_market_chameleon_specific_symbols():
    """Test avec des symboles spécifiques liquides"""
    print("\n" + "=" * 60)
    print("🎯 TEST SYMBOLES SPÉCIFIQUES")
    print("=" * 60)
    
    scraper = MarketChameleonScraper()
    test_symbols = ['SPY', 'QQQ', 'TSLA', 'NVDA', 'AAPL', 'MSFT']
    
    print(f"\nRecherche d'options inhabituelles pour: {', '.join(test_symbols)}")
    
    try:
        results = scraper.get_unusual_options_for_symbols(
            symbols=test_symbols, 
            min_volume_ratio=1.5
        )
        
        if results:
            print(f"\n✅ {len(results)} options inhabituelles trouvées:")
            
            # Grouper par symbole
            by_symbol = {}
            for result in results:
                if result.symbol not in by_symbol:
                    by_symbol[result.symbol] = []
                by_symbol[result.symbol].append(result)
            
            for symbol, options in by_symbol.items():
                print(f"\n📊 {symbol}:")
                for opt in options[:3]:  # Top 3 par symbole
                    print(f"   {opt.option_type.upper()} ${opt.strike:.2f} "
                          f"Vol: {opt.volume:,} ({opt.volume_ratio:.1f}x) "
                          f"DTE: {opt.dte}")
        else:
            print("⚠️ Aucune option inhabituelle trouvée pour ces symboles")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")

def test_integration_with_our_screener():
    """Test d'intégration avec notre screener existant"""
    print("\n" + "=" * 60)
    print("🔗 TEST INTÉGRATION AVEC NOTRE SCREENER")
    print("=" * 60)
    
    try:
        # Initialiser notre screener avec paramètres permissifs
        screener = EnhancedOptionsScreener()
        
        # Symboles de test ultra-liquides
        test_symbols = ['SPY', 'QQQ', 'TSLA', 'NVDA']
        
        print(f"\n1. Screening avec notre screener sur: {', '.join(test_symbols)}")
        
        # Paramètres très permissifs
        screening_params = {
            'min_volume': 100,
            'min_whale_score': 30,
            'min_dte': 0,
            'max_dte': 60,
            'min_oi': 50,
            'max_strike_distance': 0.20,
            'option_types': ['calls', 'puts']
        }
        
        our_results = []
        for symbol in test_symbols:
            symbol_results = screener.screen_symbol_options(symbol, **screening_params)
            our_results.extend(symbol_results)
        
        print(f"   Notre screener: {len(our_results)} résultats")
        
        if our_results:
            print("   Top 3 de notre screener:")
            for i, result in enumerate(our_results[:3], 1):
                print(f"     {i}. {result.symbol} {result.side.upper()} ${result.strike:.2f} "
                      f"Score: {result.whale_score:.0f}")
        
        # 2. Maintenant, tester l'enrichissement Market Chameleon
        print("\n2. Enrichissement avec Market Chameleon...")
        
        enhancer = MarketChameleonEnhancer()
        enhanced_results = enhancer.enhance_screening_results(our_results, use_mc_data=True)
        
        print(f"   Résultats enrichis: {len(enhanced_results)} total")
        
        # Analyser l'enrichissement
        mc_confirmed = [r for r in enhanced_results if hasattr(r, 'mc_confirmed') and r.mc_confirmed]
        mc_only = [r for r in enhanced_results if hasattr(r, 'mc_source') and r.mc_source]
        
        print(f"   - Confirmés par MC: {len(mc_confirmed)}")
        print(f"   - Nouveaux de MC: {len(mc_only)}")
        
        if mc_confirmed:
            print("\n   Options confirmées par Market Chameleon:")
            for result in mc_confirmed[:3]:
                mc_ratio = getattr(result, 'mc_volume_ratio', 0)
                print(f"     ✅ {result.symbol} {result.side.upper()} ${result.strike:.2f} "
                      f"Score: {result.whale_score:.0f} (MC ratio: {mc_ratio:.1f}x)")
        
        if mc_only:
            print("\n   Nouvelles détections Market Chameleon:")
            for result in mc_only[:3]:
                mc_ratio = getattr(result, 'mc_volume_ratio', 0)
                print(f"     🆕 {result.symbol} {result.side.upper()} ${result.strike:.2f} "
                      f"Score: {result.whale_score:.0f} (MC ratio: {mc_ratio:.1f}x)")
        
    except Exception as e:
        print(f"❌ Erreur intégration: {e}")
        import traceback
        traceback.print_exc()

def test_data_export():
    """Test d'export des données combinées"""
    print("\n" + "=" * 60)
    print("💾 TEST EXPORT DES DONNÉES")
    print("=" * 60)
    
    try:
        scraper = MarketChameleonScraper()
        
        # Récupérer les données
        results = scraper.get_unusual_options_for_symbols(
            ['SPY', 'QQQ', 'TSLA'], 
            min_volume_ratio=1.0
        )
        
        if results:
            # Convertir en DataFrame pour export
            data_dict = []
            for result in results:
                data_dict.append({
                    'symbol': result.symbol,
                    'option_symbol': result.option_symbol,
                    'type': result.option_type,
                    'strike': result.strike,
                    'expiration': result.expiration,
                    'volume': result.volume,
                    'avg_volume': result.avg_volume,
                    'volume_ratio': result.volume_ratio,
                    'open_interest': result.open_interest,
                    'last_price': result.last_price,
                    'dte': result.dte,
                    'timestamp': result.timestamp
                })
            
            df = pd.DataFrame(data_dict)
            
            # Exporter en CSV
            export_file = f"market_chameleon_data_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
            df.to_csv(export_file, index=False)
            
            print(f"✅ Données exportées: {export_file}")
            print(f"   {len(df)} enregistrements")
            print(f"   Colonnes: {', '.join(df.columns)}")
            
            # Statistiques rapides
            if not df.empty:
                print("\n📈 Statistiques:")
                print(f"   Volume ratio moyen: {df['volume_ratio'].mean():.2f}")
                print(f"   Volume ratio max: {df['volume_ratio'].max():.2f}")
                print(f"   Symboles uniques: {df['symbol'].nunique()}")
                
                # Top ratios
                print("\n🔥 Top 3 ratios de volume:")
                top_ratios = df.nlargest(3, 'volume_ratio')
                for _, row in top_ratios.iterrows():
                    print(f"   {row['symbol']} {row['type'].upper()} ${row['strike']:.2f} "
                          f"Ratio: {row['volume_ratio']:.1f}x")
        else:
            print("⚠️ Aucune donnée à exporter")
            
    except Exception as e:
        print(f"❌ Erreur export: {e}")

def run_comprehensive_test():
    """Lance tous les tests Market Chameleon"""
    print("🚀 DÉMARRAGE DES TESTS MARKET CHAMELEON")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Tests séquentiels
    test_market_chameleon_basic()
    test_market_chameleon_specific_symbols()
    test_integration_with_our_screener()
    test_data_export()
    
    print("\n" + "=" * 80)
    print("✅ TOUS LES TESTS TERMINÉS")
    print("=" * 80)
    
    print("\n📋 RECOMMANDATIONS SELON LES RÉSULTATS:")
    print("1. Si le scraping fonctionne ➜ Intégrer dans le workflow principal")
    print("2. Si erreurs d'authentification ➜ Vérifier les termes d'usage")
    print("3. Si données partielles ➜ Ajuster les sélecteurs HTML")
    print("4. Si intégration réussie ➜ Ajouter option dans l'interface Streamlit")

if __name__ == "__main__":
    run_comprehensive_test()