# async_tradier.py
import requests
import asyncio
import aiohttp
from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime, timedelta
from utils.config import Config
from functools import lru_cache
import streamlit as st
import json
import os
from pathlib import Path
import time
from dataclasses import dataclass


@dataclass
class CacheEntry:
    data: any
    timestamp: float
    ttl: int = 3600  # 1 hour default
    
    def is_expired(self) -> bool:
        return time.time() - self.timestamp > self.ttl


class AsyncTradierClient:
    def __init__(self, max_concurrent: int = 10, rate_limit: float = 0.1):
        self.api_key = Config.TRADIER_API_KEY or st.session_state.get('temp_api_key')
        self.base_url = Config.TRADIER_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }
        self._session = None
        self._semaphore = None  # Will be created when needed
        self._rate_limit = rate_limit
        self._last_request_time = 0
        self._max_concurrent = max_concurrent
        self._closed = False
        
        # Enhanced caching with persistence
        self._cache_dir = Path("data/.cache")
        self._cache_dir.mkdir(exist_ok=True)
        self._cache: Dict[str, CacheEntry] = {}
        self._load_persistent_cache()

    def _load_persistent_cache(self):
        """Load persistent cache from disk"""
        cache_file = self._cache_dir / "optionable_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                for key, value in cache_data.items():
                    entry = CacheEntry(
                        data=value['data'],
                        timestamp=value['timestamp'],
                        ttl=value.get('ttl', 3600)
                    )
                    if not entry.is_expired():
                        self._cache[key] = entry
            except Exception as e:
                print(f"Warning: Could not load cache: {e}")
    
    def _save_persistent_cache(self):
        """Save cache to disk"""
        cache_file = self._cache_dir / "optionable_cache.json"
        cache_data = {}
        for key, entry in self._cache.items():
            if not entry.is_expired():
                cache_data[key] = {
                    'data': entry.data,
                    'timestamp': entry.timestamp,
                    'ttl': entry.ttl
                }
        
        try:
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)
        except Exception as e:
            print(f"Warning: Could not save cache: {e}")

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            if self._closed:
                raise RuntimeError("AsyncTradierClient has been closed")
                
            # Create semaphore when needed (avoids loop issues at init)
            if self._semaphore is None:
                self._semaphore = asyncio.Semaphore(self._max_concurrent)
                
            connector = aiohttp.TCPConnector(
                limit=20, 
                limit_per_host=10,
                enable_cleanup_closed=True,
                force_close=True
            )
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self._session = aiohttp.ClientSession(
                headers=self.headers,
                connector=connector,
                timeout=timeout
            )
        return self._session

    async def close(self):
        """Close the client and clean up resources"""
        self._closed = True
        if self._session and not self._session.closed:
            try:
                await self._session.close()
                # Wait a bit for the session to fully close
                await asyncio.sleep(0.1)
            except Exception as e:
                print(f"Warning: Error closing aiohttp session: {e}")
            finally:
                self._session = None
        self._save_persistent_cache()
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        if hasattr(self, '_session') and self._session and not self._session.closed:
            try:
                # Try to close gracefully in destructor
                loop = None
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(self._session.close())
                except RuntimeError:
                    # Can't do much if no event loop
                    pass
            except Exception:
                pass
    
    async def _rate_limited_request(self, method: str, url: str, max_retries: int = 3, **kwargs):
        """Make rate-limited HTTP request with retry logic and better error handling"""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self._max_concurrent)
            
        async with self._semaphore:
            for attempt in range(max_retries):
                try:
                    # Rate limiting
                    current_time = time.time()
                    time_since_last = current_time - self._last_request_time
                    if time_since_last < self._rate_limit:
                        await asyncio.sleep(self._rate_limit - time_since_last)
                    
                    session = await self._get_session()
                    self._last_request_time = time.time()
                    
                    async with getattr(session, method.lower())(url, **kwargs) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 429:  # Rate limited
                            retry_after = int(response.headers.get('Retry-After', 1))
                            await asyncio.sleep(min(retry_after, 5))  # Cap at 5 seconds
                            continue  # Retry this request
                        elif response.status in [502, 503, 504]:  # Temporary server errors
                            if attempt < max_retries - 1:
                                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                                continue
                            else:
                                print(f"Server error {response.status} for {url} after {max_retries} attempts")
                                return None
                        else:
                            print(f"HTTP {response.status} for {url}")
                            return None
                            
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    if attempt < max_retries - 1:
                        print(f"Request failed (attempt {attempt + 1}/{max_retries}): {str(e)[:100]}...")
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    else:
                        print(f"Final request failure for {url}: {e}")
                        return None
                except Exception as e:
                    print(f"Unexpected error for {url}: {e}")
                    return None
            
            return None  # All retries exhausted

    def _get_cached_or_store(self, key: str, data: any, ttl: int = 3600) -> any:
        """Get from cache or store new data"""
        if key in self._cache and not self._cache[key].is_expired():
            return self._cache[key].data
        
        if data is not None:
            self._cache[key] = CacheEntry(data=data, timestamp=time.time(), ttl=ttl)
        return data
    
    def is_optionable_sync(self, symbol: str) -> bool:
        """Synchronous version - check cache first"""
        cache_key = f"optionable_{symbol}"
        cached = self._get_cached_or_store(cache_key, None)
        if cached is not None:
            return cached
        
        # Fallback to sync request if not cached
        url = f"{self.base_url}/markets/options/expirations"
        params = {"symbol": symbol}

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()

            has_options = bool(data.get("expirations", {}).get("date", []))
            return self._get_cached_or_store(cache_key, has_options)
        except:
            return self._get_cached_or_store(cache_key, False)

    async def async_is_optionable(self, symbol: str) -> bool:
        """Async version with caching and rate limiting"""
        cache_key = f"optionable_{symbol}"
        cached = self._get_cached_or_store(cache_key, None)
        if cached is not None:
            return cached

        url = f"{self.base_url}/markets/options/expirations"
        params = {"symbol": symbol}
        
        data = await self._rate_limited_request('GET', url, params=params)
        if data:
            has_options = bool(data.get("expirations", {}).get("date", []))
            return self._get_cached_or_store(cache_key, has_options)
        
        return self._get_cached_or_store(cache_key, False)

    async def filter_optionable_symbols(self, symbols: List[str]) -> List[str]:
        """Filter symbols with batch processing and progress tracking"""
        if not symbols:
            return []
        
        # Check cache first for all symbols
        cached_results = {}
        uncached_symbols = []
        
        for symbol in symbols:
            cache_key = f"optionable_{symbol}"
            if cache_key in self._cache and not self._cache[cache_key].is_expired():
                cached_results[symbol] = self._cache[cache_key].data
            else:
                uncached_symbols.append(symbol)
        
        # Process uncached symbols in batches
        batch_size = 20
        optionable = list(cached_results.keys()) if any(cached_results.values()) else []
        
        for i in range(0, len(uncached_symbols), batch_size):
            batch = uncached_symbols[i:i + batch_size]
            tasks = [self.async_is_optionable(symbol) for symbol in batch]
            
            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for symbol, result in zip(batch, results):
                    if isinstance(result, bool) and result:
                        optionable.append(symbol)
            except Exception as e:
                print(f"Batch processing error: {e}")
        
        return sorted(optionable)

    async def get_quotes_batch(self, symbols: List[str]) -> Dict[str, Dict]:
        """Get quotes for multiple symbols efficiently"""
        if not symbols:
            return {}
        
        # Split into batches to respect API limits
        batch_size = 50
        all_quotes = {}
        
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            url = f"{self.base_url}/markets/quotes"
            params = {"symbols": ",".join(batch)}
            
            data = await self._rate_limited_request('GET', url, params=params)
            if data and "quotes" in data:
                quotes = data["quotes"]
                if isinstance(quotes, dict):  # Single quote
                    all_quotes[quotes["symbol"]] = quotes
                elif isinstance(quotes, list):  # Multiple quotes
                    for quote in quotes:
                        all_quotes[quote["symbol"]] = quote
        
        return all_quotes
    
    def sync_filter_optionable_symbols(self, symbols: List[str]) -> List[str]:
        """Synchronous version using cached data where possible"""
        return [sym for sym in symbols if self.is_optionable_sync(sym)]
