# config.py
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    TRADIER_API_KEY = os.getenv('TRADIER_API_KEY')
    TRADIER_BASE_URL = 'https://api.tradier.com/v1'
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')

    # Paramètres de screening configurables
    DEFAULT_DTE = 7  # Days To Expiration par défaut
    MAX_DTE = 45    # DTE maximum
    MIN_VOLUME_THRESHOLD = 1000
    MIN_OPEN_INTEREST_THRESHOLD = 500
    VOLUME_OI_RATIO_THRESHOLD = 2.0
    DEFAULT_SHORT_INTEREST_THRESHOLD = 30.0  # % par défaut
    MIN_WHALE_SCORE = 70  # Score minimum pour détecter une baleine
