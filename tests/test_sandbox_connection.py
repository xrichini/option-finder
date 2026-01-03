#!/usr/bin/env python3

import sys
import os

sys.path.insert(0, os.getcwd())

from utils.config import Config
import requests
import logging

logger = logging.getLogger(__name__)


def main():
    print("🔑 Test connexion sandbox...")

    api_key = Config.get_tradier_api_key()
    base_url = Config.get_tradier_base_url()

    print(f"URL: {base_url}")
    print(f"Key configured: {bool(api_key)}")
    if api_key:
        logger.debug("Key is configured (hidden)")
    else:
        print("❌ Aucune clé API configurée!")
        return

    # Test simple endpoint
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}

    # Test quotes endpoint
    url = f"{base_url}/markets/quotes"
    params = {"symbols": "SPY"}

    print(f"\nTest endpoint quotes: {url}")
    try:
        response = requests.get(url, headers=headers, params=params)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Connexion sandbox OK!")
            data = response.json()
            print(f"Data preview: {str(data)[:100]}...")
        else:
            print(f"❌ Erreur: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
    except Exception:
        logger.exception("Exception calling quotes endpoint")

    # Test options expirations endpoint
    print("\nTest endpoint options expirations...")
    url2 = f"{base_url}/markets/options/expirations"
    params2 = {"symbol": "SPY"}

    try:
        response2 = requests.get(url2, headers=headers, params=params2)
        print(f"Status: {response2.status_code}")
        if response2.status_code == 200:
            print("✅ Options endpoint OK!")
            data2 = response2.json()
            print(f"Expirations preview: {str(data2)[:100]}...")
        else:
            print(f"❌ Erreur: {response2.status_code}")
            print(f"Response: {response2.text[:200]}...")
    except Exception:
        logger.exception("Exception calling options expirations endpoint")


if __name__ == "__main__":
    main()
