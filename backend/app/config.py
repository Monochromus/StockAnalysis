from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "CommodityCockpit"
    debug: bool = False

    # API Settings
    api_v1_prefix: str = "/api/v1"

    # CORS Settings
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
    ]

    # Data Provider Settings
    cache_ttl_seconds: int = 300  # 5 minutes
    default_period: str = "1y"
    default_interval: str = "1d"
    min_data_points: int = 10  # Reduced to allow short periods like 1mo

    # Provider API Keys
    alpha_vantage_api_key: Optional[str] = None
    twelve_data_api_key: Optional[str] = None

    # Provider Settings
    default_data_provider: str = "auto"  # "auto", "yfinance", "alpha_vantage", "twelve_data"
    enable_provider_fallback: bool = True
    intraday_cache_ttl_seconds: int = 60  # Shorter TTL for intraday data

    # ZigZag Settings
    zigzag_threshold_percent: float = 5.0

    # Retry Settings
    max_retries: int = 3
    retry_delay_seconds: float = 1.0

    # Gemini API Settings (for News Dashboard)
    gemini_api_key: Optional[str] = None
    news_cache_ttl_seconds: int = 14400  # 4 hours
    news_cache_db_path: str = "data/news_cache.db"

    # COT (Commitments of Traders) Settings
    cot_cache_ttl_seconds: int = 86400  # 24 hours
    cot_cache_db_path: str = "data/cot_cache.db"
    cot_lookback_weeks: int = 52  # Default lookback for COT Index
    cot_app_token: Optional[str] = None  # Optional Socrata API token

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
