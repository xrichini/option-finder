# enhanced_screener.py
import asyncio
from typing import List, Dict, Optional
from data.screener_logic import OptionsScreener
from data.ai_analysis_manager import AIAnalysisManager
from models.option_model import OptionScreenerResult
from utils.config import Config

class EnhancedOptionsScreener:
    """Enhanced Options Screener with AI analysis capabilities"""
    
    def __init__(self, enable_ai: bool = None, enable_market_chameleon: bool = True):
        self.base_screener = OptionsScreener()
        self.ai_enabled = enable_ai if enable_ai is not None else Config.has_ai_capabilities()
        self.ai_manager = AIAnalysisManager() if self.ai_enabled else None
        
        # Initialize Market Chameleon integration
        self.mc_enabled = enable_market_chameleon
        self.mc_enhancer = None
        
        if enable_market_chameleon:
            try:
                from data.market_chameleon_scraper import MarketChameleonEnhancer
                self.mc_enhancer = MarketChameleonEnhancer()
                print("✅ Market Chameleon integration enabled")
            except ImportError as e:
                print(f"⚠️ Market Chameleon not available: {e}")
                self.mc_enabled = False
        
    async def screen_with_ai_analysis(
        self,
        symbols: List[str],
        option_type: str,
        max_dte: int = 7,
        min_volume: int = 1000,
        min_oi: int = 500,
        min_whale_score: float = 70,
        enable_ai_for_top_n: int = 5,
        progress_callback: Optional[callable] = None
    ) -> List[OptionScreenerResult]:
        """
        Screen options with AI enhancement for top results
        
        Args:
            symbols: List of symbols to screen
            option_type: 'call' or 'put'
            max_dte: Maximum days to expiration
            min_volume: Minimum volume threshold
            min_oi: Minimum open interest
            min_whale_score: Minimum whale score
            enable_ai_for_top_n: Number of top results to enhance with AI
            progress_callback: Progress callback function
        
        Returns:
            List of OptionScreenerResult with AI analysis for top results
        """
        if progress_callback:
            progress_callback(0.1, "Starting options screening...")
        
        # Step 1: Run base screening
        try:
            if self.base_screener.use_async:
                results = await self.base_screener.screen_async(
                    symbols=symbols,
                    option_type=option_type,
                    max_dte=max_dte,
                    min_volume=min_volume,
                    min_oi=min_oi,
                    min_whale_score=min_whale_score,
                    progress_callback=lambda p, msg: progress_callback(0.1 + p * 0.6, msg) if progress_callback else None
                )
            else:
                if option_type == 'call':
                    results = self.base_screener.screen_big_calls(
                        symbols, max_dte, min_volume, min_oi, min_whale_score
                    )
                else:
                    results = self.base_screener.screen_big_puts(
                        symbols, max_dte, min_volume, min_oi, min_whale_score
                    )
        except Exception as e:
            print(f"Error in base screening: {e}")
            return []
        
        if progress_callback:
            progress_callback(0.7, f"Found {len(results)} options. Running AI analysis...")
        
        # Step 2: Market Chameleon enhancement
        if self.mc_enabled and self.mc_enhancer and results:
            if progress_callback:
                progress_callback(0.75, "Enhancing with Market Chameleon data...")
            try:
                results = self.mc_enhancer.enhance_screening_results(results, use_mc_data=True)
            except Exception as e:
                print(f"Error enhancing with Market Chameleon: {e}")
        
        # Step 3: AI analysis for top results
        if self.ai_enabled and self.ai_manager and results and enable_ai_for_top_n > 0:
            await self._enhance_with_ai_analysis(results[:enable_ai_for_top_n], progress_callback)
        
        if progress_callback:
            progress_callback(1.0, "Analysis complete!")
        
        return results
    
    async def _enhance_with_ai_analysis(
        self, 
        results: List[OptionScreenerResult], 
        progress_callback: Optional[callable] = None
    ):
        """Enhance top results with AI analysis"""
        if not self.ai_manager:
            return
        
        # Group results by ticker to avoid duplicate AI calls
        ticker_groups = {}
        for result in results:
            if result.symbol not in ticker_groups:
                ticker_groups[result.symbol] = []
            ticker_groups[result.symbol].append(result)
        
        total_tickers = len(ticker_groups)
        processed = 0
        
        # Process each unique ticker
        for ticker, ticker_results in ticker_groups.items():
            try:
                if progress_callback:
                    progress_callback(
                        0.7 + (processed / total_tickers) * 0.3,
                        f"AI analyzing {ticker}..."
                    )
                
                # Use the best (highest whale score) option for this ticker for AI analysis
                best_option = max(ticker_results, key=lambda x: x.whale_score)
                
                # Prepare option data for AI analysis
                option_data = {
                    'whale_score': best_option.whale_score,
                    'vol_oi_ratio': best_option.vol_oi_ratio,
                    'volume_1d': best_option.volume_1d,
                    'open_interest': best_option.open_interest,
                    'strike': best_option.strike,
                    'expiration': best_option.expiration,
                    'side': best_option.side,
                    'dte': best_option.dte
                }
                
                # Run comprehensive AI analysis
                ai_results = await self.ai_manager.comprehensive_analysis(ticker, option_data)
                
                # Apply AI results to all options for this ticker
                for result in ticker_results:
                    result.set_ai_analysis(ai_results)
                
                processed += 1
                
                # Add small delay to respect API rate limits
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"Error in AI analysis for {ticker}: {e}")
                continue
    
    async def generate_portfolio_strategy(
        self, 
        results: List[OptionScreenerResult],
        market_conditions: Dict = None
    ) -> Optional[Dict]:
        """Generate overall portfolio strategy using AI"""
        if not self.ai_enabled or not self.ai_manager or not results:
            return None
        
        try:
            strategy_analysis = await self.ai_manager.analyze_options_strategy(
                results[:10],  # Use top 10 results
                market_conditions
            )
            
            return {
                'strategy_summary': strategy_analysis.summary,
                'confidence': strategy_analysis.confidence_score,
                'recommendations': strategy_analysis.recommendations,
                'risk_factors': strategy_analysis.risk_factors,
                'detailed_analysis': strategy_analysis.detailed_analysis,
                'timestamp': strategy_analysis.timestamp
            }
            
        except Exception as e:
            print(f"Error generating portfolio strategy: {e}")
            return None
    
    def get_ai_capabilities_status(self) -> Dict[str, bool]:
        """Get status of AI capabilities"""
        return {
            'ai_enabled': self.ai_enabled,
            'openai_available': bool(Config.get_openai_api_key()),
            'perplexity_available': bool(Config.get_perplexity_api_key()),
            'has_ai_manager': self.ai_manager is not None,
            'market_chameleon_enabled': self.mc_enabled,
            'market_chameleon_available': self.mc_enhancer is not None
        }
    
    async def close(self):
        """Clean up resources"""
        if self.base_screener:
            await self.base_screener.close_async()