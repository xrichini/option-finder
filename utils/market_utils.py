"""
Utilitaires d'enrichissement - Secteur & Sizzle Index

Sizzle Index (Unusual Whales) :
    volume_today / avg_volume_30d
    > 2.0  → activité notable
    > 5.0  → activité très inhabituelle
"""

from __future__ import annotations

import sqlite3
import os
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Secteur par symbole (principaux tickers US + ETFs)
# ---------------------------------------------------------------------------
SECTOR_MAP: Dict[str, str] = {
    # Technology
    "AAPL": "Technology",
    "MSFT": "Technology",
    "GOOGL": "Technology",
    "GOOG": "Technology",
    "META": "Technology",
    "NVDA": "Technology",
    "AMD": "Technology",
    "INTC": "Technology",
    "TSMC": "Technology",
    "AVGO": "Technology",
    "QCOM": "Technology",
    "TXN": "Technology",
    "MU": "Technology",
    "AMAT": "Technology",
    "LRCX": "Technology",
    "KLAC": "Technology",
    "MRVL": "Technology",
    "SNPS": "Technology",
    "CDNS": "Technology",
    "FTNT": "Technology",
    "PANW": "Technology",
    "CRWD": "Technology",
    "ZS": "Technology",
    "OKTA": "Technology",
    "DDOG": "Technology",
    "NET": "Technology",
    "SNOW": "Technology",
    "PLTR": "Technology",
    "ORCL": "Technology",
    "CRM": "Technology",
    "SAP": "Technology",
    "NOW": "Technology",
    "ADBE": "Technology",
    "INTU": "Technology",
    "IBM": "Technology",
    "HPQ": "Technology",
    "DELL": "Technology",
    "WDC": "Technology",
    "STX": "Technology",
    "SMCI": "Technology",
    # Consumer Technology
    "AMZN": "Consumer Technology",
    "NFLX": "Consumer Technology",
    "SPOT": "Consumer Technology",
    "PINS": "Consumer Technology",
    "SNAP": "Consumer Technology",
    "TWTR": "Consumer Technology",
    "LYFT": "Consumer Technology",
    "UBER": "Consumer Technology",
    "DASH": "Consumer Technology",
    "BYND": "Consumer",
    "ABNB": "Consumer Technology",
    # Finance
    "JPM": "Finance",
    "GS": "Finance",
    "MS": "Finance",
    "BAC": "Finance",
    "WFC": "Finance",
    "C": "Finance",
    "USB": "Finance",
    "PNC": "Finance",
    "AXP": "Finance",
    "V": "Finance",
    "MA": "Finance",
    "PYPL": "Finance",
    "SQ": "Finance",
    "COIN": "Finance",
    "HOOD": "Finance",
    "BX": "Finance",
    "KKR": "Finance",
    "APO": "Finance",
    # Healthcare & Biotech
    "JNJ": "Healthcare",
    "PFE": "Healthcare",
    "MRNA": "Healthcare",
    "ABBV": "Healthcare",
    "BMY": "Healthcare",
    "MRK": "Healthcare",
    "AMGN": "Healthcare",
    "GILD": "Healthcare",
    "UNH": "Healthcare",
    "CVS": "Healthcare",
    "LLY": "Healthcare",
    "BSX": "Healthcare",
    "ISRG": "Healthcare",
    "VRTX": "Healthcare",
    "REGN": "Healthcare",
    "BIIB": "Healthcare",
    # Energy
    "XOM": "Energy",
    "CVX": "Energy",
    "COP": "Energy",
    "EOG": "Energy",
    "SLB": "Energy",
    "OXY": "Energy",
    "PSX": "Energy",
    "MPC": "Energy",
    "VLO": "Energy",
    # Consumer
    "WMT": "Consumer",
    "COST": "Consumer",
    "TGT": "Consumer",
    "HD": "Consumer",
    "LOW": "Consumer",
    "MCD": "Consumer",
    "SBUX": "Consumer",
    "NKE": "Consumer",
    "TSLA": "Consumer",
    "F": "Consumer",
    "GM": "Consumer",
    "RIVN": "Consumer",
    "LCID": "Consumer",
    "TM": "Consumer",
    # Industrials
    "BA": "Industrials",
    "CAT": "Industrials",
    "GE": "Industrials",
    "MMM": "Industrials",
    "HON": "Industrials",
    "LMT": "Industrials",
    "RTX": "Industrials",
    "NOC": "Industrials",
    "DE": "Industrials",
    "UPS": "Industrials",
    "FDX": "Industrials",
    # Real Estate / REIT
    "SPG": "Real Estate",
    "AMT": "Real Estate",
    "PLD": "Real Estate",
    "DLR": "Real Estate",
    # Materials
    "NEM": "Materials",
    "FCX": "Materials",
    "AA": "Materials",
    "CLF": "Materials",
    # Telecom
    "T": "Telecom",
    "VZ": "Telecom",
    "TMUS": "Telecom",
    # ETFs
    "SPY": "ETF",
    "QQQ": "ETF",
    "IWM": "ETF",
    "DIA": "ETF",
    "VIX": "ETF",
    "GLD": "ETF",
    "SLV": "ETF",
    "TLT": "ETF",
    "HYG": "ETF",
    "LQD": "ETF",
    "XLF": "ETF",
    "XLK": "ETF",
    "XLV": "ETF",
    "XLE": "ETF",
    "XLI": "ETF",
    "XLC": "ETF",
    "XLY": "ETF",
    "XLP": "ETF",
    "XLRE": "ETF",
    "XLU": "ETF",
    "GDX": "ETF",
    "GDXJ": "ETF",
    "ARKK": "ETF",
    "SQQQ": "ETF",
    "TQQQ": "ETF",
    "SPXU": "ETF",
    "UVXY": "ETF",
    "VXX": "ETF",
    "IBIT": "ETF",
    "FBTC": "ETF",
    # Crypto-related
    "MSTR": "Technology",
    "MARA": "Technology",
    "RIOT": "Technology",
    "CLSK": "Technology",
    # PATH
    "PATH": "Technology",
    "WMB": "Energy",
}


