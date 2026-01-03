# screener_logic.py
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import asyncio
import os
from models.option_model import OptionScreenerResult
from data.tradier_client import TradierClient
from data.async_tradier import AsyncTradierClient
from data.historical_data_manager import HistoricalDataManager
from utils.config import Config


class OptionsScreener:
    def __init__(self, use_async: bool = True, enable_historical: bool = True):
        self.config = Config()
        self.client = TradierClient()
        self.async_client = AsyncTradierClient(max_concurrent=8, rate_limit=0.08) if use_async else None
        self.use_async = use_async
        self.historical_manager = HistoricalDataManager() if enable_historical else None
        self.enable_historical = enable_historical

    def calculate_vol_oi_score(self, volume: int, open_interest: int) -> float:
        """Calculate Volume/Open Interest score based on Unusual Whales methodology"""
        if open_interest == 0:
            return 95.0  # Brand new contracts, very high score
        
        ratio = volume / open_interest
        
        # Scoring based on Unusual Whales examples
        if ratio >= 10.0:  # Like NVDA example (11.55 ratio)
            return 95.0
        elif ratio >= 5.0:
            return 85.0
        elif ratio >= 2.0:
            return 75.0
        elif ratio >= 1.0:  # Volume > OI threshold
            return 65.0
        else:
            return max(10.0, ratio * 50)  # Proportional score
    
    def calculate_large_block_score(self, volume: int, whale_threshold: int = 5000) -> float:
        """Detect large institutional blocks based on Unusual Whales methodology"""
        if volume >= 10000:  # Like MSFT examples
            return 95.0
        elif volume >= whale_threshold:
            # Progressive scoring for large blocks
            return min(95.0, 80.0 + (volume - whale_threshold) / 1000 * 3)
        else:
            return max(0, (volume / whale_threshold) * 50)
    
    def calculate_whale_score(
        self,
        volume_1d: int,
        volume_7d: int,
        open_interest: int,
        delta: float,
        iv: float,
    ) -> float:
        """Enhanced whale score using Unusual Whales methodology"""
        # Calculate individual component scores
        vol_oi_score = self.calculate_vol_oi_score(volume_1d, open_interest)
        block_score = self.calculate_large_block_score(volume_1d)
        
        # Legacy scoring components (preserved for continuity)
        legacy_score = 0
        
        # Volume 1 jour score (0-25 points)
        if volume_1d > 5000:
            legacy_score += 25
        elif volume_1d > 2000:
            legacy_score += 20
        elif volume_1d > 1000:
            legacy_score += 15
        elif volume_1d > 500:
            legacy_score += 10
        
        # Delta score pour calls ITM/ATM (0-15 points)
        if delta > 0.4:
            legacy_score += 15
        elif delta > 0.3:
            legacy_score += 10
        elif delta > 0.2:
            legacy_score += 5
        
        # Implied Volatility score (0-10 points)
        if iv > 0.8:
            legacy_score += 10
        elif iv > 0.5:
            legacy_score += 7
        elif iv > 0.3:
            legacy_score += 5
        
        # Composite score with Unusual Whales weighting
        composite_score = (
            legacy_score * 0.4 +      # Legacy logic (40%)
            vol_oi_score * 0.35 +     # Vol/OI ratio (35%) - very important per UW
            block_score * 0.25        # Large blocks (25%) - institutional detection
        )
        
        return min(100.0, composite_score)
    
    def calculate_whale_score_v3(
        self,
        volume_1d: int,
        volume_7d: int, 
        open_interest: int,
        delta: float,
        iv: float,
        option_symbol: str
    ) -> Tuple[float, Dict[str, any]]:
        """Enhanced whale score v3 with historical anomaly detection"""
        # Get base scores from v2
        base_score = self.calculate_whale_score(
            volume_1d, volume_7d, open_interest, delta, iv
        )
        
        # Historical anomaly scores
        volume_anomaly = 0.0
        oi_anomaly = 0.0
        historical_stats = {}
        
        if self.historical_manager:
            try:
                # Calculate volume anomaly vs historical average
                volume_anomaly, vol_stats = self.historical_manager.calculate_volume_anomaly(
                    current_volume=volume_1d,
                    option_symbol=option_symbol,
                    lookback_days=10
                )
                
                # Calculate OI anomaly vs historical average  
                oi_anomaly, oi_stats = self.historical_manager.calculate_oi_anomaly(
                    current_oi=open_interest,
                    option_symbol=option_symbol,
                    lookback_days=10
                )
                
                historical_stats = {
                    "volume_stats": vol_stats,
                    "oi_stats": oi_stats
                }
                
            except Exception as e:
                print(f"Historical analysis error for {option_symbol}: {e}")
        
        # Composite score v3 with historical weighting
        if volume_anomaly > 0 or oi_anomaly > 0:
            # Historical data available - use enhanced scoring
            enhanced_score = (
                base_score * 0.50 +         # Base UW logic (50%)
                volume_anomaly * 0.35 +     # Volume vs history (35%)
                oi_anomaly * 0.15           # OI vs history (15%)
            )
        else:
            # No historical data - fallback to base score
            enhanced_score = base_score
        
        scoring_details = {
            "base_score": base_score,
            "volume_anomaly": volume_anomaly,
            "oi_anomaly": oi_anomaly,
            "enhanced_score": enhanced_score,
            "has_historical_data": (volume_anomaly > 0 or oi_anomaly > 0),
            "historical_stats": historical_stats
        }
        
        return min(100.0, enhanced_score), scoring_details
    
    def get_vol_oi_ratio(self, volume: int, open_interest: int) -> float:
        """Calculate Volume/Open Interest ratio"""
        return volume / open_interest if open_interest > 0 else float('inf')
    
    def categorize_block_size(self, volume: int) -> str:
        """Categorize option volume into block sizes"""
        if volume >= 10000:
            return "🐋 Whale"
        elif volume >= 5000:
            return "🦑 Large"
        elif volume >= 2000:
            return "🐟 Medium"
        else:
            return "🦐 Small"
    
    def is_unusual_activity(self, vol_oi_ratio: float, volume: int) -> bool:
        """Determine if activity is unusual based on UW criteria"""
        return vol_oi_ratio >= 1.0 or volume >= 5000

    def _screen_options(
        self,
        symbols: List[str],
        option_type: str,
        max_dte: int = 7,
        min_volume: int = 1000,
        min_oi: int = 500,
        min_whale_score: float = 70,
    ) -> List[OptionScreenerResult]:
        """
        Screen générique pour détecter les big options buying

        Args:
            symbols: Liste des symboles à analyser
            option_type: 'call' ou 'put'
            max_dte: DTE maximum (défaut 7)
            min_volume: Volume minimum requis
            min_oi: Open Interest minimum
            min_whale_score: Score minimum pour être considéré comme whale
        """
        results = []

        for symbol in symbols:
            print(f"🔍 Analyse {symbol}...")

            # 1. Récupérer les expirations disponibles
            expirations = self.client.get_option_expirations(symbol)
            if not expirations:
                print(f"❌ Pas d'expirations pour {symbol}")
                continue

            # 2. Filtrer les expirations par DTE
            # Filtrer les expirations par DTE
            filtered_exps = self.client.filter_expirations_by_dte(expirations, max_dte)
            if not filtered_exps:
                print(f"❌ Pas d'expirations < {max_dte} DTE pour {symbol}")
                continue

            # 3. Pour chaque expiration, analyser les options
            print(f"📅 Analyse de {len(filtered_exps)} expirations...")

            for expiration in filtered_exps:
                try:
                    # Récupérer les chaînes d'options
                    chain_data = self.client.get_option_chains(symbol, expiration)
                    if not chain_data:
                        continue

                    # Filtrer par type d'option (call/put)
                    options = [
                        opt
                        for opt in chain_data
                        if (
                            opt["option_type"].lower() == option_type
                            and opt["volume"] >= min_volume
                            and opt["open_interest"] >= min_oi
                        )
                    ]

                except Exception as e:
                    print(f"❌ Erreur: {symbol} exp. {expiration} - {str(e)}")
                    continue

                # 4. Analyser chaque option
                for opt in options:
                    try:
                        # Vérifier données requises
                        required_fields = [
                            "volume",
                            "open_interest",
                            "symbol",
                            "expiration_date",
                            "strike",
                        ]
                        if not all(field in opt for field in required_fields):
                            symbol_str = opt.get("symbol", "?")
                            print(f"❌ Données manquantes: {symbol_str}")
                            continue

                        # Extraire métriques avec validation
                        volume_1d = int(opt["volume"])
                        open_interest = int(opt["open_interest"])
                        volume_7d = volume_1d * 7  # TODO: Vraie donnée 7j
                        strike = float(opt["strike"])

                        # Traiter les Greeks avec précaution
                        greeks = opt.get("greeks", {}) or {}
                        try:
                            delta = float(greeks.get("delta", 0.3))
                            iv = float(greeks.get("mid_iv", 0.4))
                        except (ValueError, TypeError):
                            delta = 0.3
                            iv = 0.4

                        # Calculer whale score
                        whale_score = self.calculate_whale_score(
                            volume_1d=volume_1d,
                            volume_7d=volume_7d,
                            open_interest=open_interest,
                            delta=abs(delta),  # Valeur absolue pour les puts
                            iv=iv,
                        )

                        # Vérifier si au-dessus du seuil
                        if whale_score >= min_whale_score:
                            result = OptionScreenerResult(
                                symbol=symbol,
                                option_symbol=opt["symbol"],
                                expiration=opt["expiration_date"],
                                strike=strike,
                                side=option_type,
                                delta=delta,
                                volume_1d=volume_1d,
                                volume_7d=volume_7d,
                                open_interest=open_interest,
                                last_price=float(opt.get("last", 0.0)),
                                bid=float(opt.get("bid", 0.0)),
                                ask=float(opt.get("ask", 0.0)),
                                implied_volatility=iv,
                                whale_score=whale_score,
                                dte=int(
                                    (
                                        datetime.strptime(
                                            opt["expiration_date"], "%Y-%m-%d"
                                        )
                                        - datetime.now()
                                    ).days
                                ),
                            )
                            results.append(result)
                            score_msg = (
                                f"✅ {result.option_symbol} "
                                f"Score: {whale_score:.0f}"
                            )
                            print(score_msg)

                    except Exception as e:
                        option_info = {
                            "symbol": opt.get("symbol", "N/A"),
                            "type": opt.get("option_type", "N/A"),
                            "data": opt,
                        }
                        print(f"❌ Erreur traitement option: {str(e)}")
                        print(f"🔍 Détails option en erreur: {option_info}")
                        continue

        return results

    def screen_big_calls(
        self,
        symbols: List[str],
        max_dte: int = 7,
        min_volume: int = 1000,
        min_oi: int = 500,
        min_whale_score: float = 70,
    ) -> List[OptionScreenerResult]:
        """Screen principal pour détecter les big call buying"""
        return self._screen_options(
            symbols=symbols,
            option_type="call",
            max_dte=max_dte,
            min_volume=min_volume,
            min_oi=min_oi,
            min_whale_score=min_whale_score,
        )

    def screen_big_puts(
        self,
        symbols: List[str],
        max_dte: int = 7,
        min_volume: int = 1000,
        min_oi: int = 500,
        min_whale_score: float = 70,
    ) -> List[OptionScreenerResult]:
        """Screen principal pour détecter les big put buying"""
        return self._screen_options(
            symbols=symbols,
            option_type="put",
            max_dte=max_dte,
            min_volume=min_volume,
            min_oi=min_oi,
            min_whale_score=min_whale_score,
        )
    
    async def close_async(self):
        """Clean up async resources"""
        if self.async_client:
            await self.async_client.close()
    
    async def _async_screen_symbol(
        self, 
        symbol: str, 
        option_type: str, 
        max_dte: int, 
        min_volume: int, 
        min_oi: int, 
        min_whale_score: float
    ) -> List[OptionScreenerResult]:
        """Async version for single symbol screening"""
        results = []
        
        try:
            # Get expirations
            expirations = self.client.get_option_expirations(symbol)
            if not expirations:
                return results
                
            # Filter by DTE
            filtered_exps = self.client.filter_expirations_by_dte(expirations, max_dte)
            if not filtered_exps:
                return results
                
            # Process each expiration
            for expiration in filtered_exps:
                try:
                    chain_data = self.client.get_option_chains(symbol, expiration)
                    if not chain_data:
                        continue
                        
                    # Filter options
                    options = [
                        opt for opt in chain_data
                        if (opt["option_type"].lower() == option_type
                            and opt["volume"] >= min_volume
                            and opt["open_interest"] >= min_oi)
                    ]
                    
                    # Process each qualifying option
                    for opt in options:
                        try:
                            result = self._process_option(
                                opt, symbol, option_type, min_whale_score
                            )
                            if result:
                                results.append(result)
                        except Exception as e:
                            print(f"Error processing option: {e}")
                            continue
                            
                except Exception as e:
                    print(f"Error processing expiration {expiration}: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error screening symbol {symbol}: {e}")
            
        return results
    
    def _process_option(
        self, 
        opt: Dict, 
        symbol: str, 
        option_type: str, 
        min_whale_score: float
    ) -> Optional[OptionScreenerResult]:
        """Process individual option data into OptionScreenerResult"""
        try:
            # Extract basic metrics
            volume_1d = int(opt["volume"])
            open_interest = int(opt["open_interest"])
            volume_7d = volume_1d * 7  # TODO: Get real 7-day data
            strike = float(opt["strike"])
            
            # Handle Greeks safely
            greeks = opt.get("greeks", {}) or {}
            try:
                delta = float(greeks.get("delta", 0.3))
                iv = float(greeks.get("mid_iv", 0.4))
            except (ValueError, TypeError):
                delta = 0.3
                iv = 0.4
                
            # Use enhanced whale score v3 with historical data
            if self.enable_historical:
                whale_score, scoring_details = self.calculate_whale_score_v3(
                    volume_1d=volume_1d,
                    volume_7d=volume_7d,
                    open_interest=open_interest,
                    delta=abs(delta),
                    iv=iv,
                    option_symbol=opt["symbol"]
                )
            else:
                # Fallback to v2 scoring
                whale_score = self.calculate_whale_score(
                    volume_1d=volume_1d,
                    volume_7d=volume_7d,
                    open_interest=open_interest,
                    delta=abs(delta),
                    iv=iv
                )
                scoring_details = {"enhanced_score": whale_score, "has_historical_data": False}
            
            # Calculate additional metrics
            vol_oi_ratio = self.get_vol_oi_ratio(volume_1d, open_interest)
            
            # Apply basic Unusual Whales filters (configurable via Config class)
            # These can be configured via environment variables or config files
            min_vol_oi = float(os.getenv('MIN_VOL_OI_RATIO', '0.0'))
            min_whale_block = int(os.getenv('MIN_WHALE_BLOCK', '0'))
            filter_new_only = os.getenv('FILTER_NEW_POSITIONS_ONLY', 'false').lower() == 'true'
            
            # Apply Vol/OI filter
            if vol_oi_ratio < min_vol_oi:
                return None
            
            # Apply whale block filter
            if volume_1d < min_whale_block:
                return None
            
            # Apply new positions filter
            if filter_new_only and vol_oi_ratio < 1.0:
                return None
            
            # Check threshold
            if whale_score >= min_whale_score:
                result = OptionScreenerResult(
                    symbol=symbol,
                    option_symbol=opt["symbol"],
                    expiration=opt["expiration_date"],
                    strike=strike,
                    side=option_type,
                    delta=delta,
                    volume_1d=volume_1d,
                    volume_7d=volume_7d,
                    open_interest=open_interest,
                    last_price=float(opt.get("last", 0.0)),
                    bid=float(opt.get("bid", 0.0)),
                    ask=float(opt.get("ask", 0.0)),
                    implied_volatility=iv,
                    whale_score=whale_score,
                    dte=int(
                        (datetime.strptime(opt["expiration_date"], "%Y-%m-%d") - 
                         datetime.now()).days
                    )
                )
                
                # Set historical context if available
                if self.enable_historical and scoring_details.get('has_historical_data', False):
                    vol_stats = scoring_details.get('historical_stats', {}).get('volume_stats', {})
                    oi_stats = scoring_details.get('historical_stats', {}).get('oi_stats', {})
                    
                    volume_ratio = vol_stats.get('volume_ratio')
                    oi_ratio = oi_stats.get('oi_ratio')
                    
                    result.set_historical_context(volume_ratio, oi_ratio)
                
                return result
                
        except Exception as e:
            print(f"Error processing option data: {e}")
            
        return None
    
    async def screen_async(
        self,
        symbols: List[str],
        option_type: str,
        max_dte: int = 7,
        min_volume: int = 1000,
        min_oi: int = 500,
        min_whale_score: float = 70,
        progress_callback: Optional[callable] = None
    ) -> List[OptionScreenerResult]:
        """Optimized async screening for large symbol lists"""
        if not symbols or not self.use_async:
            # Fallback to sync method
            return self._screen_options(
                symbols, option_type, max_dte, min_volume, min_oi, min_whale_score
            )
        
        all_results = []
        
        # Process in batches to manage memory and API limits
        batch_size = 10
        total_batches = (len(symbols) + batch_size - 1) // batch_size
        
        for batch_idx in range(0, len(symbols), batch_size):
            batch_symbols = symbols[batch_idx:batch_idx + batch_size]
            
            # Update progress
            if progress_callback:
                progress = (batch_idx // batch_size + 1) / total_batches
                progress_callback(progress, f"Processing batch {batch_idx//batch_size + 1}/{total_batches}")
            
            # Create async tasks for the batch
            tasks = [
                self._async_screen_symbol(
                    symbol, option_type, max_dte, min_volume, min_oi, min_whale_score
                ) for symbol in batch_symbols
            ]
            
            try:
                # Execute batch with timeout
                batch_results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=60  # 60 second timeout per batch
                )
                
                # Collect results, handling exceptions
                for symbol, result in zip(batch_symbols, batch_results):
                    if isinstance(result, list):
                        all_results.extend(result)
                    elif isinstance(result, Exception):
                        print(f"Error screening {symbol}: {result}")
                        
            except asyncio.TimeoutError:
                print(f"Timeout processing batch {batch_idx//batch_size + 1}")
                continue
            except Exception as e:
                print(f"Error processing batch: {e}")
                continue
        
        # Save results to historical database for future anomaly detection
        if self.historical_manager and all_results:
            try:
                saved_count = self.historical_manager.save_scan_results(all_results)
                print(f"💾 Saved {saved_count} results to historical database")
            except Exception as e:
                print(f"Error saving to historical database: {e}")
        
        return sorted(all_results, key=lambda x: x.whale_score, reverse=True)
    
    def get_historical_stats(self) -> Dict[str, any]:
        """Get historical database statistics"""
        if not self.historical_manager:
            return {"enabled": False}
        
        try:
            stats = self.historical_manager.get_database_stats()
            stats["enabled"] = True
            return stats
        except Exception as e:
            return {"enabled": False, "error": str(e)}
    
    def cleanup_historical_data(self, days_to_keep: int = 30) -> int:
        """Clean up old historical data"""
        if not self.historical_manager:
            return 0
        
        return self.historical_manager.cleanup_old_data(days_to_keep)
