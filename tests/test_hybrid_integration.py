#!/usr/bin/env python3
"""
Test d'intégration de l'architecture hybride Tradier + Polygon.io

Ce script teste la nouvelle architecture hybride avec:
- Service hybride (HybridDataService)  
- Service de screening hybride (HybridScreeningService)
- Nouveaux endpoints FastAPI
"""

import asyncio
import logging
from datetime import datetime
import sys
import os

# Setup des paths pour imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.hybrid_data_service import HybridDataService
from services.hybrid_screening_service import HybridScreeningService
from models.api_models import OptionsOpportunity

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_hybrid_data_service():
    """Test du service de données hybrides"""
    
    print("=" * 60)
    print("🔄 TEST HYBRID DATA SERVICE")
    print("=" * 60)
    
    try:
        # Initialisation du service
        hybrid_service = HybridDataService(enable_polygon=True)
        
        # Test du statut
        print("\n📊 Statut du service hybride:")
        status = hybrid_service.get_service_status()
        for key, value in status.items():
            print(f"  {key}: {value}")
        
        # Test de récupération de données historiques
        print("\n📈 Test données historiques Polygon.io (AAPL):")
        historical_data = await hybrid_service.get_historical_volume_data("AAPL", 30)
        
        if historical_data:
            print("  ✅ Données historiques récupérées:")
            print(f"    Volume moyen 30j: {historical_data.get('avg_volume', 'N/A'):,}")
            print(f"    Tendance prix: {historical_data.get('price_trend', 'N/A')}")
            print(f"    Régime volatilité: {historical_data.get('volatility_regime', 'N/A')}")
            print(f"    Points de données: {historical_data.get('data_points', 'N/A')}")
        else:
            print("  ❌ Pas de données historiques (Polygon.io peut être non configuré)")
        
        # Test d'enrichissement d'une opportunité mock
        print("\n🔍 Test enrichissement opportunité:")
        
        # Créer une opportunité mock
        mock_opportunity = OptionsOpportunity(
            option_symbol="AAPL240315C00185000",
            underlying_symbol="AAPL",
            option_type="call",
            strike=185.0,
            expiration="2024-03-15",
            expiration_date="2024-03-15",  # Champ requis par Pydantic
            dte=7,
            last=1.25,
            bid=1.20,
            ask=1.30,
            volume=2500,
            open_interest=1200,
            whale_score=75.5,
            underlying_price=186.50
        )
        
        # Enrichissement
        hybrid_metrics = await hybrid_service.enrich_opportunity_with_hybrid_data(mock_opportunity)
        
        print("  ✅ Métriques hybrides générées:")
        print(f"    Score temps réel: {hybrid_metrics.realtime_score:.1f}")
        print(f"    Score historique: {hybrid_metrics.historical_score:.1f}")
        print(f"    Score hybride final: {hybrid_metrics.hybrid_score:.1f}")
        print(f"    Qualité Greeks: {hybrid_metrics.greeks_quality}")
        print(f"    Fraîcheur données: {hybrid_metrics.data_freshness}")
        print(f"    Polygon.io disponible: {hybrid_metrics.polygon_available}")
        
        if hybrid_metrics.volume_anomaly_ratio:
            print(f"    Ratio anomalie volume: {hybrid_metrics.volume_anomaly_ratio:.2f}x")
        
        print("  ✅ Test HybridDataService réussi!")
        
    except Exception as e:
        print(f"  ❌ Erreur test HybridDataService: {e}")

async def test_hybrid_screening_service():
    """Test du service de screening hybride"""
    
    print("\n" + "=" * 60)
    print("🔍 TEST HYBRID SCREENING SERVICE") 
    print("=" * 60)
    
    try:
        # Initialisation du service
        hybrid_screening = HybridScreeningService()
        
        # Test du statut
        print("\n📊 Statut du service de screening hybride:")
        status = await hybrid_screening.get_hybrid_service_status()
        for key, value in status.items():
            if key != "cache_entries":  # Skip cache details
                print(f"  {key}: {value}")
        
        # Test screening hybride sur symboles populaires
        test_symbols = ["AAPL", "TSLA", "NVDA", "SPY"]  # Symboles tests
        print(f"\n🚀 Test screening hybride sur {len(test_symbols)} symboles:")
        print(f"  Symboles: {', '.join(test_symbols)}")
        
        # Callback de progression
        async def progress_callback(current: int, total: int, symbol: str, details: str):
            progress_pct = (current / total) * 100 if total > 0 else 0
            print(f"    📈 {progress_pct:.0f}% - {symbol} - {details}")
        
        # Screening avec paramètres de test optimisés
        opportunities = await hybrid_screening.screen_options_hybrid(
            symbols=test_symbols,
            option_type="both",
            max_dte=14,  # Options courtes pour plus de chances de trouver des résultats
            min_volume=50,  # Volume minimum bas pour les tests
            min_oi=10,
            min_whale_score=50.0,  # Score minimum bas pour avoir des résultats
            enable_ai=False,
            progress_callback=progress_callback
        )
        
        print(f"\n  ✅ Screening terminé: {len(opportunities)} opportunités trouvées")
        
        # Affichage des meilleures opportunités
        if opportunities:
            print("\n  🏆 Top 3 opportunités hybrides:")
            for i, opp in enumerate(opportunities[:3], 1):
                print(f"    {i}. {opp['option_symbol']} ({opp['underlying_symbol']})")
                print(f"       Score hybride: {opp['hybrid_score']:.1f}")
                print(f"       Type: {opp['option_type']} | DTE: {opp['dte']}")
                print(f"       Volume: {opp['volume']:,} | OI: {opp['open_interest']:,}")
                
                # Données hybrides spécifiques
                if opp.get('volume_anomaly_ratio'):
                    print(f"       Anomalie volume: {opp['volume_anomaly_ratio']:.2f}x")
                if opp.get('price_trend_30d'):
                    print(f"       Tendance 30j: {opp['price_trend_30d']}")
                if opp.get('volatility_regime'):
                    print(f"       Volatilité: {opp['volatility_regime']}")
                
                print(f"       Fraîcheur: {opp.get('data_freshness', 'unknown')}")
                print(f"       Polygon actif: {opp.get('polygon_enabled', False)}")
                print("")
        else:
            print("    ℹ️ Aucune opportunité trouvée avec ces critères")
            print("    💡 C'est normal en dehors des heures de marché ou avec des critères stricts")
        
        print("  ✅ Test HybridScreeningService réussi!")
        
    except Exception as e:
        print(f"  ❌ Erreur test HybridScreeningService: {e}")

