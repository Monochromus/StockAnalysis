"""Volatility and RSI calculation for Prophet forecasting."""

import pandas as pd
import numpy as np
from typing import Tuple


class ProphetIndicators:
    """
    Calculate volatility and RSI for Prophet forecasting.

    Prepares indicator series in Prophet-compatible format (ds, y columns).
    """

    def __init__(self, df: pd.DataFrame):
        """
        Initialize with OHLCV DataFrame.

        Args:
            df: DataFrame with Open, High, Low, Close, Volume columns
                and datetime index
        """
        self.df = df.copy()
        self._ensure_columns()

    def _ensure_columns(self) -> None:
        """Ensure required columns exist."""
        required = ["Open", "High", "Low", "Close"]
        missing = [col for col in required if col not in self.df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

    def _remove_timezone(self, dt_index: pd.DatetimeIndex) -> pd.DatetimeIndex:
        """Remove timezone from datetime index (Prophet requirement)."""
        if dt_index.tz is not None:
            return dt_index.tz_localize(None)
        return dt_index

    def calculate_volatility(self, window: int = 20) -> pd.DataFrame:
        """
        Calculate rolling volatility (annualized standard deviation of returns).

        Args:
            window: Rolling window size in periods

        Returns:
            DataFrame with 'ds' (datetime) and 'y' (volatility) columns
        """
        # Calculate log returns
        log_returns = np.log(self.df["Close"] / self.df["Close"].shift(1))

        # Rolling standard deviation, annualized (assuming daily data)
        volatility = log_returns.rolling(window=window).std() * np.sqrt(252)

        # Create Prophet-compatible DataFrame (remove timezone)
        prophet_df = pd.DataFrame({
            "ds": self._remove_timezone(self.df.index),
            "y": volatility.values
        })

        # Drop NaN values from rolling window
        prophet_df = prophet_df.dropna().reset_index(drop=True)

        return prophet_df

    def calculate_rsi(self, period: int = 14) -> pd.DataFrame:
        """
        Calculate Relative Strength Index (RSI).

        Args:
            period: RSI calculation period

        Returns:
            DataFrame with 'ds' (datetime) and 'y' (RSI) columns
        """
        delta = self.df["Close"].diff()

        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)

        avg_gain = gain.ewm(span=period, adjust=False).mean()
        avg_loss = loss.ewm(span=period, adjust=False).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        # Create Prophet-compatible DataFrame (remove timezone)
        prophet_df = pd.DataFrame({
            "ds": self._remove_timezone(self.df.index),
            "y": rsi.values
        })

        # Drop NaN values
        prophet_df = prophet_df.dropna().reset_index(drop=True)

        return prophet_df

    def calculate_atr(self, period: int = 14) -> pd.DataFrame:
        """
        Calculate Average True Range (ATR) for volatility measure.

        Args:
            period: ATR calculation period

        Returns:
            DataFrame with 'ds' (datetime) and 'y' (ATR) columns
        """
        high = self.df["High"]
        low = self.df["Low"]
        close = self.df["Close"]

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.ewm(span=period, adjust=False).mean()

        # Create Prophet-compatible DataFrame (remove timezone)
        prophet_df = pd.DataFrame({
            "ds": self._remove_timezone(self.df.index),
            "y": atr.values
        })

        # Drop NaN values
        prophet_df = prophet_df.dropna().reset_index(drop=True)

        return prophet_df

    def prepare_price_data(self) -> pd.DataFrame:
        """
        Prepare close price data for Prophet forecasting.

        Returns:
            DataFrame with 'ds' (datetime) and 'y' (price) columns
        """
        prophet_df = pd.DataFrame({
            "ds": self._remove_timezone(self.df.index),
            "y": self.df["Close"].values
        })

        prophet_df = prophet_df.dropna().reset_index(drop=True)

        return prophet_df

    def prepare_all_indicators(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Prepare all indicator data for Prophet forecasting.

        Returns:
            Tuple of (price_df, volatility_df, rsi_df)
        """
        price_df = self.prepare_price_data()
        volatility_df = self.calculate_volatility()
        rsi_df = self.calculate_rsi()

        return price_df, volatility_df, rsi_df
