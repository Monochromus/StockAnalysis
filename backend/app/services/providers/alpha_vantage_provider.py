"""Alpha Vantage data provider - best for intraday data."""
from __future__ import annotations

import time
from datetime import datetime
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


class AlphaVantageProvider(BaseProvider):
    """Alpha Vantage data provider - excellent for intraday data."""

    BASE_URL = "https://www.alphavantage.co/query"

    # Alpha Vantage interval mapping
    INTERVAL_MAP = {
        "1m": "1min",
        "5m": "5min",
        "15m": "15min",
        "30m": "30min",
        "60m": "60min",
        "1h": "60min",
    }

    # Supported intervals
    INTRADAY_INTERVALS = {"1m", "5m", "15m", "30m", "60m", "1h"}
    DAILY_INTERVALS = {"1d"}

    def __init__(self):
        self.settings = get_settings()
        self._api_key: Optional[str] = getattr(self.settings, 'alpha_vantage_api_key', None)
        self._cache = TTLCache(maxsize=100, ttl=self.settings.cache_ttl_seconds)
        self._intraday_cache = TTLCache(maxsize=50, ttl=60)  # 1 minute for intraday
        # Free tier: 5 requests/minute, 500/day
        self._rate_limiter = RateLimiter(requests_per_minute=5, requests_per_day=500)
        self._client = httpx.AsyncClient(timeout=30.0)

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            name="alpha_vantage",
            display_name="Alpha Vantage",
            requires_api_key=True,
            capabilities=[
                ProviderCapability.INTRADAY,
                ProviderCapability.DAILY,
                ProviderCapability.STOCKS,
                ProviderCapability.FOREX,
                ProviderCapability.CRYPTO,
            ],
            rate_limit_per_minute=5,
            rate_limit_per_day=500,
            priority=1,  # Best for intraday
        )

    def is_available(self) -> bool:
        """Check if API key is configured."""
        return bool(self._api_key)

    def supports_interval(self, interval: str) -> bool:
        return interval.lower() in (self.INTRADAY_INTERVALS | self.DAILY_INTERVALS)

    def _get_cache_key(self, symbol: str, period: str, interval: str) -> str:
        return f"av:{symbol}:{period}:{interval}"

    def _is_intraday(self, interval: str) -> bool:
        return interval.lower() in self.INTRADAY_INTERVALS

    async def fetch_ohlcv(
        self,
        symbol: str,
        period: str,
        interval: str,
    ) -> FetchResult:
        """Fetch OHLCV data from Alpha Vantage."""
        start_time = time.time()

        if not self.is_available():
            return FetchResult(
                error="Alpha Vantage API key not configured",
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
            if self._is_intraday(interval):
                data = await self._fetch_intraday(symbol, interval)
            else:
                data = await self._fetch_daily(symbol, period)

            self._rate_limiter.record_request()

            if data is None:
                return FetchResult(
                    error=f"No data returned for {symbol}",
                    fetch_time_ms=(time.time() - start_time) * 1000,
                )

            if len(data.candles) < self.settings.min_data_points:
                return FetchResult(
                    error=f"Insufficient data: {len(data.candles)} points",
                    fetch_time_ms=(time.time() - start_time) * 1000,
                )

            # Cache result
            cache[cache_key] = data

            return FetchResult(
                data=data,
                from_cache=False,
                fetch_time_ms=(time.time() - start_time) * 1000,
            )

        except Exception as e:
            return FetchResult(
                error=f"Alpha Vantage error: {str(e)}",
                fetch_time_ms=(time.time() - start_time) * 1000,
            )

    async def _fetch_intraday(self, symbol: str, interval: str) -> Optional[OHLCVData]:
        """Fetch intraday data."""
        av_interval = self.INTERVAL_MAP.get(interval.lower(), "5min")

        params = {
            "function": "TIME_SERIES_INTRADAY",
            "symbol": symbol.upper(),
            "interval": av_interval,
            "outputsize": "full",
            "apikey": self._api_key,
        }

        response = await self._client.get(self.BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()

        # Check for error messages
        if "Error Message" in data:
            raise ValueError(data["Error Message"])
        if "Note" in data:
            # Rate limit message
            raise ValueError(data["Note"])

        # Parse time series data
        time_series_key = f"Time Series ({av_interval})"
        if time_series_key not in data:
            return None

        time_series = data[time_series_key]
        candles = self._parse_time_series(time_series, interval)

        if not candles:
            return None

        return OHLCVData(
            symbol=symbol.upper(),
            candles=candles,
            start_date=candles[0].timestamp,
            end_date=candles[-1].timestamp,
            interval=interval,
            count=len(candles),
        )

    async def _fetch_daily(self, symbol: str, period: str) -> Optional[OHLCVData]:
        """Fetch daily data."""
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol.upper(),
            "outputsize": "full",
            "apikey": self._api_key,
        }

        response = await self._client.get(self.BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()

        if "Error Message" in data:
            raise ValueError(data["Error Message"])
        if "Note" in data:
            raise ValueError(data["Note"])

        time_series_key = "Time Series (Daily)"
        if time_series_key not in data:
            return None

        time_series = data[time_series_key]
        candles = self._parse_time_series(time_series, "1d")

        # Filter by period
        candles = self._filter_by_period(candles, period)

        if not candles:
            return None

        return OHLCVData(
            symbol=symbol.upper(),
            candles=candles,
            start_date=candles[0].timestamp,
            end_date=candles[-1].timestamp,
            interval="1d",
            count=len(candles),
        )

    def _parse_time_series(self, time_series: dict, interval: str) -> list[Candle]:
        """Parse Alpha Vantage time series data into candles."""
        candles = []

        for timestamp_str, values in sorted(time_series.items()):
            try:
                # Alpha Vantage uses format: "2024-01-15 09:30:00" or "2024-01-15"
                if " " in timestamp_str:
                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                else:
                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d")

                candles.append(
                    Candle(
                        timestamp=timestamp,
                        open=float(values["1. open"]),
                        high=float(values["2. high"]),
                        low=float(values["3. low"]),
                        close=float(values["4. close"]),
                        volume=float(values.get("5. volume", 0)),
                    )
                )
            except (ValueError, KeyError):
                continue

        return candles

    def _filter_by_period(self, candles: list[Candle], period: str) -> list[Candle]:
        """Filter candles to match the requested period."""
        if not candles:
            return candles

        period_days = {
            "1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1825
        }
        days = period_days.get(period.lower(), 365)

        cutoff = datetime.now().replace(tzinfo=None)
        from datetime import timedelta
        cutoff = cutoff - timedelta(days=days)

        return [c for c in candles if c.timestamp >= cutoff]

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
