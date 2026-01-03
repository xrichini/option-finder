#!/usr/bin/env python3
"""
Test des paramètres sandbox-friendly pour valider qu'on obtient des résultats
avec des critères adaptés aux données de développement
"""

import sys
import os
sys.path.insert(0, os.getcwd())

from utils.config import Config
from data.enhanced_tradier_client import EnhancedTradierClient

def main():
    print("🧪 TEST PARAMÈTRES SANDBOX-FRIENDLY")
    print("=" * 60)
    
    # 1. Vérification de la configuration
    print("\n📋 Configuration actuelle...")
    print(f"  🌍 Environnement: {Config.get_tradier_environment()}")
    print(f"  🔗 URL: {Config.get_tradier_base_url()}")
    print(f"  🏠 Mode développement: {Config.is_development_mode()}")
    
    # Affichage des paramètres
    params = Config.get_screening_parameters()
    print("\n🔧 Paramètres de screening:")
    for key, value in params.items():
        print(f"    {key}: {value}")
    
    # 2. Test du client avec paramètres sandbox
    print("\n🔗 Test client Tradier...")
    client = EnhancedTradierClient(Config.get_tradier_api_key())
    
    # 3. Test avec quelques symboles populaires
    test_symbols = ['AAPL', 'TSLA', 'SPY', 'NVDA']
    print(f"\n📊 Test screening sur {len(test_symbols)} symboles...")
    print(f"  📋 Symboles: {', '.join(test_symbols)}")
    
    # Récupération des chaînes d'options
    all_options = []
    for symbol in test_symbols:
        print(f"    🔍 Analyse {symbol}...")
        contracts = client.get_options_chains(symbol)
        print(f"      ✅ {len(contracts)} contrats trouvés")
        all_options.extend(contracts)
    
    print(f"\n📊 Total: {len(all_options)} contrats collectés")
    
    if not all_options:
        print("❌ Aucun contrat trouvé - problème avec les données")
        return
    
    # 4. Filtrage avec paramètres sandbox
    print("\n🔍 Filtrage avec paramètres sandbox...")
    min_volume = Config.get_min_volume_threshold()
    min_oi = Config.get_min_open_interest_threshold() 
    min_whale_score = Config.get_min_whale_score()
    
    print("  🎯 Critères:")
    print(f"    Volume minimum: {min_volume}")
    print(f"    Open Interest minimum: {min_oi}")
    print(f"    Score whale minimum: {min_whale_score}")
    
    # Filtrage simple
    filtered_options = []
    for contract in all_options:
        volume = getattr(contract, 'volume', 0) or 0
        oi = getattr(contract, 'open_interest', 0) or 0
        
        if volume >= min_volume and oi >= min_oi:
            filtered_options.append({
                'symbol': contract.symbol,
                'underlying': contract.underlying,
                'strike': contract.strike,
                'option_type': contract.option_type,
                'volume': volume,
                'open_interest': oi,
                'last': getattr(contract, 'last', 0),
                'vol_oi_ratio': volume / max(oi, 1)
            })
    
    print(f"\n✅ {len(filtered_options)} options passent les critères")
    
    # 5. Affichage des meilleurs résultats
    if filtered_options:
        # Tri par volume décroissant
        filtered_options.sort(key=lambda x: x['volume'], reverse=True)
        
        print("\n🏆 TOP 10 OPTIONS (volume):")
        for i, opt in enumerate(filtered_options[:10], 1):
            print(f"    {i}. {opt['underlying']} {opt['option_type'].upper()} ${opt['strike']}")
            print(f"       Vol: {opt['volume']:,} | OI: {opt['open_interest']:,} | "
                  f"Ratio: {opt['vol_oi_ratio']:.2f} | Prix: ${opt['last']:.2f}")
    else:
        print("❌ Aucune option ne passe les critères - essayez des paramètres encore plus bas")
        print("\n💡 Suggestion: diminuez encore les paramètres:")
        print("   - Volume minimum: 1")
        print("   - Open Interest minimum: 1")
        print("   - Ou utilisez des symboles plus actifs")
    
    print(f"\n{'=' * 60}")
    print("📊 RÉSUMÉ")
    print(f"{'=' * 60}")
    print(f"Environnement: {Config.get_tradier_environment()}")
    print(f"Contrats analysés: {len(all_options)}")
    print(f"Contrats filtrés: {len(filtered_options)}")
    print(f"Taux de réussite: {len(filtered_options)/max(len(all_options),1)*100:.1f}%")
    
    if Config.is_development_mode():
        print("\n🏠 MODE SANDBOX ACTIF:")
        print("✅ Paramètres relaxés pour développement")
        print("✅ Données de test utilisées")
        print("✅ Critères adaptés aux volumes sandbox")
    
    if len(filtered_options) > 0:
        print("\n🎉 SUCCÈS! Vous devriez maintenant voir des options dans l'interface!")
    else:
        print("\n⚠️  Aucun résultat - paramètres peut-être encore trop stricts pour sandbox")

if __name__ == "__main__":
    main()