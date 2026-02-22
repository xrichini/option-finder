#!/usr/bin/env python3
"""
Test rapide du scraper Short Interest
"""

import asyncio
import logging
from data.short_interest_scraper import ShortInterestScraper

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_scraper():
    """Test du scraper Short Interest"""
    try:
        scraper = ShortInterestScraper()
        print('📊 Test de récupération des données short interest...')
        
        # Test sur un petit échantillon
        data = await scraper.get_high_short_interest_data(exchange='nasdaq', limit=5)
        
        if data:
            print(f'✅ {len(data)} stocks récupérés avec succès!')
            for stock in data[:3]:  # Affiche les 3 premiers
                print(f'🎯 {stock["symbol"]}: {stock["short_interest_percent"]:.1f}% short interest')
                if stock.get("market_cap"):
                    print(f'   💰 Market cap: ${stock["market_cap"]:,}')
                if stock.get("sector"):
                    print(f'   🏢 Secteur: {stock["sector"]}')
                print()
        else:
            print('❌ Aucune donnée récupérée')
            
    except Exception as e:
        print(f'❌ Erreur durant le test: {e}')

if __name__ == "__main__":
    asyncio.run(test_scraper())