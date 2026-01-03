#!/usr/bin/env python3
"""
Test rapide du système de recommandations avec tri par score de confiance
"""

import asyncio
import logging
from services.screening_service import ScreeningService

# Configuration logging simple
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

async def test_recommendations_sort():
    """Test du tri des recommandations"""
    print("🧪 Test du système de recommandations avec tri par score...")
    
    service = ScreeningService()
    
    try:
        # Génération des recommandations
        recommendations = await service.get_ai_trade_recommendations()
        
        print(f"\n📊 {len(recommendations)} recommandations générées :\n")
        
        for i, rec in enumerate(recommendations, 1):
            confidence = rec['confidence_level'] * 100
            print(f"{i:2d}. {rec['symbol']} - {rec['strategy']}")
            print(f"    📊 Score IA: {confidence:.0f}%")
            print(f"    💰 R/R: {rec['risk_reward_ratio']:.1f}:1")
            print(f"    🎯 Probabilité: {rec['probability_success']*100:.0f}%")
            print(f"    ⏰ Horizon: {rec['time_horizon']}")
            print()
        
        # Vérification du tri
        scores = [rec['confidence_level'] for rec in recommendations]
        is_sorted_desc = all(scores[i] >= scores[i+1] for i in range(len(scores)-1))
        
        print(f"✅ Tri par score décroissant: {'CORRECT' if is_sorted_desc else 'INCORRECT'}")
        print(f"📈 Scores: {[f'{s*100:.0f}%' for s in scores]}")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    asyncio.run(test_recommendations_sort())