"""In-memory cache for HMM models."""

from typing import Dict, Optional
from cachetools import TTLCache
from functools import lru_cache

from .hmm_model import HMMRegimeDetector


class HMMCache:
    """
    In-memory cache for trained HMM models.

    Models are cached by symbol and interval to avoid retraining.
    Cache has a TTL of 1 hour and max 100 models.
    """

    def __init__(self, maxsize: int = 100, ttl: int = 3600):
        """
        Initialize cache.

        Args:
            maxsize: Maximum number of models to cache
            ttl: Time-to-live in seconds (default 1 hour)
        """
        self._cache: TTLCache = TTLCache(maxsize=maxsize, ttl=ttl)

    def _make_key(self, symbol: str, interval: str, n_states: int) -> str:
        """Generate cache key from symbol, interval, and n_states."""
        return f"{symbol.upper()}:{interval}:{n_states}"

    def get(
        self, symbol: str, interval: str, n_states: int = 7
    ) -> Optional[HMMRegimeDetector]:
        """
        Get a cached HMM model.

        Args:
            symbol: Ticker symbol
            interval: Data interval (1d, 1h, etc.)
            n_states: Number of HMM states

        Returns:
            Cached HMMRegimeDetector if exists, None otherwise
        """
        key = self._make_key(symbol, interval, n_states)
        return self._cache.get(key)

    def set(
        self, symbol: str, interval: str, model: HMMRegimeDetector
    ) -> None:
        """
        Cache an HMM model.

        Args:
            symbol: Ticker symbol
            interval: Data interval
            model: Trained HMMRegimeDetector
        """
        key = self._make_key(symbol, interval, model.n_states)
        self._cache[key] = model

    def invalidate(self, symbol: str, interval: str, n_states: int = 7) -> bool:
        """
        Remove a model from cache.

        Args:
            symbol: Ticker symbol
            interval: Data interval
            n_states: Number of HMM states

        Returns:
            True if model was in cache and removed
        """
        key = self._make_key(symbol, interval, n_states)
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        """Clear all cached models."""
        self._cache.clear()

    @property
    def size(self) -> int:
        """Return number of cached models."""
        return len(self._cache)

    def has(self, symbol: str, interval: str, n_states: int = 7) -> bool:
        """Check if a model is cached."""
        key = self._make_key(symbol, interval, n_states)
        return key in self._cache


# Singleton instance
_hmm_cache: Optional[HMMCache] = None


def get_hmm_cache() -> HMMCache:
    """Get the singleton HMM cache instance."""
    global _hmm_cache
    if _hmm_cache is None:
        _hmm_cache = HMMCache()
    return _hmm_cache
