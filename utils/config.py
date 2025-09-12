# config.py
import streamlit as st


class Config:
    TRADIER_API_KEY = st.secrets.get("TRADIER_API_KEY")
    TRADIER_BASE_URL = "https://api.tradier.com/v1"
    OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY")
    PERPLEXITY_API_KEY = st.secrets.get("PERPLEXITY_API_KEY")

    # Options screening parameters
    DEFAULT_DTE = 7  # Days To Expiration par défaut
    MAX_DTE = 45  # DTE maximum
    MIN_VOLUME_THRESHOLD = 1000
    MIN_OPEN_INTEREST_THRESHOLD = 1000
    VOLUME_OI_RATIO_THRESHOLD = 2.0
    DEFAULT_SHORT_INTEREST_THRESHOLD = 30.0  # % par défaut
    MIN_WHALE_SCORE = 70  # Score minimum pour détecter une baleine
    
    # Performance optimization parameters
    ENABLE_ASYNC_SCREENING = True
    MAX_CONCURRENT_REQUESTS = 10
    API_RATE_LIMIT = 0.1  # seconds between requests
    BATCH_SIZE_SYMBOLS = 20  # symbols per batch for async processing
    BATCH_SIZE_OPTIONS = 50  # options per batch for quote requests
    REQUEST_TIMEOUT = 30  # seconds
    
    # Pre-filtering parameters
    ENABLE_PREFILTERING = True
    MIN_MARKET_CAP = 100_000_000  # 100M minimum market cap
    MIN_STOCK_VOLUME = 500_000    # 500K minimum average volume
    CACHE_TTL_MARKET_DATA = 1800  # 30 minutes
    CACHE_TTL_OPTIONABLE = 3600   # 1 hour
    
    # Excluded sectors for pre-filtering
    EXCLUDED_SECTORS = [
        'Real Estate Investment Trusts',
        'Asset Management',
    ]
