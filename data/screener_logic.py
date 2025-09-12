# screener_logic.py
from typing import List, Dict, Optional
from datetime import datetime
import asyncio
from models.option_model import OptionScreenerResult
from data.tradier_client import TradierClient
from data.async_tradier import AsyncTradierClient
from utils.config import Config
import streamlit as st


class OptionsScreener:
    def __init__(self, use_async: bool = True):
        self.config = Config()
        self.client = TradierClient()
        self.async_client = AsyncTradierClient(max_concurrent=8, rate_limit=0.08) if use_async else None
        self.use_async = use_async

    def calculate_whale_score(
        self,
        volume_1d: int,
        volume_7d: int,
        open_interest: int,
        delta: float,
        iv: float,
    ) -> float:
        """Score de probabilité de 'whale' basé sur plusieurs critères"""
        score = 0

        # Volume 1 jour score (0-25 points)
        if volume_1d > 5000:
            score += 25
        elif volume_1d > 2000:
            score += 20
        elif volume_1d > 1000:
            score += 15
        elif volume_1d > 500:
            score += 10

        # Volume 7 jours score (0-25 points)
        if volume_7d > 20000:
            score += 25
        elif volume_7d > 10000:
            score += 20
        elif volume_7d > 5000:
            score += 15

        # Ratio Volume/OI score (0-25 points)
        vol_oi_ratio = volume_1d / open_interest if open_interest > 0 else 0
        if vol_oi_ratio > 5:
            score += 25
        elif vol_oi_ratio > 3:
            score += 20
        elif vol_oi_ratio > 2:
            score += 15
        elif vol_oi_ratio > 1:
            score += 10

        # Delta score pour calls ITM/ATM (0-15 points)
        if delta > 0.4:
            score += 15
        elif delta > 0.3:
            score += 10
        elif delta > 0.2:
            score += 5

        # Implied Volatility score (0-10 points)
        if iv > 0.8:
            score += 10
        elif iv > 0.5:
            score += 7
        elif iv > 0.3:
            score += 5

        return min(score, 100)  # Cap à 100

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
                
            # Calculate whale score
            whale_score = self.calculate_whale_score(
                volume_1d=volume_1d,
                volume_7d=volume_7d,
                open_interest=open_interest,
                delta=abs(delta),
                iv=iv
            )
            
            # Check threshold
            if whale_score >= min_whale_score:
                return OptionScreenerResult(
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
        
        return sorted(all_results, key=lambda x: x.whale_score, reverse=True)
