# test_market_chameleon_simple.py - Test Market Chameleon standalone
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.market_chameleon_scraper import MarketChameleonScraper, MarketChameleonEnhancer
from datetime import datetime
import pandas as pd

def test_market_chameleon_scraper_basic():
    """Test basique du scraper Market Chameleon"""
    print("=" * 60)
    print("🧪 TEST BASIQUE MARKET CHAMELEON SCRAPER")
    print("=" * 60)
    
    try:
        scraper = MarketChameleonScraper()
        
        print("\n1. Test de scraping général (limite 10 pour rapidité)...")
        all_data = scraper.scrape_unusual_volume_data(limit=10)
        
        if all_data:
            print(f"✅ {len(all_data)} enregistrements récupérés")
            
            # Afficher un échantillon
            print("\nÉchantillon des données:")
            for i, data in enumerate(all_data[:3], 1):
                print(f"  {i}. {data.symbol} {data.option_type.upper()} ${data.strike:.2f}")
                print(f"      Volume: {data.volume:,} (Ratio: {data.volume_ratio:.2f}x)")
                print(f"      Exp: {data.expiration}, DTE: {data.dte}")
                print()
            
            # Statistiques rapides
            avg_ratio = sum(d.volume_ratio for d in all_data) / len(all_data) if all_data else 0
            max_ratio = max(d.volume_ratio for d in all_data) if all_data else 0
            
            print("📊 Statistiques:")
            print(f"   - Ratio moyen: {avg_ratio:.2f}x")
            print(f"   - Ratio maximum: {max_ratio:.2f}x")
            print(f"   - Symboles uniques: {len(set(d.symbol for d in all_data))}")
            
        else:
            print("⚠️ Aucune donnée récupérée")
            print("   Causes possibles:")
            print("   - Site nécessite authentification")
            print("   - Structure HTML modifiée")
            print("   - Blocage anti-bot temporaire")
            print("   - Marchés fermés")
            
        return len(all_data) > 0
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_market_chameleon_specific_symbols():
    """Test avec des symboles spécifiques liquides"""
    print("\n" + "=" * 60)
    print("🎯 TEST SYMBOLES SPÉCIFIQUES")
    print("=" * 60)
    
    try:
        scraper = MarketChameleonScraper()
        test_symbols = ['SPY', 'QQQ', 'TSLA', 'NVDA', 'AAPL']
        
        print(f"\nRecherche d'options inhabituelles pour: {', '.join(test_symbols)}")
        print("Seuil: ratio volume >= 1.5x")
        
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
                print(f"\n📊 {symbol} ({len(options)} options):")
                for opt in options[:3]:  # Top 3 par symbole
                    print(f"   {opt.option_type.upper()} ${opt.strike:.2f} "
                          f"Vol: {opt.volume:,} ({opt.volume_ratio:.1f}x) "
                          f"DTE: {opt.dte}")
                if len(options) > 3:
                    print(f"   ... et {len(options)-3} autres")
        else:
            print("⚠️ Aucune option inhabituelle trouvée")
            print("   - Peut-être que les seuils sont trop stricts")
            print("   - Ou les marchés sont peu actifs actuellement")
            
        return len(results) > 0
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def test_data_processing():
    """Test du traitement et export des données"""
    print("\n" + "=" * 60)
    print("💾 TEST TRAITEMENT DES DONNÉES")
    print("=" * 60)
    
    try:
        scraper = MarketChameleonScraper()
        
        # Récupérer les données avec seuil bas pour avoir des résultats
        results = scraper.get_unusual_options_for_symbols(
            ['SPY', 'QQQ'], 
            min_volume_ratio=1.0  # Seuil très bas
        )
        
        if results:
            # Convertir en DataFrame
            data_list = []
            for result in results:
                data_list.append({
                    'symbol': result.symbol,
                    'option_type': result.option_type,
                    'strike': result.strike,
                    'expiration': result.expiration,
                    'volume': result.volume,
                    'avg_volume': result.avg_volume,
                    'volume_ratio': result.volume_ratio,
                    'dte': result.dte,
                    'timestamp': result.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                })
            
            df = pd.DataFrame(data_list)
            
            print(f"✅ {len(df)} enregistrements traités")
            print(f"Colonnes: {list(df.columns)}")
            
            # Statistiques
            if not df.empty:
                print("\n📈 Statistiques des données:")
                print(f"   Volume ratio moyen: {df['volume_ratio'].mean():.2f}")
                print(f"   Volume ratio médian: {df['volume_ratio'].median():.2f}")
                print(f"   Volume ratio max: {df['volume_ratio'].max():.2f}")
                print(f"   DTE moyen: {df['dte'].mean():.1f} jours")
                
                # Types d'options
                type_counts = df['option_type'].value_counts()
                print("\n📊 Répartition par type:")
                for opt_type, count in type_counts.items():
                    print(f"   {opt_type.upper()}: {count}")
                
                # Export test
                export_file = f"mc_test_data_{datetime.now().strftime('%H%M')}.csv"
                df.to_csv(export_file, index=False)
                print(f"\n💾 Données exportées: {export_file}")
                
                # Afficher le top 3
                print("\n🔥 Top 3 ratios de volume:")
                top_3 = df.nlargest(3, 'volume_ratio')
                for i, (_, row) in enumerate(top_3.iterrows(), 1):
                    print(f"   {i}. {row['symbol']} {row['option_type'].upper()} "
                          f"${row['strike']:.2f} - {row['volume_ratio']:.1f}x")
                
        else:
            print("⚠️ Pas de données à traiter")
            
        return len(results) > 0 if results else False
        
    except Exception as e:
        print(f"❌ Erreur processing: {e}")
        return False

