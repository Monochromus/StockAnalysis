"""Multi-provider data infrastructure."""
from .base import (
    BaseProvider,
    ProviderInfo,
    ProviderCapability,
    FetchResult,
    ProviderMetadata,
    is_intraday_interval,
)
from .rate_limiter import RateLimiter
from .selector import ProviderSelector
from .manager import DataProviderManager, get_provider_manager
from .yfinance_provider import YFinanceProvider
from .alpha_vantage_provider import AlphaVantageProvider
from .twelve_data_provider import TwelveDataProvider

__all__ = [
    # Base classes
    "BaseProvider",
    "ProviderInfo",
    "ProviderCapability",
    "FetchResult",
    "ProviderMetadata",
    "is_intraday_interval",
    # Utilities
    "RateLimiter",
    "ProviderSelector",
    # Manager
    "DataProviderManager",
    "get_provider_manager",
    # Providers
    "YFinanceProvider",
    "AlphaVantageProvider",
    "TwelveDataProvider",
]
