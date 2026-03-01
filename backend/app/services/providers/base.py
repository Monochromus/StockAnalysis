"""Base classes for data providers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Tuple

from app.schemas import Candle, OHLCVData


class ProviderCapability(Enum):
    """Capabilities that a provider can support."""
    INTRADAY = auto()  # 1m, 5m, 15m, 30m, 1h intervals
    DAILY = auto()     # 1d interval
    WEEKLY = auto()    # 1wk interval
    STOCKS = auto()
    CRYPTO = auto()
    FOREX = auto()


@dataclass
class ProviderInfo:
    """Information about a data provider."""
    name: str
    display_name: str
    requires_api_key: bool
    capabilities: List[ProviderCapability]
    rate_limit_per_minute: int = 0
    rate_limit_per_day: int = 0
    priority: int = 10  # Lower = higher priority


@dataclass
class FetchResult:
    """Result from a provider fetch operation."""
    data: Optional[OHLCVData] = None
    error: Optional[str] = None
    from_cache: bool = False
    fetch_time_ms: float = 0.0

    @property
    def success(self) -> bool:
        return self.data is not None and self.error is None


@dataclass
class ProviderMetadata:
    """Metadata about which provider served data."""
    provider_name: str
    provider_display_name: str
    from_cache: bool = False
    fetch_time_ms: Optional[float] = None


INTRADAY_INTERVALS = {"1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h"}
DAILY_INTERVALS = {"1d"}
WEEKLY_INTERVALS = {"1wk", "1mo", "3mo"}


def is_intraday_interval(interval: str) -> bool:
    """Check if an interval is considered intraday."""
    return interval.lower() in INTRADAY_INTERVALS


class BaseProvider(ABC):
    """Abstract base class for all data providers."""

    @property
    @abstractmethod
    def info(self) -> ProviderInfo:
        """Return provider information."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available (e.g., has valid API key)."""
        pass

    @abstractmethod
    def supports_interval(self, interval: str) -> bool:
        """Check if the provider supports the given interval."""
        pass

    @abstractmethod
    async def fetch_ohlcv(
        self,
        symbol: str,
        period: str,
        interval: str,
    ) -> FetchResult:
        """Fetch OHLCV data for a symbol."""
        pass

    def supports_symbol_type(self, symbol: str) -> bool:
        """Check if provider supports the type of symbol (stock, crypto, forex)."""
        # Default implementation - can be overridden by subclasses
        return True
