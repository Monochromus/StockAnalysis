"""Data provider manager - main entry point for fetching market data."""
from __future__ import annotations

from functools import lru_cache
from typing import List, Optional, Tuple

from app.config import get_settings

from .base import BaseProvider, ProviderMetadata, FetchResult
from .selector import ProviderSelector
from .yfinance_provider import YFinanceProvider
from .alpha_vantage_provider import AlphaVantageProvider
from .twelve_data_provider import TwelveDataProvider

from app.schemas import OHLCVData


class DataProviderManager:
    """
    Main entry point for fetching market data from multiple providers.

    Handles provider selection, fallback logic, and metadata tracking.
    """

    def __init__(self):
        self.settings = get_settings()

        # Initialize all providers
        self._providers: List[BaseProvider] = [
            YFinanceProvider(),
            AlphaVantageProvider(),
            TwelveDataProvider(),
        ]

        self._selector = ProviderSelector(self._providers)

        # Default provider preference from settings
        default_pref = getattr(self.settings, 'default_data_provider', 'auto')
        self._default_preference = None if default_pref == 'auto' else default_pref

        # Whether to enable fallback to other providers
        self._enable_fallback = getattr(self.settings, 'enable_provider_fallback', True)

    async def get_ohlcv(
        self,
        symbol: str,
        period: Optional[str] = None,
        interval: Optional[str] = None,
        user_preference: Optional[str] = None,
    ) -> Tuple[OHLCVData, ProviderMetadata]:
        """
        Fetch OHLCV data using the best available provider.

        Args:
            symbol: Ticker symbol
            period: Data period (e.g., "1y", "3mo")
            interval: Data interval (e.g., "1d", "1h", "5m")
            user_preference: Optional provider name to prefer

        Returns:
            Tuple of (OHLCVData, ProviderMetadata)

        Raises:
            DataProviderError: If all providers fail
        """
        from app.core.exceptions import DataProviderError

        period = period or self.settings.default_period
        interval = interval or self.settings.default_interval

        # Determine provider preference
        preference = user_preference or self._default_preference

        # Get ordered list of providers to try
        providers = self._selector.select(interval, preference)

        if not providers:
            raise DataProviderError(
                f"No providers available for interval '{interval}'"
            )

        # Try providers in order
        errors = []
        for provider in providers:
            result = await provider.fetch_ohlcv(symbol, period, interval)

            if result.success:
                metadata = ProviderMetadata(
                    provider_name=provider.info.name,
                    provider_display_name=provider.info.display_name,
                    from_cache=result.from_cache,
                    fetch_time_ms=result.fetch_time_ms,
                )
                return result.data, metadata

            # Record error and try next provider
            errors.append(f"{provider.info.name}: {result.error}")

            # If fallback is disabled, stop after first failure
            if not self._enable_fallback:
                break

        # All providers failed
        error_summary = "; ".join(errors)
        raise DataProviderError(f"All providers failed: {error_summary}")

    def get_providers_status(self) -> List[dict]:
        """
        Get status of all available providers.

        Returns list of dicts with provider info and availability.
        """
        status = []

        for provider in self._providers:
            info = provider.info
            rate_info = {}

            # Get rate limit info if available
            if hasattr(provider, '_rate_limiter'):
                rate_info = provider._rate_limiter.get_remaining()

            status.append({
                "name": info.name,
                "display_name": info.display_name,
                "available": provider.is_available(),
                "requires_api_key": info.requires_api_key,
                "capabilities": [c.name.lower() for c in info.capabilities],
                "priority": info.priority,
                "rate_limits": {
                    "per_minute": info.rate_limit_per_minute,
                    "per_day": info.rate_limit_per_day,
                    **rate_info,
                },
            })

        return status

    def get_provider_by_name(self, name: str) -> Optional[BaseProvider]:
        """Get a specific provider by name."""
        return self._selector.get_provider_by_name(name)


@lru_cache
def get_provider_manager() -> DataProviderManager:
    """Get singleton instance of DataProviderManager."""
    return DataProviderManager()
