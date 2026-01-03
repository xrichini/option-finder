#!/usr/bin/env python3
"""
Short Interest Endpoints
API endpoints pour la gestion du short interest et pré-filtrage des symboles
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import logging
from datetime import datetime

from data.short_interest_scraper import ShortInterestScraper, MarketFilterParams, ShortInterestStock
from data.ai_short_interest_classifier import AIShortInterestClassifier

logger = logging.getLogger(__name__)

# Router pour les endpoints short interest
short_interest_router = APIRouter(prefix="/api/short-interest", tags=["short-interest"])

class ShortInterestRequest(BaseModel):
    """Requête pour récupérer les stocks avec short interest élevé"""
    exchange: str = Field(default="all", description="Exchange à cibler (all, nasdaq, nyse, amex)")
    enable_prefiltering: bool = Field(default=True, description="Activer le pré-filtrage par critères de marché")
    min_market_cap: int = Field(default=100_000_000, description="Capitalisation minimum en USD")
    min_avg_volume: int = Field(default=500_000, description="Volume moyen minimum")
    min_short_interest: float = Field(default=20.0, description="Short interest minimum en pourcentage")
    max_price: Optional[float] = Field(default=None, description="Prix maximum par action")
    excluded_sectors: Optional[List[str]] = Field(default=None, description="Secteurs à exclure")

class ShortInterestStock(BaseModel):
    """Modèle de réponse pour un stock avec short interest élevé"""
    symbol: str
    company_name: str
    exchange: str
    short_interest_pct: float
    float_shares: Optional[float] = None
    outstanding_shares: Optional[float] = None
    industry: Optional[str] = None
    market_cap: Optional[int] = None
    avg_volume: Optional[int] = None
    price: Optional[float] = None
    sector: Optional[str] = None

class ShortInterestResponse(BaseModel):
    """Réponse pour les stocks avec short interest élevé"""
    success: bool
    timestamp: datetime
    stocks: List[ShortInterestStock]
    total_count: int
    filtered_count: int
    scraping_params: Dict[str, Any]
    execution_time_seconds: float

class SymbolsRequest(BaseModel):
    """Requête simplifiée pour obtenir seulement les symboles"""
    exchange: str = Field(default="all", description="Exchange à cibler")
    enable_prefiltering: bool = Field(default=True, description="Activer le pré-filtrage")
    min_market_cap: int = Field(default=100_000_000, description="Capitalisation minimum")
    min_avg_volume: int = Field(default=500_000, description="Volume moyen minimum")

class SymbolsResponse(BaseModel):
    """Réponse simplifiée avec seulement les symboles"""
    success: bool
    timestamp: datetime
    symbols: List[str]
    count: int
    execution_time_seconds: float
    filtering_applied: bool

@short_interest_router.get("/stocks", response_model=ShortInterestResponse)
async def get_short_interest_stocks(
    exchange: str = Query(default="all", description="Exchange (all, nasdaq, nyse, amex)"),
    enable_prefiltering: bool = Query(default=True, description="Activer le pré-filtrage"),
    min_market_cap: int = Query(default=100_000_000, description="Market cap minimum"),
    min_avg_volume: int = Query(default=500_000, description="Volume moyen minimum"),
    min_short_interest: float = Query(default=20.0, description="Short interest minimum %"),
    max_price: Optional[float] = Query(default=None, description="Prix maximum"),
):
    """
    Récupère les stocks avec short interest élevé depuis HighShortInterest.com
    
    Cette route scrape HighShortInterest.com, enrichit les données avec yfinance,
    et applique des filtres de marché pour identifier les candidats au short squeeze.
    """
    start_time = datetime.now()
    
    try:
        logger.info(f"🔍 Début scraping short interest - Exchange: {exchange}")
        
        # Initialiser le scraper
        scraper = ShortInterestScraper()
        
        # Scraping initial
        stocks = scraper.scrape_short_interest_stocks(exchange=exchange)
        initial_count = len(stocks)
        
        if not stocks:
            return ShortInterestResponse(
                success=True,
                timestamp=datetime.now(),
                stocks=[],
                total_count=0,
                filtered_count=0,
                scraping_params={
                    "exchange": exchange,
                    "enable_prefiltering": enable_prefiltering,
                    "min_market_cap": min_market_cap,
                    "min_avg_volume": min_avg_volume,
                    "min_short_interest": min_short_interest,
                    "max_price": max_price
                },
                execution_time_seconds=(datetime.now() - start_time).total_seconds()
            )
        
        # Pré-filtrage si activé
        filtered_stocks = stocks
        if enable_prefiltering:
            logger.info(f"📊 Enrichissement et filtrage de {len(stocks)} stocks")
            
            # Enrichir avec données de marché
            enriched_stocks = scraper.enrich_with_market_data(stocks)
            
            # Appliquer les filtres
            filter_params = MarketFilterParams(
                min_market_cap=min_market_cap,
                min_avg_volume=min_avg_volume,
                min_short_interest=min_short_interest,
                max_price=max_price
            )
            
            filtered_stocks = scraper.filter_stocks_by_criteria(enriched_stocks, filter_params)
        
        # Convertir en format de réponse
        response_stocks = [
            ShortInterestStock(
                symbol=stock.symbol,
                company_name=stock.company_name,
                exchange=stock.exchange,
                short_interest_pct=stock.short_interest_pct,
                float_shares=stock.float_shares,
                outstanding_shares=stock.outstanding_shares,
                industry=stock.industry,
                market_cap=stock.market_cap,
                avg_volume=stock.avg_volume,
                price=stock.price,
                sector=stock.sector
            )
            for stock in filtered_stocks
        ]
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"✅ Short interest scraping terminé: {len(response_stocks)} stocks en {execution_time:.2f}s")
        
        return ShortInterestResponse(
            success=True,
            timestamp=datetime.now(),
            stocks=response_stocks,
            total_count=initial_count,
            filtered_count=len(response_stocks),
            scraping_params={
                "exchange": exchange,
                "enable_prefiltering": enable_prefiltering,
                "min_market_cap": min_market_cap,
                "min_avg_volume": min_avg_volume,
                "min_short_interest": min_short_interest,
                "max_price": max_price
            },
            execution_time_seconds=execution_time
        )
        
    except Exception as e:
        logger.error(f"❌ Erreur lors du scraping short interest: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors du scraping: {str(e)}")

@short_interest_router.get("/symbols", response_model=SymbolsResponse)
async def get_short_interest_symbols(
    exchange: str = Query(default="all", description="Exchange (all, nasdaq, nyse, amex)"),
    enable_prefiltering: bool = Query(default=True, description="Activer le pré-filtrage"),
    min_market_cap: int = Query(default=100_000_000, description="Market cap minimum"),
    min_avg_volume: int = Query(default=500_000, description="Volume moyen minimum"),
):
    """
    Version simplifiée qui retourne seulement la liste des symboles
    
    Idéale pour alimenter le système de screening d'options avec une liste
    de symboles pré-filtrés ayant un short interest élevé.
    """
    start_time = datetime.now()
    
    try:
        logger.info(f"🎯 Récupération symboles short interest - Exchange: {exchange}")
        
        # Utiliser la fonction compatible avec l'ancien système
        from data.short_interest_scraper import get_high_short_interest_symbols
        
        symbols = get_high_short_interest_symbols(
            enable_prefiltering=enable_prefiltering,
            min_market_cap=min_market_cap,
            min_avg_volume=min_avg_volume,
            exchange=exchange
        )
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"✅ {len(symbols)} symboles récupérés en {execution_time:.2f}s")
        
        return SymbolsResponse(
            success=True,
            timestamp=datetime.now(),
            symbols=symbols,
            count=len(symbols),
            execution_time_seconds=execution_time,
            filtering_applied=enable_prefiltering
        )
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des symboles: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération: {str(e)}")

@short_interest_router.post("/scan", response_model=Dict[str, Any])
async def scan_with_short_interest_symbols(
    request: SymbolsRequest,
    min_volume: int = Query(default=100, description="Volume minimum des options"),
    min_oi: int = Query(default=50, description="Open Interest minimum"),
    max_dte: int = Query(default=30, description="DTE maximum"),
    min_whale_score: float = Query(default=60.0, description="Score whale minimum")
):
    """
    Pipeline complet: Short Interest → Filtrage → Screening Options
    
    1. Récupère les symboles avec short interest élevé
    2. Applique les filtres de marché  
    3. Lance le screening d'options avec ces symboles
    """
    start_time = datetime.now()
    
    try:
        logger.info("🚀 Début du pipeline Short Interest → Options Screening")
        
        # Étape 1: Récupérer les symboles avec short interest
        from data.short_interest_scraper import get_high_short_interest_symbols
        
        symbols = get_high_short_interest_symbols(
            enable_prefiltering=request.enable_prefiltering,
            min_market_cap=request.min_market_cap,
            min_avg_volume=request.min_avg_volume,
            exchange=request.exchange
        )
        
        if not symbols:
            return {
                "success": True,
                "message": "Aucun symbole avec short interest élevé trouvé",
                "symbols_found": 0,
                "opportunities": [],
                "execution_time_seconds": (datetime.now() - start_time).total_seconds()
            }
        
        logger.info(f"📋 {len(symbols)} symboles avec short interest élevé trouvés")
        
        # Étape 2: Screening des options sur ces symboles
        from services.hybrid_screening_service import HybridScreeningService
        
        screening_service = HybridScreeningService()
        
        screening_params = {
            "symbols": symbols,
            "min_volume": min_volume,
            "min_oi": min_oi,
            "max_dte": max_dte,
            "min_whale_score": min_whale_score
        }
        
        # Lancer le screening hybride
        screening_result = await screening_service.screen_options_hybrid(
            symbols=symbols,
            min_volume=min_volume,
            min_oi=min_oi, 
            max_dte=max_dte,
            min_whale_score=min_whale_score
        )
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"✅ Pipeline terminé: {len(screening_result.get('opportunities', []))} opportunités en {execution_time:.2f}s")
        
        return {
            "success": True,
            "timestamp": datetime.now(),
            "pipeline": "short_interest_to_options",
            "symbols_scanned": len(symbols),
            "short_interest_symbols": symbols[:10],  # Premiers 10 pour debug
            "opportunities": screening_result.get("opportunities", []),
            "opportunities_count": len(screening_result.get("opportunities", [])),
            "screening_params": screening_params,
            "execution_time_seconds": execution_time
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur dans le pipeline Short Interest → Options: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur pipeline: {str(e)}")

@short_interest_router.post("/scan-ai", response_model=Dict[str, Any])
async def scan_with_ai_classification(
    request: SymbolsRequest,
    min_volume: int = Query(default=100, description="Volume minimum des options"),
    min_oi: int = Query(default=50, description="Open Interest minimum"),
    max_dte: int = Query(default=30, description="DTE maximum"),
    min_whale_score: float = Query(default=60.0, description="Score whale minimum"),
    enable_ai_filter: bool = Query(default=True, description="Activer le filtrage IA"),
    min_ai_score: float = Query(default=70.0, description="Score IA minimum"),
    min_squeeze_probability: float = Query(default=60.0, description="Probabilité squeeze minimum")
):
    """
    Pipeline complet: Short Interest → Filtrage → Screening Options
    
    1. Récupère les symboles avec short interest élevé
    2. Applique les filtres de marché  
    3. Lance le screening d'options avec ces symboles
    """
    start_time = datetime.now()
    
    try:
        logger.info("🤖 Début du pipeline avancé: Short Interest → Options → Classification IA")
        
        # Étape 1: Récupérer les données Short Interest détaillées (pas juste les symboles)
        scraper = ShortInterestScraper()
        
        # Récupérer les données complètes avec enrichissement
        si_data_list = await scraper.get_high_short_interest_data(
            exchange=request.exchange,
            limit=50  # Limite pour l'IA
        )
        
        if not si_data_list:
            return {
                "success": True,
                "message": "Aucun symbole avec short interest élevé trouvé",
                "ai_analysis": False,
                "symbols_found": 0,
                "opportunities": [],
                "execution_time_seconds": (datetime.now() - start_time).total_seconds()
            }
        
        # Convertir en dict pour accès facile
        si_data_dict = {item['symbol']: item for item in si_data_list}
        symbols = list(si_data_dict.keys())
        
        logger.info(f"🎯 {len(symbols)} symboles avec données SI complètes récupérées")
        
        # Étape 2: Screening des options sur ces symboles
        from services.hybrid_screening_service import HybridScreeningService
        
        screening_service = HybridScreeningService()
        
        # Lancer le screening hybride
        screening_result = await screening_service.screen_options_hybrid(
            symbols=symbols,
            min_volume=min_volume,
            min_oi=min_oi, 
            max_dte=max_dte,
            min_whale_score=min_whale_score
        )
        
        opportunities = screening_result if isinstance(screening_result, list) else screening_result.get("opportunities", [])
        
        if not opportunities:
            return {
                "success": True,
                "message": "Aucune opportunité options trouvée sur les symboles SI",
                "ai_analysis": False,
                "symbols_scanned": len(symbols),
                "opportunities": [],
                "execution_time_seconds": (datetime.now() - start_time).total_seconds()
            }
        
        logger.info(f"📊 {len(opportunities)} opportunités options trouvées avant classification IA")
        
        # Étape 3: Classification IA des opportunités
        ai_classifier = AIShortInterestClassifier()
        
        logger.info("🤖 Début de la classification IA...")
        
        # Classifier toutes les opportunités avec l'IA
        ai_classified_opportunities = await ai_classifier.classify_short_interest_results(
            opportunities=opportunities,
            short_interest_stocks=si_data_dict
        )
        
        # Étape 4: Filtrage selon les critères IA (optionnel)
        final_opportunities = ai_classified_opportunities
        
        if enable_ai_filter and ai_classified_opportunities:
            logger.info(f"🔍 Filtrage IA activé: score≥{min_ai_score}, squeeze≥{min_squeeze_probability}%")
            
            filtered_opportunities = ai_classifier.filter_by_ai_criteria(
                opportunities=ai_classified_opportunities,
                min_ai_score=min_ai_score,
                min_squeeze_probability=min_squeeze_probability,
                allowed_strategies=['BUY_CALLS', 'SELL_PUTS', 'BUY_STRADDLE']
            )
            
            final_opportunities = filtered_opportunities
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Statistiques IA
        ai_stats = {
            "total_analyzed": len(opportunities),
            "ai_classified": len(ai_classified_opportunities),
            "final_filtered": len(final_opportunities),
            "ai_filter_enabled": enable_ai_filter
        }
        
        if ai_classified_opportunities:
            ai_scores = [opp.get('ai_score', 0) for opp in ai_classified_opportunities]
            squeeze_probs = [opp.get('ai_squeeze_probability', 0) for opp in ai_classified_opportunities]
            
            ai_stats.update({
                "avg_ai_score": sum(ai_scores) / len(ai_scores),
                "avg_squeeze_probability": sum(squeeze_probs) / len(squeeze_probs),
                "high_confidence_count": len([s for s in ai_scores if s >= 80]),
                "squeeze_candidates": len([p for p in squeeze_probs if p >= 70])
            })
        
        logger.info(f"✨ Pipeline IA terminé: {len(final_opportunities)} opportunités finales en {execution_time:.2f}s")
        
        return {
            "success": True,
            "timestamp": datetime.now(),
            "pipeline": "short_interest_to_options_ai",
            "ai_analysis": True,
            "symbols_scanned": len(symbols),
            "short_interest_data_available": len(si_data_dict),
            "opportunities": final_opportunities,
            "opportunities_count": len(final_opportunities),
            "ai_statistics": ai_stats,
            "screening_params": {
                "min_volume": min_volume,
                "min_oi": min_oi,
                "max_dte": max_dte,
                "min_whale_score": min_whale_score,
                "min_ai_score": min_ai_score,
                "min_squeeze_probability": min_squeeze_probability
            },
            "execution_time_seconds": execution_time
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur dans le pipeline IA Short Interest → Options: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur pipeline IA: {str(e)}")

# Route de test/santé
@short_interest_router.get("/test-ai")
async def test_ai_classification():
    """Test endpoint pour vérifier le fonctionnement de l'IA"""
    try:
        # Test simple avec données simulées
        test_option = {
            'symbol': 'TEST_240315C10',
            'underlying_symbol': 'TEST',
            'underlying_price': 12.50,
            'strike_price': 10.0,
            'option_type': 'call',
            'premium': 2.80,
            'volume': 1500,
            'open_interest': 800,
            'days_to_expiration': 15,
            'implied_volatility': 0.85,
            'delta': 0.75,
            'gamma': 0.08,
            'theta': -0.12,
            'vega': 0.22,
            'short_interest_percent': 45.2,
            'days_to_cover': 8.5,
            'float_shares': 15000000,
            'current_price': 12.50,
            'whale_score': 78.5,
            'hybrid_score': 82.1
        }
        
        # Test de classification IA
        classifier = AIShortInterestClassifier()
        ai_analysis = await classifier.classify_opportunity(
            test_option,
            {'short_interest_percent': 45.2, 'days_to_cover': 8.5}
        )
        
        return {
            'status': 'success',
            'message': 'IA test completed successfully',
            'test_option': test_option,
            'ai_analysis': ai_analysis
        }
        
    except Exception as e:
        logger.error(f"Erreur test IA: {str(e)}")
        return {
            'status': 'error',
            'message': f'Erreur lors du test IA: {str(e)}'
        }

@short_interest_router.get("/health")
async def health_check():
    """Vérification de santé du service short interest"""
    return {
        "service": "short-interest",
        "status": "healthy",
        "timestamp": datetime.now(),
        "endpoints": [
            "/api/short-interest/stocks",
            "/api/short-interest/symbols", 
            "/api/short-interest/scan",
            "/api/short-interest/scan-ai",
            "/api/short-interest/test-ai",
            "/api/short-interest/health"
        ]
    }
