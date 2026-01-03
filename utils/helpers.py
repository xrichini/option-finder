# helpers.py
from datetime import datetime
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
import asyncio
import nest_asyncio
from data.async_tradier import AsyncTradierClient
import yfinance as yf
import logging

logger = logging.getLogger(__name__)


def get_market_data_batch(symbols: List[str]) -> Dict[str, Dict]:
    """Get basic market data for filtering before expensive API calls"""
    if not symbols:
        return {}

    market_data = {}
    batch_size = 50  # yfinance can handle larger batches

    for i in range(0, len(symbols), batch_size):
        batch = symbols[i : i + batch_size]
        try:
            # Use yfinance for quick market data
            tickers = yf.Tickers(" ".join(batch))

            for symbol in batch:
                try:
                    ticker = tickers.tickers[symbol]
                    info = ticker.info
                    hist = ticker.history(period="5d")

                    if not hist.empty and info:
                        market_data[symbol] = {
                            "market_cap": info.get("marketCap", 0),
                            "avg_volume": info.get("averageVolume", 0),
                            "price": info.get(
                                "currentPrice",
                                hist["Close"].iloc[-1] if len(hist) > 0 else 0,
                            ),
                            "sector": info.get("sector", "Unknown"),
                            "volume_5d": hist["Volume"].mean() if len(hist) > 0 else 0,
                        }
                except Exception:
                    # If individual symbol fails, continue but log for debugging
                    logger.exception("Error fetching market data for symbol %s", symbol)
                    continue
        except Exception:
            logger.exception("Batch market data error")
            continue

    return market_data


def filter_symbols_by_market_criteria(
    symbols: List[str],
    min_market_cap: int = 100_000_000,  # 100M min market cap
    min_avg_volume: int = 500_000,  # 500K average volume
    excluded_sectors: List[str] = None,
) -> List[str]:
    """Pre-filter symbols by market criteria to reduce API calls"""
    if excluded_sectors is None:
        excluded_sectors = ["Real Estate Investment Trusts"]

    if not symbols:
        return []

    # Get market data
    market_data = get_market_data_batch(symbols)

    filtered_symbols = []
    for symbol in symbols:
        if symbol not in market_data:
            # If no data, include it (might be new or special case)
            filtered_symbols.append(symbol)
            continue

        data = market_data[symbol]

        # Apply filters
        if (
            data.get("market_cap", 0) >= min_market_cap
            and data.get("avg_volume", 0) >= min_avg_volume
            and data.get("sector") not in excluded_sectors
        ):
            filtered_symbols.append(symbol)

    return filtered_symbols


def get_high_short_interest_symbols(
    enable_prefiltering: bool = True,
    min_market_cap: int = 100_000_000,
    min_avg_volume: int = 500_000,
) -> List[str]:
    """Enhanced version with smart pre-filtering"""
    nest_asyncio.apply()
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0) Chrome/91.0"}

    try:
        logger.info("📡 Récupération des symboles...")
        url = "https://www.highshortinterest.com/"
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        main_table = soup.find("table", {"class": "stocks"}) or soup.find("table")

        if not main_table:
            logger.warning("Aucun tableau trouvé sur la page")
            return []

        # Extract symbols with short interest data if available
        symbols_data = []
        for row in main_table.select("tr")[1:]:
            cols = row.select("td")
            if cols and len(cols) >= 2:
                symbol = cols[0].get_text(strip=True)
                if symbol.isalpha():
                    short_interest = (
                        cols[1].get_text(strip=True) if len(cols) > 1 else "N/A"
                    )
                    symbols_data.append((symbol, short_interest))

        initial_symbols = sorted([s[0] for s in symbols_data])
        logger.info("%d symboles trouvés", len(initial_symbols))

        # Apply market-based pre-filtering
        if enable_prefiltering and initial_symbols:
            logger.info("🔍 Pré-filtrage par critères de marché...")
            filtered_symbols = filter_symbols_by_market_criteria(
                initial_symbols,
                min_market_cap=min_market_cap,
                min_avg_volume=min_avg_volume,
            )
            logger.info(
                "%d symboles après pré-filtrage (%d exclus)",
                len(filtered_symbols),
                len(initial_symbols) - len(filtered_symbols),
            )
        else:
            filtered_symbols = initial_symbols

        # Final optionable check
        logger.info("🔍 Vérification des options disponibles...")
        client = AsyncTradierClient(max_concurrent=15, rate_limit=0.05)

        async def filter_symbols():
            try:
                result = await client.filter_optionable_symbols(filtered_symbols)
                return result
            except Exception:
                logger.exception("Exception in filter_symbols")
                return []
            finally:
                await client.close()

        try:
            optionable_symbols = asyncio.run(filter_symbols())
        except Exception:
            logger.exception("Exception in asyncio.run during optionable check")
            # Fallback: return filtered symbols without optionable check
            logger.warning(
                "Skipping optionable check due to error, returning all filtered symbols"
            )
            return filtered_symbols

        if optionable_symbols:
            pass  # Success - symbols found
        else:
            # Return filtered symbols even if option check failed
            return filtered_symbols

        return optionable_symbols

    except requests.RequestException:
        logger.exception("Erreur réseau lors de la récupération des symboles")
        return []
    except Exception:
        logger.exception("Erreur inattendue dans get_high_short_interest_symbols")
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
    except Exception:
        logger.exception("Erreur en calculant DTE pour %s", expiration_date)
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