def test_enhancer_mock():
    """Test de l'enhancer avec données simulées"""
    print("\n" + "=" * 60)
    print("🔗 TEST ENHANCER (MODE SIMULATION)")
    print("=" * 60)
    
    try:
        from models.option_model import OptionScreenerResult
        
        # Créer quelques résultats simulés
        mock_results = []
        
        # Simuler des résultats de notre screener
        for i, (symbol, strike) in enumerate([('SPY', 500), ('QQQ', 400), ('TSLA', 250)]):
            result = OptionScreenerResult(
                symbol=symbol,
                option_symbol=f"{symbol}250120C{strike:08d}",
                expiration="2025-01-20",
                strike=strike,
                side="call",
                delta=0.5,
                volume_1d=5000 + i*1000,
                volume_7d=35000 + i*7000,
                open_interest=10000 + i*2000,
                last_price=10.5,
                bid=10.0,
                ask=11.0,
                implied_volatility=0.25,
                whale_score=75 + i*5,
                dte=7
            )
            mock_results.append(result)
        
        print(f"Résultats simulés créés: {len(mock_results)}")
        for result in mock_results:
            print(f"   {result.symbol} {result.side.upper()} ${result.strike} "
                  f"Score: {result.whale_score}")
        
        # Tester l'enhancer
        enhancer = MarketChameleonEnhancer()
        
        print("\nTest d'enrichissement avec Market Chameleon...")
        enhanced_results = enhancer.enhance_screening_results(
            mock_results, 
            use_mc_data=True
        )
        
        print(f"Résultats après enrichissement: {len(enhanced_results)}")
        
        # Analyser les enrichissements
        mc_confirmed = [r for r in enhanced_results if hasattr(r, 'mc_confirmed') and r.mc_confirmed]
        mc_new = [r for r in enhanced_results if hasattr(r, 'mc_source') and r.mc_source]
        
        print(f"   Confirmés par MC: {len(mc_confirmed)}")
        print(f"   Nouveaux de MC: {len(mc_new)}")
        
        if mc_confirmed:
            print("\n✅ Options confirmées par Market Chameleon:")
            for result in mc_confirmed:
                mc_ratio = getattr(result, 'mc_volume_ratio', 0)
                print(f"   {result.symbol} {result.side.upper()} ${result.strike} "
                      f"(MC ratio: {mc_ratio:.1f}x)")
        
        if mc_new:
            print("\n🆕 Nouvelles détections Market Chameleon:")
            for result in mc_new:
                mc_ratio = getattr(result, 'mc_volume_ratio', 0)
                print(f"   {result.symbol} {result.side.upper()} ${result.strike} "
                      f"(MC ratio: {mc_ratio:.1f}x)")
                      
        return True
        
    except Exception as e:
        print(f"❌ Erreur enhancer: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_simple_tests():
    """Lance tous les tests simples Market Chameleon"""
    print("🚀 TESTS MARKET CHAMELEON - VERSION SIMPLIFIÉE")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = {}
    
    # Test 1: Scraper basique
    print("TEST 1/4: Scraper basique")
    results['scraper_basic'] = test_market_chameleon_scraper_basic()
    
    # Test 2: Symboles spécifiques
    print("\nTEST 2/4: Symboles spécifiques")
    results['symbols_specific'] = test_market_chameleon_specific_symbols()
    
    # Test 3: Traitement des données
    print("\nTEST 3/4: Traitement des données")
    results['data_processing'] = test_data_processing()
    
    # Test 4: Enhancer simulé
    print("\nTEST 4/4: Enhancer simulé")
    results['enhancer_mock'] = test_enhancer_mock()
    
    # Résumé final
    print("\n" + "=" * 80)
    print("📊 RÉSUMÉ DES TESTS")
    print("=" * 80)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSÉ" if result else "❌ ÉCHOUÉ"
        print(f"{test_name.ljust(20)}: {status}")
    
    print(f"\nRésultat global: {passed}/{total} tests réussis ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 TOUS LES TESTS SONT PASSÉS!")
        print("✅ Market Chameleon est opérationnel")
    elif passed >= total/2:
        print("\n⚠️ Tests partiellement réussis")
        print("📝 Vérifier les logs pour les tests échoués")
    else:
        print("\n❌ Tests majoritairement échoués")
        print("🔧 Vérifier la configuration et connectivité")
    
    print("\n📋 PROCHAINES ÉTAPES:")
    print("1. Si scraping OK ➜ Intégrer dans l'interface principale")
    print("2. Si erreurs réseau ➜ Vérifier proxy/firewall") 
    print("3. Si structure HTML ➜ Mettre à jour les sélecteurs")
    print("4. Si tout OK ➜ Activer Market Chameleon dans Streamlit")

if __name__ == "__main__":
    run_simple_tests()