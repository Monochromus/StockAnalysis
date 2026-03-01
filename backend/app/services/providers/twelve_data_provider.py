"""Twelve Data provider - good balance of intraday and daily data."""
from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Optional

import httpx
from cachetools import TTLCache

from app.config import get_settings
from app.schemas import Candle, OHLCVData

from .base import (
    BaseProvider,
    ProviderInfo,
    ProviderCapability,
    FetchResult,
)
from .rate_limiter import RateLimiter


class TwelveDataProvider(BaseProvider):
    """Twelve Data provider - versatile API with good coverage."""

    BASE_URL = "https://api.twelvedata.com/time_series"

    # Twelve Data interval mapping
    INTERVAL_MAP = {
        "1m": "1min",
        "5m": "5min",
        "15m": "15min",
        "30m": "30min",
        "1h": "1h",
        "60m": "1h",
        "1d": "1day",
        "1wk": "1week",
        "1mo": "1month",
    }

    SUPPORTED_INTERVALS = set(INTERVAL_MAP.keys())
    INTRADAY_INTERVALS = {"1m", "5m", "15m", "30m", "1h", "60m"}

    def __init__(self):
        self.settings = get_settings()
        self._api_key: Optional[str] = getattr(self.settings, 'twelve_data_api_key', None)
        self._cache = TTLCache(maxsize=100, ttl=self.settings.cache_ttl_seconds)
        self._intraday_cache = TTLCache(maxsize=50, ttl=60)
        # Free tier: 8 requests/minute, 800/day
        self._rate_limiter = RateLimiter(requests_per_minute=8, requests_per_day=800)
        self._client = httpx.AsyncClient(timeout=30.0)

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            name="twelve_data",
            display_name="Twelve Data",
            requires_api_key=True,
            capabilities=[
                ProviderCapability.INTRADAY,
                ProviderCapability.DAILY,
                ProviderCapability.WEEKLY,
                ProviderCapability.STOCKS,
                ProviderCapability.FOREX,
                ProviderCapability.CRYPTO,
            ],
            rate_limit_per_minute=8,
            rate_limit_per_day=800,
            priority=2,  # Secondary choice
        )

    def is_available(self) -> bool:
        return bool(self._api_key)

    def supports_interval(self, interval: str) -> bool:
        return interval.lower() in self.SUPPORTED_INTERVALS

    def _get_cache_key(self, symbol: str, period: str, interval: str) -> str:
        return f"td:{symbol}:{period}:{interval}"

    def _is_intraday(self, interval: str) -> bool:
        return interval.lower() in self.INTRADAY_INTERVALS

    def _period_to_outputsize(self, period: str, interval: str) -> int:
        """Convert period to number of data points for Twelve Data."""
        # Estimate number of bars based on period and interval
        period_days = {
            "1d": 1, "5d": 5, "1mo": 22, "3mo": 66,
            "6mo": 132, "1y": 252, "2y": 504, "5y": 1260
        }
        days = period_days.get(period.lower(), 252)

        # Calculate bars based on interval
        if interval in {"1m"}:
            return min(days * 390, 5000)  # 390 minutes per trading day
        elif interval in {"5m"}:
            return min(days * 78, 5000)
        elif interval in {"15m"}:
            return min(days * 26, 5000)
        elif interval in {"30m"}:
            return min(days * 13, 5000)
        elif interval in {"1h", "60m"}:
            return min(days * 7, 5000)
        else:
            return min(days, 5000)

    async def fetch_ohlcv(
        self,
        symbol: str,
        period: str,
        interval: str,
    ) -> FetchResult:
        """Fetch OHLCV data from Twelve Data."""
        start_time = time.time()

        if not self.is_available():
            return FetchResult(
                error="Twelve Data API key not configured",
                fetch_time_ms=(time.time() - start_time) * 1000,
            )

        cache_key = self._get_cache_key(symbol, period, interval)

        # Check cache
        cache = self._intraday_cache if self._is_intraday(interval) else self._cache
        if cache_key in cache:
            return FetchResult(
                data=cache[cache_key],
                from_cache=True,
                fetch_time_ms=(time.time() - start_time) * 1000,
            )

        # Check rate limit
        if not self._rate_limiter.can_request():
            wait_time = self._rate_limiter.wait_time_seconds()
            return FetchResult(
                error=f"Rate limited. Try again in {wait_time:.1f}s",
                fetch_time_ms=(time.time() - start_time) * 1000,
            )

        try:
            td_interval = self.INTERVAL_MAP.get(interval.lower(), "1day")
            outputsize = self._period_to_outputsize(period, interval)

            params = {
                "symbol": symbol.upper(),
                "interval": td_interval,
                "outputsize": outputsize,
                "apikey": self._api_key,
            }

            response = await self._client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

            self._rate_limiter.record_request()

            # Check for errors
            if data.get("status") == "error":
                return FetchResult(
                    error=data.get("message", "Unknown error"),
                    fetch_time_ms=(time.time() - start_time) * 1000,
                )

            if "values" not in data:
                return FetchResult(
                    error=f"No data returned for {symbol}",
                    fetch_time_ms=(time.time() - start_time) * 1000,
                )

            candles = self._parse_values(data["values"], interval)

            if len(candles) < self.settings.min_data_points:
                return FetchResult(
                    error=f"Insufficient data: {len(candles)} points",
                    fetch_time_ms=(time.time() - start_time) * 1000,
                )

            ohlcv_data = OHLCVData(
                symbol=symbol.upper(),
                candles=candles,
                start_date=candles[0].timestamp,
                end_date=candles[-1].timestamp,
                interval=interval,
                count=len(candles),
            )

            # Cache result
            cache[cache_key] = ohlcv_data

            return FetchResult(
                data=ohlcv_data,
                from_cache=False,
                fetch_time_ms=(time.time() - start_time) * 1000,
            )

        except Exception as e:
            return FetchResult(
                error=f"Twelve Data error: {str(e)}",
                fetch_time_ms=(time.time() - start_time) * 1000,
            )

    def _parse_values(self, values: list, interval: str) -> list[Candle]:
        """Parse Twelve Data values into candles."""
        candles = []

        for item in values:
            try:
                # Twelve Data datetime format: "2024-01-15 09:30:00" or "2024-01-15"
                datetime_str = item["datetime"]
                if " " in datetime_str:
                    timestamp = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
                else:
                    timestamp = datetime.strptime(datetime_str, "%Y-%m-%d")

                candles.append(
                    Candle(
                        timestamp=timestamp,
                        open=float(item["open"]),
                        high=float(item["high"]),
                        low=float(item["low"]),
                        close=float(item["close"]),
                        volume=float(item.get("volume", 0)),
                    )
                )
            except (ValueError, KeyError):
                continue

        # Twelve Data returns newest first, so reverse
        candles.reverse()
        return candles

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
