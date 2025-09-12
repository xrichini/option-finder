# helpers.py
import streamlit as st
from datetime import datetime
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
import asyncio
import nest_asyncio
from data.async_tradier import AsyncTradierClient


def get_high_short_interest_symbols() -> List[str]:
    """Récupère et filtre les symboles avec options de highshortinterest.com"""
    # Nécessaire pour exécuter asyncio dans Streamlit
    nest_asyncio.apply()

    # User agent header simplifié
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0) Chrome/91.0"}

    try:
        with st.spinner("📡 Récupération des symboles..."):
            # Récupération et parsing de la page
            url = "https://www.highshortinterest.com/"
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            main_table = soup.find("table", {"class": "stocks"}) or soup.find("table")

            if not main_table:
                st.error("❌ Aucun tableau trouvé sur la page")
                return []

            # Extrait et nettoie les symboles
            symbols = {
                cols[0].get_text(strip=True)
                for row in main_table.select("tr")[1:]
                if (cols := row.select("td")) and cols[0].get_text(strip=True).isalpha()
            }
            initial_symbols = sorted(symbols)

        # Filtrage asynchrone des symboles avec options
        with st.spinner("🔍 Vérification des options disponibles..."):
            client = AsyncTradierClient()

            async def filter_symbols():
                return await client.filter_optionable_symbols(initial_symbols)

            # Exécute le filtrage asynchrone
            optionable_symbols = asyncio.run(filter_symbols())

            # Affiche uniquement le résultat final
            if optionable_symbols:
                st.success(
                    f"✅ {len(optionable_symbols)} symboles avec options "
                    f"sur {len(initial_symbols)} total"
                )

            return optionable_symbols

    except requests.RequestException as e:
        st.error(f"❌ Erreur réseau: {str(e)}")
        return []
    except Exception as e:
        st.error(f"❌ Erreur inattendue: {str(e)}")
        return []


def format_large_number(num: int) -> str:
    """Formate les grands nombres avec des suffixes"""
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    else:
        return str(num)


def calculate_dte(expiration_date: str) -> int:
    """Calcule les days to expiration"""
    try:
        exp_date = datetime.strptime(expiration_date, "%Y-%m-%d").date()
        return (exp_date - datetime.now().date()).days
    except Exception as e:
        return 0


def format_percentage(value: float) -> str:
    """Formate un pourcentage"""
    return f"{value:.1f}%"


def get_whale_score_emoji(score: float) -> str:
    """Retourne un emoji basé sur le whale score"""
    if score >= 90:
        return "🐋"
    elif score >= 80:
        return "🦈"
    elif score >= 70:
        return "🐟"
    else:
        return "🐠"
