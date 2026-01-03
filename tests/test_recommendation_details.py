#!/usr/bin/env python3
"""
Test détaillé des informations complètes dans les recommandations IA
"""

import asyncio
import logging
from services.screening_service import ScreeningService

# Configuration logging simple
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

async def test_recommendation_details():
    """Test des détails complets des recommandations"""
    print("🔍 Test des détails complets des recommandations...")
    
    service = ScreeningService()
    
    try:
        # Génération des recommandations
        recommendations = await service.get_ai_trade_recommendations()
        
        print("\n📊 Analyse de la première recommandation :\n")
        
        if recommendations:
            rec = recommendations[0]  # Première recommandation
            
            print("="*60)
            print("🎯 DÉTAILS COMPLETS DE LA RECOMMANDATION")
            print("="*60)
            
            # Données réelles (API Tradier)
            print("\n📈 DONNÉES RÉELLES (API Tradier):")
            print(f"   • Titre: {rec['symbol']}")
            print(f"   • Option: {rec['option_symbol']}")
            print(f"   • Type: {rec['option_type']}")
            print(f"   • Strike: ${rec['strike']}")
            print(f"   • Expiration: {rec['expiration_date']} ({rec['dte']} jours)")
            print(f"   • Volume: {rec['volume']:,}")
            print(f"   • Open Interest: {rec['open_interest']:,}")
            print(f"   • Bid/Ask: ${rec['bid']}/${rec['ask']}")
            print(f"   • Dernier: ${rec['entry_price']}")
            
            # Recommandation de trade
            print("\n🎯 RECOMMANDATION DE TRADE:")
            print(f"   • Action: {rec['trade_action']}")
            print(f"   • Type complet: {rec['trade_type']}")
            print(f"   • Recommandation: {rec['full_recommendation']}")
            
            # Stratégie et analyse
            print("\n🧠 ANALYSE IA:")
            print(f"   • Score IA: {rec['confidence_level']*100:.0f}%")
            print(f"   • Stratégie: {rec['strategy']}")
            print(f"   • Description: {rec['strategy_description']}")
            print(f"   • Outlook: {rec['market_outlook']}")
            
            # Prix cibles (calculés)
            print("\n💰 PRIX CIBLES (Calculés):")
            print(f"   • Entrée: ${rec['entry_price']:.2f}")
            print(f"   • Cible: ${rec['target_price']:.2f}")
            print(f"   • Stop-loss: ${rec['stop_loss']:.2f}")
            print(f"   • Risque max: ${rec['max_risk']:.2f}")
            print(f"   • Gain potentiel: ${rec['potential_return']:.2f}")
            print(f"   • Ratio R/R: {rec['risk_reward_ratio']:.1f}:1")
            print(f"   • Probabilité: {rec['probability_success']*100:.0f}%")
            
            # Facteurs et avertissements
            print("\n📊 FACTEURS CLÉS:")
            for factor in rec['key_factors']:
                print(f"   • {factor}")
            
            if rec['warnings']:
                print("\n⚠️  AVERTISSEMENTS:")
                for warning in rec['warnings']:
                    print(f"   • {warning}")
            
            print("\n" + "="*60)
            print("🔍 ANALYSE DONNÉES RÉELLES vs CALCULÉES:")
            print("="*60)
            print("✅ RÉELLES: symbol, option_symbol, option_type, strike, expiration_date, volume, open_interest, bid, ask, entry_price")
            print("🧮 CALCULÉES: target_price, stop_loss, strategy, probability_success, trade_action")
            
        else:
            print("❌ Aucune recommandation générée")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_recommendation_details())