"""YFinance data provider - fallback provider with no API key required."""
from __future__ import annotations

import time
from typing import List

import yfinance as yf
from cachetools import TTLCache

from app.config import get_settings
from app.core.exceptions import (
    TickerNotFoundError,
    InsufficientDataError,
    DataProviderError,
)
from app.schemas import Candle, OHLCVData

from .base import (
    BaseProvider,
    ProviderInfo,
    ProviderCapability,
    FetchResult,
    is_intraday_interval,
)
from .rate_limiter import RateLimiter


class YFinanceProvider(BaseProvider):
    """YFinance data provider - reliable fallback with broad coverage."""

    SUPPORTED_INTERVALS = {
        "1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h",
        "1d", "5d", "1wk", "1mo", "3mo"
    }

    # YFinance has intraday limitations - max 7 days for 1m, 60 days for others
    INTRADAY_MAX_PERIODS = {
        "1m": "7d",
        "2m": "60d",
        "5m": "60d",
        "15m": "60d",
        "30m": "60d",
        "60m": "730d",
        "90m": "60d",
        "1h": "730d",
    }

    def __init__(self):
        self.settings = get_settings()
        self._cache = TTLCache(maxsize=100, ttl=self.settings.cache_ttl_seconds)
        self._intraday_cache = TTLCache(maxsize=50, ttl=60)  # 1 minute for intraday
        # YFinance has implicit rate limiting but we add a small buffer
        self._rate_limiter = RateLimiter(requests_per_minute=10, requests_per_day=0)

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            name="yfinance",
            display_name="Yahoo Finance",
            requires_api_key=False,
            capabilities=[
                ProviderCapability.INTRADAY,
                ProviderCapability.DAILY,
                ProviderCapability.WEEKLY,
                ProviderCapability.STOCKS,
                ProviderCapability.CRYPTO,
            ],
            rate_limit_per_minute=10,
            rate_limit_per_day=0,
            priority=3,  # Fallback provider
        )

    def is_available(self) -> bool:
        """YFinance is always available (no API key required)."""
        return True

    def supports_interval(self, interval: str) -> bool:
        return interval.lower() in self.SUPPORTED_INTERVALS

    def _get_cache_key(self, symbol: str, period: str, interval: str) -> str:
        return f"yf:{symbol}:{period}:{interval}"

    def _get_effective_period(self, period: str, interval: str) -> str:
        """Get effective period respecting yfinance intraday limits."""
        if interval in self.INTRADAY_MAX_PERIODS:
            max_period = self.INTRADAY_MAX_PERIODS[interval]
            # Simple period comparison (could be more sophisticated)
            return max_period if self._period_to_days(period) > self._period_to_days(max_period) else period
        return period

    def _period_to_days(self, period: str) -> int:
        """Convert period string to approximate days."""
        period_map = {
            "1d": 1, "5d": 5, "7d": 7, "1mo": 30, "3mo": 90,
            "6mo": 180, "1y": 365, "2y": 730, "5y": 1825, "10y": 3650, "max": 10000
        }
        return period_map.get(period.lower(), 365)

    async def fetch_ohlcv(
        self,
        symbol: str,
        period: str,
        interval: str,
    ) -> FetchResult:
        """Fetch OHLCV data using yfinance."""
        start_time = time.time()
        cache_key = self._get_cache_key(symbol, period, interval)

        # Check appropriate cache
        cache = self._intraday_cache if is_intraday_interval(interval) else self._cache
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

        # Adjust period for intraday limitations
        effective_period = self._get_effective_period(period, interval)

        last_error = None
        for attempt in range(self.settings.max_retries):
            try:
                if attempt > 0:
                    time.sleep(self.settings.retry_delay_seconds * (attempt + 1))

                ticker = yf.Ticker(symbol)
                df = ticker.history(period=effective_period, interval=interval)

                self._rate_limiter.record_request()

                if df is None or df.empty:
                    return FetchResult(
                        error=f"No data found for {symbol}",
                        fetch_time_ms=(time.time() - start_time) * 1000,
                    )

                if len(df) < self.settings.min_data_points:
                    return FetchResult(
                        error=f"Insufficient data: {len(df)} points (min: {self.settings.min_data_points})",
                        fetch_time_ms=(time.time() - start_time) * 1000,
                    )

                # Convert to candles
                candles = []
                for idx, row in df.iterrows():
                    try:
                        candles.append(
                            Candle(
                                timestamp=idx.to_pydatetime(),
                                open=float(row["Open"]),
                                high=float(row["High"]),
                                low=float(row["Low"]),
                                close=float(row["Close"]),
                                volume=float(row["Volume"]),
                            )
                        )
                    except Exception:
                        continue

                if len(candles) < self.settings.min_data_points:
                    return FetchResult(
                        error=f"Insufficient valid candles: {len(candles)}",
                        fetch_time_ms=(time.time() - start_time) * 1000,
                    )

                data = OHLCVData(
                    symbol=symbol.upper(),
                    candles=candles,
                    start_date=candles[0].timestamp,
                    end_date=candles[-1].timestamp,
                    interval=interval,
                    count=len(candles),
                )

                # Cache the result
                cache[cache_key] = data

                return FetchResult(
                    data=data,
                    from_cache=False,
                    fetch_time_ms=(time.time() - start_time) * 1000,
                )

            except Exception as e:
                last_error = str(e)
                if "429" in last_error or "Too Many Requests" in last_error:
                    time.sleep(5)
                    continue
                if attempt < self.settings.max_retries - 1:
                    continue

        return FetchResult(
            error=f"Failed after {self.settings.max_retries} attempts: {last_error}",
            fetch_time_ms=(time.time() - start_time) * 1000,
        )
