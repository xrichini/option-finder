# config.py
import os
import logging

logger = logging.getLogger(__name__)


class Config:
    """Configuration helpers.

    Avoid reading environment variables at import time. Use getters so
    that tests and runtime configuration can override env vars before
    access.
    """

    # Screening defaults / parameters
    DEFAULT_DTE: int = 7
    MAX_DTE: int = 45

    # Production parameters
    MIN_VOLUME_THRESHOLD_PROD: int = 1000
    MIN_OPEN_INTEREST_THRESHOLD_PROD: int = 1000
    VOLUME_OI_RATIO_THRESHOLD_PROD: float = 2.0
    MIN_WHALE_SCORE_PROD: int = 70

    # Sandbox parameters
    MIN_VOLUME_THRESHOLD_SANDBOX: int = 10
    MIN_OPEN_INTEREST_THRESHOLD_SANDBOX: int = 1
    VOLUME_OI_RATIO_THRESHOLD_SANDBOX: float = 1.0
    MIN_WHALE_SCORE_SANDBOX: int = 30

    DEFAULT_SHORT_INTEREST_THRESHOLD: float = 30.0

    ENABLE_ASYNC_SCREENING: bool = True
    MAX_CONCURRENT_REQUESTS: int = 10
    API_RATE_LIMIT: float = 0.1
    BATCH_SIZE_SYMBOLS: int = 20
    BATCH_SIZE_OPTIONS: int = 50
    REQUEST_TIMEOUT: int = 30

    ENABLE_PREFILTERING: bool = True
    MIN_MARKET_CAP: int = 100_000_000
    MIN_STOCK_VOLUME: int = 500_000
    CACHE_TTL_MARKET_DATA: int = 1800
    CACHE_TTL_OPTIONABLE: int = 3600

    EXCLUDED_SECTORS = [
        "Real Estate Investment Trusts",
        "Asset Management",
    ]

    @staticmethod
    def _get_env(key: str, default: str = "") -> str:
        return os.getenv(key, default)

    @classmethod
    def is_sandbox(cls) -> bool:
        return cls._get_env("TRADIER_SANDBOX", "false").lower() == "true"

    @classmethod
    def is_development_mode(cls) -> bool:
        """Alias for is_sandbox() for backward compatibility"""
        return cls.is_sandbox()

    @classmethod
    def get_openai_api_key(cls) -> str:
        return cls._get_env("OPENAI_API_KEY", "")

    @classmethod
    def get_perplexity_api_key(cls) -> str:
        return cls._get_env("PERPLEXITY_API_KEY", "")

    @classmethod
    def get_polygon_api_key(cls) -> str:
        return cls._get_env("POLYGON_API_KEY", "")

    @classmethod
    def get_tradier_api_key(cls) -> str:
        """Return the appropriate Tradier API key depending on sandbox flag."""
        if cls.is_sandbox():
            return (
                cls._get_env("TRADIER_API_KEY_SANDBOX")
                or cls._get_env("TRADIER_API_KEY_PRODUCTION")
                or cls._get_env("TRADIER_API_KEY")
            )
        return cls._get_env("TRADIER_API_KEY_PRODUCTION") or cls._get_env(
            "TRADIER_API_KEY"
        )

    @classmethod
    def get_tradier_environment(cls) -> str:
        return "sandbox" if cls.is_sandbox() else "production"

    @classmethod
    def get_tradier_base_url(cls) -> str:
        if cls.is_sandbox():
            return "https://sandbox.tradier.com/v1"
        return "https://api.tradier.com/v1"

    @classmethod
    def has_ai_capabilities(cls) -> bool:
        return bool(
            cls.get_openai_api_key() or cls.get_perplexity_api_key()
        )

    @classmethod
    def get_min_volume_threshold(cls) -> int:
        return (
            cls.MIN_VOLUME_THRESHOLD_SANDBOX
            if cls.is_sandbox()
            else cls.MIN_VOLUME_THRESHOLD_PROD
        )

    @classmethod
    def get_min_open_interest_threshold(cls) -> int:
        return (
            cls.MIN_OPEN_INTEREST_THRESHOLD_SANDBOX
            if cls.is_sandbox()
            else cls.MIN_OPEN_INTEREST_THRESHOLD_PROD
        )

    @classmethod
    def get_volume_oi_ratio_threshold(cls) -> float:
        return (
            cls.VOLUME_OI_RATIO_THRESHOLD_SANDBOX
            if cls.is_sandbox()
            else cls.VOLUME_OI_RATIO_THRESHOLD_PROD
        )

    @classmethod
    def get_min_whale_score(cls) -> int:
        return (
            cls.MIN_WHALE_SCORE_SANDBOX
            if cls.is_sandbox()
            else cls.MIN_WHALE_SCORE_PROD
        )

    @classmethod
    def get_screening_parameters(cls) -> dict:
        return {
            "min_volume_threshold": cls.get_min_volume_threshold(),
            "min_open_interest_threshold": (
                cls.get_min_open_interest_threshold()
            ),
            "volume_oi_ratio_threshold": (
                cls.get_volume_oi_ratio_threshold()
            ),
            "min_whale_score": cls.get_min_whale_score(),
            "environment": cls.get_tradier_environment(),
            "is_sandbox": cls.is_sandbox(),
        }

    @classmethod
    def validate(cls, strict: bool = False) -> bool:
        """Validate presence of critical configuration.

        If `strict` is True and critical keys are missing, this will return
        False (caller may choose to exit). Otherwise it will log warnings
        and return False if essential keys are missing.
        """
        ok = True

        tradier_key = cls.get_tradier_api_key()
        if not tradier_key:
            logger.warning(
                "Tradier API key not configured. Set "
                "TRADIER_API_KEY_PRODUCTION or TRADIER_API_KEY_SANDBOX"
            )
            ok = False

        # Optional but useful keys
        if not cls.get_openai_api_key() and (
            not cls.get_perplexity_api_key()
        ):
            logger.info(
                "No AI API keys configured "
                "(OPENAI_API_KEY or PERPLEXITY_API_KEY)"
            )

        if strict and not ok:
            logger.error(
                "Config validation failed (strict mode). "
                "Exiting would be recommended."
            )

        return ok