def get_sector(symbol: str) -> str:
    """Retourne le secteur du symbole. Fallback = 'Other'."""
    return SECTOR_MAP.get(symbol.upper(), "Other")


# ---------------------------------------------------------------------------
# Sizzle Index  (via options_history.db)
# ---------------------------------------------------------------------------
_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "options_history.db")
_DB_PATH = os.path.normpath(_DB_PATH)


def compute_sizzle_index(
    option_symbol: str,
    current_volume: int,
    window_days: int = 30,
) -> float:
    """
    Sizzle Index = current_volume / avg_volume_{window_days}d

    Utilise options_history.db si disponible, sinon retourne 0.0
    (le score whale classique prend le relais).
    """
    if not os.path.exists(_DB_PATH):
        return 0.0
    if current_volume <= 0:
        return 0.0

    try:
        cutoff = (datetime.now() - timedelta(days=window_days)).strftime("%Y-%m-%d")
        con = sqlite3.connect(_DB_PATH)
        try:
            row = con.execute(
                """
                SELECT AVG(volume)
                FROM option_history
                WHERE symbol = ?
                  AND date >= ?
                  AND volume > 0
                """,
                (option_symbol, cutoff),
            ).fetchone()
        finally:
            con.close()

        avg_vol = row[0] if row and row[0] else None
        if avg_vol and avg_vol > 0:
            return round(current_volume / avg_vol, 2)
        return 0.0

    except Exception as e:
        logger.debug(
            f"Impossible de calculer le Sizzle Index pour {option_symbol}: {e}"
        )
        return 0.0


def compute_moneyness(
    option_type: str, strike: float, underlying_price: float
) -> tuple[str, float]:
    """
    Retourne (label, pct_distance) :
      label = 'ITM' | 'OTM' | 'ATM'
      pct_distance = % distance du strike au spot (positif = plus loin OTM)
    """
    if underlying_price <= 0:
        return "", 0.0

    pct = ((strike - underlying_price) / underlying_price) * 100

    if option_type.lower() == "call":
        label = (
            "ITM" if underlying_price > strike else ("ATM" if abs(pct) < 1 else "OTM")
        )
        dist = -pct  # positif = ITM pour une call
    else:
        label = (
            "ITM" if underlying_price < strike else ("ATM" if abs(pct) < 1 else "OTM")
        )
        dist = pct  # positif = ITM pour une put

    return label, round(pct, 2)