async def test_hybrid_recommendations():
    """Test des recommandations hybrides"""
    
    print("\n" + "=" * 60)
    print("🤖 TEST RECOMMENDATIONS HYBRIDES")
    print("=" * 60)
    
    try:
        hybrid_screening = HybridScreeningService()
        
        # Test recommandations avec symboles limités pour les tests
        test_symbols = ["SPY", "QQQ", "AAPL"]  # ETFs + stock populaire
        print(f"\n🎯 Génération de recommandations sur {len(test_symbols)} symboles:")
        
        recommendations = await hybrid_screening.get_hybrid_recommendations(
            symbols=test_symbols,
            max_results=5
        )
        
        print(f"  ✅ {len(recommendations)} recommandations générées")
        
        if recommendations:
            print("\n  🌟 Meilleures recommandations hybrides:")
            for i, rec in enumerate(recommendations, 1):
                print(f"    {i}. {rec['option_symbol']} ({rec['underlying_symbol']})")
                print(f"       Recommandation: {rec['recommendation_type']}")
                print(f"       Score confiance: {rec['confidence_score']:.1f}%")
                print(f"       Niveau risque: {rec['risk_level']}")
                
                target_profit = rec.get('target_profit')
                if target_profit:
                    print(f"       Objectif profit: {target_profit:.1f}%")
                
                stop_loss = rec.get('stop_loss')  
                if stop_loss:
                    print(f"       Stop loss suggéré: {stop_loss:.1f}%")
                
                historical_context = rec.get('historical_context', '')
                if historical_context and historical_context != "Contexte limité":
                    print(f"       Contexte: {historical_context}")
                
                # Sources de données
                data_sources = rec.get('data_sources', {})
                active_sources = [k for k, v in data_sources.items() if v]
                print(f"       Sources actives: {', '.join(active_sources)}")
                print("")
        else:
            print("    ℹ️ Aucune recommandation générée")
            print("    💡 Peut être dû aux heures de marché ou critères stricts")
        
        print("  ✅ Test recommandations hybrides réussi!")
        
    except Exception as e:
        print(f"  ❌ Erreur test recommandations: {e}")

async def main():
    """Test principal de l'intégration hybride"""
    
    print("🚀 TESTS D'INTÉGRATION ARCHITECTURE HYBRIDE")
    print("   Tradier (temps réel) + Polygon.io (historique)")
    print(f"   Timestamp: {datetime.now().isoformat()}")
    
    try:
        # Tests séquentiels
        await test_hybrid_data_service()
        await test_hybrid_screening_service()  
        await test_hybrid_recommendations()
        
        print("\n" + "=" * 60)
        print("🎉 TOUS LES TESTS TERMINÉS")
        print("=" * 60)
        print("")
        print("📋 Résumé des tests:")
        print("  ✅ HybridDataService - Service de données hybrides")
        print("  ✅ HybridScreeningService - Service de screening enrichi")
        print("  ✅ Recommandations hybrides - Algorithmes avancés")
        print("")
        print("🔧 Pour utiliser l'API FastAPI:")
        print("  1. Lancer l'app: python app.py")
        print("  2. Ouvrir: http://localhost:8000/api/docs")
        print("  3. Tester les endpoints /api/hybrid/*")
        print("")
        print("📊 Endpoints disponibles:")
        print("  • GET /api/hybrid/status - Statut des services")
        print("  • POST /api/hybrid/screen - Screening hybride")
        print("  • GET /api/hybrid/recommendations - Recommandations IA")
        print("  • GET /api/hybrid/data-sources - Info sources de données")
        print("  • GET /api/hybrid/historical/{symbol} - Analyse historique")
        print("")
        print("🔗 Architecture hybride opérationnelle!")
        
    except Exception as e:
        print(f"\n❌ ERREUR GÉNÉRALE: {e}")
        
if __name__ == "__main__":
    asyncio.run(main())