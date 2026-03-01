"""TTL-based cache for Prophet models and forecasts."""

from typing import Dict, Optional, Any
from cachetools import TTLCache
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CachedForecast:
    """Cached forecast data with metadata."""

    symbol: str
    period: str
    interval: str
    forecasts: Dict[str, Any]  # All forecast results
    created_at: datetime
    forecast_periods: int


class ProphetCache:
    """
    In-memory cache for Prophet forecasts.

    Caches complete forecast results by symbol to avoid recomputation.
    Cache has a TTL of 1 hour and max 50 forecasts.
    """

    def __init__(self, maxsize: int = 50, ttl: int = 3600):
        """
        Initialize cache.

        Args:
            maxsize: Maximum number of forecasts to cache
            ttl: Time-to-live in seconds (default 1 hour)
        """
        self._cache: TTLCache = TTLCache(maxsize=maxsize, ttl=ttl)

    def _make_key(self, symbol: str, period: str, interval: str) -> str:
        """Generate cache key from symbol and data parameters."""
        return f"{symbol.upper()}:{period}:{interval}"

    def get(
        self,
        symbol: str,
        period: str,
        interval: str
    ) -> Optional[CachedForecast]:
        """
        Get cached forecast.

        Args:
            symbol: Ticker symbol
            period: Data period (e.g., "5y")
            interval: Data interval (e.g., "1d")

        Returns:
            CachedForecast if exists, None otherwise
        """
        key = self._make_key(symbol, period, interval)
        return self._cache.get(key)

    def set(
        self,
        symbol: str,
        period: str,
        interval: str,
        forecasts: Dict[str, Any],
        forecast_periods: int
    ) -> None:
        """
        Cache forecast results.

        Args:
            symbol: Ticker symbol
            period: Data period
            interval: Data interval
            forecasts: All forecast results
            forecast_periods: Number of forecast periods
        """
        key = self._make_key(symbol, period, interval)

        cached = CachedForecast(
            symbol=symbol.upper(),
            period=period,
            interval=interval,
            forecasts=forecasts,
            created_at=datetime.utcnow(),
            forecast_periods=forecast_periods,
        )

        self._cache[key] = cached

    def invalidate(self, symbol: str, period: str, interval: str) -> bool:
        """
        Remove a forecast from cache.

        Args:
            symbol: Ticker symbol
            period: Data period
            interval: Data interval

        Returns:
            True if forecast was in cache and removed
        """
        key = self._make_key(symbol, period, interval)
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def invalidate_symbol(self, symbol: str) -> int:
        """
        Remove all cached forecasts for a symbol.

        Args:
            symbol: Ticker symbol

        Returns:
            Number of entries removed
        """
        symbol_upper = symbol.upper()
        keys_to_remove = [
            key for key in self._cache.keys()
            if key.startswith(f"{symbol_upper}:")
        ]

        for key in keys_to_remove:
            del self._cache[key]

        return len(keys_to_remove)

    def clear(self) -> None:
        """Clear all cached forecasts."""
        self._cache.clear()

    @property
    def size(self) -> int:
        """Return number of cached forecasts."""
        return len(self._cache)

    def has(self, symbol: str, period: str, interval: str) -> bool:
        """Check if a forecast is cached."""
        key = self._make_key(symbol, period, interval)
        return key in self._cache


# Singleton instance
_prophet_cache: Optional[ProphetCache] = None


def get_prophet_cache() -> ProphetCache:
    """Get the singleton Prophet cache instance."""
    global _prophet_cache
    if _prophet_cache is None:
        _prophet_cache = ProphetCache()
    return _prophet_cache
