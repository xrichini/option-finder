# async_tradier.py
import requests
import asyncio
import aiohttp
from typing import Dict, List, Set
from datetime import datetime, timedelta
from utils.config import Config
from functools import lru_cache
import streamlit as st


class AsyncTradierClient:
    def __init__(self):
        self.api_key = Config.TRADIER_API_KEY
        self.base_url = Config.TRADIER_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }
        self._session = None
        self._optionable_cache = {}

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession(headers=self.headers)
        return self._session

    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None

    @st.cache_data(ttl=3600)  # Cache pour 1 heure
    def is_optionable(self, symbol: str) -> bool:
        """Vérifie si un symbole a des options (version synchrone, mise en cache)"""
        if symbol in self._optionable_cache:
            return self._optionable_cache[symbol]

        url = f"{self.base_url}/markets/options/expirations"
        params = {"symbol": symbol}

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()

            has_options = bool(data.get("expirations", {}).get("date", []))
            self._optionable_cache[symbol] = has_options
            return has_options
        except:
            return False

    async def async_is_optionable(self, symbol: str) -> bool:
        """Version asynchrone de is_optionable"""
        if symbol in self._optionable_cache:
            return self._optionable_cache[symbol]

        session = await self._get_session()
        url = f"{self.base_url}/markets/options/expirations"
        params = {"symbol": symbol}

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    has_options = bool(data.get("expirations", {}).get("date", []))
                    self._optionable_cache[symbol] = has_options
                    return has_options
                return False
        except:
            return False

    async def filter_optionable_symbols(self, symbols: List[str]) -> List[str]:
        """Filtre une liste de symboles pour ne garder que ceux avec options"""
        tasks = [self.async_is_optionable(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks)

        # Combine les résultats avec les symboles d'origine
        optionable = [sym for sym, has_opt in zip(symbols, results) if has_opt]
        return sorted(optionable)

    def sync_filter_optionable_symbols(self, symbols: List[str]) -> List[str]:
        """Version synchrone du filtre (pour compatibilité)"""
        return [sym for sym in symbols if self.is_optionable(sym)]
