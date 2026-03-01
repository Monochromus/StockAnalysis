from __future__ import annotations
import time
from datetime import datetime
from functools import lru_cache
from typing import Optional, Tuple, List

import yfinance as yf
from cachetools import TTLCache

from app.config import get_settings
from app.core.exceptions import (
    TickerNotFoundError,
    InsufficientDataError,
    DataProviderError,
)
from app.schemas import Candle, OHLCVData, TickerInfo, TickerSearchResult


class DataProvider:
    def __init__(self):
        self.settings = get_settings()
        self._cache = TTLCache(maxsize=100, ttl=self.settings.cache_ttl_seconds)
        self._ticker_cache = TTLCache(maxsize=500, ttl=3600)  # 1 hour for ticker info

    def _get_cache_key(self, symbol: str, period: str, interval: str) -> str:
        return f"{symbol}:{period}:{interval}"

    def get_ticker_info(self, symbol: str) -> TickerInfo:
        """Get basic ticker information."""
        cache_key = f"info:{symbol}"
        if cache_key in self._ticker_cache:
            return self._ticker_cache[cache_key]

        # Return basic info without API call to avoid rate limiting
        ticker_info = TickerInfo(
            symbol=symbol.upper(),
            name=symbol.upper(),
            exchange=None,
            type="EQUITY",
            currency="USD",
        )
        self._ticker_cache[cache_key] = ticker_info
        return ticker_info

    def search_tickers(self, query: str, limit: int = 10) -> List[TickerSearchResult]:
        """Search for tickers matching query."""
        if len(query) < 1:
            return []

        # Return the query as a result - actual validation happens on data fetch
        return [
            TickerSearchResult(
                symbol=query.upper(),
                name=query.upper(),
                exchange=None,
                score=1.0,
            )
        ]

    def get_ohlcv(
        self,
        symbol: str,
        period: Optional[str] = None,
        interval: Optional[str] = None,
    ) -> Tuple[OHLCVData, Optional[str]]:
        """
        Fetch OHLCV data for a symbol.
        Returns (data, warning_message).
        """
        period = period or self.settings.default_period
        interval = interval or self.settings.default_interval
        cache_key = self._get_cache_key(symbol, period, interval)

        # Check cache
        if cache_key in self._cache:
            return self._cache[cache_key], None

        warning = None
        last_error = None

        for attempt in range(self.settings.max_retries):
            try:
                # Add delay between retries to avoid rate limiting
                if attempt > 0:
                    time.sleep(self.settings.retry_delay_seconds * (attempt + 1))

                ticker = yf.Ticker(symbol)

                # Fetch historical data directly - skip .info to avoid rate limiting
                df = ticker.history(period=period, interval=interval)

                if df is None or df.empty:
                    raise TickerNotFoundError(symbol)

                if len(df) < self.settings.min_data_points:
                    raise InsufficientDataError(
                        symbol, len(df), self.settings.min_data_points
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
                    raise InsufficientDataError(
                        symbol, len(candles), self.settings.min_data_points
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
                self._cache[cache_key] = data
                return data, warning

            except (TickerNotFoundError, InsufficientDataError):
                raise
            except Exception as e:
                last_error = str(e)
                # Check for rate limiting
                if "429" in last_error or "Too Many Requests" in last_error:
                    warning = "Rate limited by Yahoo Finance, retrying..."
                    time.sleep(5)  # Longer delay for rate limiting
                    continue
                if attempt < self.settings.max_retries - 1:
                    continue
                raise DataProviderError(f"Failed after {self.settings.max_retries} attempts: {last_error}")

        raise DataProviderError(f"Failed to fetch data: {last_error}")


@lru_cache
def get_data_provider() -> DataProvider:
    return DataProvider()
