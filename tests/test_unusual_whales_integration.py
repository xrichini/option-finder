#!/usr/bin/env python3
"""
Test de l'intégration Unusual Whales avec analyse historique
"""

import asyncio
import logging
from services.screening_service import ScreeningService

# Configuration logging simple
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

async def test_unusual_whales_integration():
    """Test complet de l'intégration Unusual Whales"""
    print("🐋 Test intégration Unusual Whales avec analyse historique...")
    
    service = ScreeningService()
    
    try:
        print("\n📊 1. Statistiques de la base historique:")
        stats = service.unusual_whales_service.get_database_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        print("\n🔍 2. Test screening avec Unusual Whales:")
        symbols = ["AAPL", "TSLA", "NVDA"]
        opportunities = await service.screen_options_classic(symbols)
        
        print(f"   Opportunités trouvées: {len(opportunities)}")
        
        if opportunities:
            print("\n📈 3. Analyse détaillée de la première opportunité:")
            opp = opportunities[0]
            
            print(f"   Option: {opp.option_symbol}")
            print(f"   Volume: {opp.volume:,}")
            print(f"   Open Interest: {opp.open_interest:,}")
            print(f"   Score Whale v3: {opp.whale_score:.1f}")
            
            # Analyse Unusual Whales complète
            uw_analysis = service.unusual_whales_service.analyze_opportunity(opp)
            
            print("\n🐋 4. Analyse Unusual Whales complète:")
            print(f"   Vol/OI Ratio: {uw_analysis.get('vol_oi_ratio', 0):.1f}")
            print(f"   Catégorie: {uw_analysis.get('block_category', 'N/A')}")
            print(f"   Activité inhabituelle: {uw_analysis.get('unusual_activity', False)}")
            print(f"   Nouvelle position: {uw_analysis.get('new_position', False)}")
            print(f"   Signal institutionnel: {uw_analysis.get('institutional_signal', False)}")
            
            # Détails de scoring
            scoring_details = uw_analysis.get('scoring_details', {})
            if scoring_details:
                print("\n📊 5. Détails du scoring:")
                print(f"   Score de base: {scoring_details.get('base_score', 0):.1f}")
                print(f"   Anomalie volume: {scoring_details.get('volume_anomaly', 0):.1f}")
                print(f"   Anomalie OI: {scoring_details.get('oi_anomaly', 0):.1f}")
                print(f"   Données historiques: {scoring_details.get('has_historical_data', False)}")
                
                # Stats historiques détaillées
                hist_stats = scoring_details.get('historical_stats', {})
                if hist_stats:
                    vol_stats = hist_stats.get('volume_stats', {})
                    if vol_stats and vol_stats.get('volume_ratio'):
                        print(f"   📈 Volume vs moyenne: {vol_stats['volume_ratio']:.1f}x")
                        print(f"   📊 Moyenne historique: {vol_stats.get('avg_volume', 0):.0f}")
                        print(f"   📅 Points de données: {vol_stats.get('data_points', 0)}")
        
        print("\n🎯 6. Test recommandations IA avec Unusual Whales:")
        recommendations = await service.get_ai_trade_recommendations()
        
        print(f"   Recommandations générées: {len(recommendations)}")
        
        if recommendations:
            rec = recommendations[0]
            print(f"   Top recommandation: {rec['full_recommendation']}")
            print(f"   Score IA: {rec['confidence_level']*100:.0f}%")
            print(f"   Facteurs clés: {rec['key_factors'][:3]}")  # 3 premiers facteurs
        
        print("\n✅ Test réussi ! Intégration Unusual Whales opérationnelle")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_unusual_whales_integration())