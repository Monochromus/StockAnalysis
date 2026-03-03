"""TTL-based cache for XGBoost models and predictions."""

from typing import Dict, Optional, Any
from cachetools import TTLCache
from dataclasses import dataclass
from datetime import datetime

from .xgboost_model import XGBoostResidualCorrector, HybridForecastResult


@dataclass
class CachedXGBoostResult:
    """Cached XGBoost result data with metadata."""

    symbol: str
    period: str
    interval: str
    model: XGBoostResidualCorrector
    result: HybridForecastResult
    created_at: datetime


class XGBoostCache:
    """
    In-memory cache for XGBoost models and predictions.

    Caches trained models and their predictions by symbol.
    Cache has a TTL of 1 hour and max 30 entries.
    """

    def __init__(self, maxsize: int = 30, ttl: int = 3600):
        """
        Initialize cache.

        Args:
            maxsize: Maximum number of models to cache
            ttl: Time-to-live in seconds (default 1 hour)
        """
        self._cache: TTLCache = TTLCache(maxsize=maxsize, ttl=ttl)

    def _make_key(self, symbol: str, period: str, interval: str) -> str:
        """Generate cache key from symbol and data parameters."""
        return f"xgb:{symbol.upper()}:{period}:{interval}"

    def get(
        self,
        symbol: str,
        period: str,
        interval: str
    ) -> Optional[CachedXGBoostResult]:
        """
        Get cached XGBoost result.

        Args:
            symbol: Ticker symbol
            period: Data period (e.g., "5y")
            interval: Data interval (e.g., "1d")

        Returns:
            CachedXGBoostResult if exists, None otherwise
        """
        key = self._make_key(symbol, period, interval)
        return self._cache.get(key)

    def set(
        self,
        symbol: str,
        period: str,
        interval: str,
        model: XGBoostResidualCorrector,
        result: HybridForecastResult
    ) -> None:
        """
        Cache XGBoost model and result.

        Args:
            symbol: Ticker symbol
            period: Data period
            interval: Data interval
            model: Trained XGBoost model
            result: Hybrid forecast result
        """
        key = self._make_key(symbol, period, interval)

        cached = CachedXGBoostResult(
            symbol=symbol.upper(),
            period=period,
            interval=interval,
            model=model,
            result=result,
            created_at=datetime.utcnow(),
        )

        self._cache[key] = cached

    def invalidate(self, symbol: str, period: str, interval: str) -> bool:
        """
        Remove a result from cache.

        Args:
            symbol: Ticker symbol
            period: Data period
            interval: Data interval

        Returns:
            True if result was in cache and removed
        """
        key = self._make_key(symbol, period, interval)
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def invalidate_symbol(self, symbol: str) -> int:
        """
        Remove all cached results for a symbol.

        Args:
            symbol: Ticker symbol

        Returns:
            Number of entries removed
        """
        symbol_upper = symbol.upper()
        keys_to_remove = [
            key for key in self._cache.keys()
            if key.startswith(f"xgb:{symbol_upper}:")
        ]

        for key in keys_to_remove:
            del self._cache[key]

        return len(keys_to_remove)

    def clear(self) -> None:
        """Clear all cached results."""
        self._cache.clear()

    @property
    def size(self) -> int:
        """Return number of cached results."""
        return len(self._cache)

    def has(self, symbol: str, period: str, interval: str) -> bool:
        """Check if a result is cached."""
        key = self._make_key(symbol, period, interval)
        return key in self._cache


# Singleton instance
_xgboost_cache: Optional[XGBoostCache] = None


def get_xgboost_cache() -> XGBoostCache:
    """Get the singleton XGBoost cache instance."""
    global _xgboost_cache
    if _xgboost_cache is None:
        _xgboost_cache = XGBoostCache()
    return _xgboost_cache
