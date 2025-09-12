# tradier_client.py
import requests
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from utils.config import Config


class TradierClient:
    def __init__(self):
        self.api_key = Config.TRADIER_API_KEY
        self.base_url = Config.TRADIER_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

    def get_option_expirations(self, symbol: str) -> List[str]:
        """Récupère les dates d'expiration disponibles"""
        url = f"{self.base_url}/markets/options/expirations"
        params = {"symbol": symbol}

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()

            if "expirations" in data and "date" in data["expirations"]:
                return data["expirations"]["date"]
            return []
        except Exception as e:
            print(f"Erreur récupération expirations {symbol}: {e}")
            return []

    def filter_expirations_by_dte(
        self, expirations: List[str], max_dte: int
    ) -> List[str]:
        """Filtre les expirations selon les DTE"""
        today = datetime.now().date()
        filtered = []

        for exp_str in expirations:
            try:
                exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
                dte = (exp_date - today).days

                if 0 < dte <= max_dte:
                    filtered.append(exp_str)
            except ValueError:
                continue

        return sorted(filtered)

    def get_option_chains(self, symbol: str, expiration: str) -> List[Dict]:
        """Récupère la chaîne d'options pour un symbole et expiration donnés"""
        url = f"{self.base_url}/markets/options/chains"
        params = {
            "symbol": symbol,
            "expiration": expiration,
            "greeks": "true",  # Inclure les Greeks pour Delta
        }

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()

            # Extrait les options de la réponse
            if "options" in data and "option" in data["options"]:
                return data["options"]["option"]
            return []

        except Exception as e:
            print(f"❌ Erreur chaîne {symbol} {expiration}: {e}")
            return []

    def get_historical_volume(self, option_symbols: List[str]) -> Dict[str, Dict]:
        """
        Récupère les volumes historiques (7 jours) pour les options
        Note: Tradier API peut ne pas avoir toutes les données historiques d'options
        """
        # Implémentation simplifiée - Tradier Time & Sales pour volume historique
        volumes = {}
        for symbol in option_symbols:
            volumes[symbol] = {
                "volume_1d": 0,  # Volume du jour (depuis l'API chains)
                "volume_7d": 0,  # Volume 7 jours (estimation ou API séparée)
            }
        return volumes

    def get_quote(self, symbols: List[str]) -> Dict:
        """Récupère les cotations pour une liste de symboles"""
        if not symbols:
            return {}

        url = f"{self.base_url}/markets/quotes"
        params = {"symbols": ",".join(symbols)}

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Erreur récupération quotes: {e}")
            return {}
