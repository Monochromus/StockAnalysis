"""Technical indicators for trading signals."""

import pandas as pd
import numpy as np
import ta
from typing import Dict, List


class TechnicalIndicators:
    """Calculate technical indicators for trading analysis."""

    def __init__(self, df: pd.DataFrame):
        """
        Initialize with OHLCV data.

        Args:
            df: DataFrame with Open, High, Low, Close, Volume columns
        """
        self.df = df.copy()
        self._indicators: Dict[str, pd.Series] = {}

    def calculate_all(self) -> pd.DataFrame:
        """Calculate all indicators and return enriched DataFrame."""
        result = self.df.copy()

        # RSI
        result["rsi"] = self.rsi()

        # MACD
        macd_data = self.macd()
        result["macd"] = macd_data["macd"]
        result["macd_signal"] = macd_data["signal"]
        result["macd_histogram"] = macd_data["histogram"]

        # ADX
        adx_data = self.adx()
        result["adx"] = adx_data["adx"]
        result["di_plus"] = adx_data["di_plus"]
        result["di_minus"] = adx_data["di_minus"]

        # Bollinger Bands
        bb_data = self.bollinger_bands()
        result["bb_upper"] = bb_data["upper"]
        result["bb_middle"] = bb_data["middle"]
        result["bb_lower"] = bb_data["lower"]
        result["bb_width"] = bb_data["width"]
        result["bb_pct"] = bb_data["pct_b"]

        # Momentum
        result["momentum"] = self.momentum()
        result["roc"] = self.rate_of_change()

        # Volume indicators
        result["volume_sma"] = self.volume_sma()
        result["volume_ratio"] = result["Volume"] / result["volume_sma"]

        # Moving averages
        result["sma_20"] = self.sma(20)
        result["sma_50"] = self.sma(50)
        result["sma_200"] = self.sma(200)
        result["ema_12"] = self.ema(12)
        result["ema_26"] = self.ema(26)

        # ATR for volatility
        result["atr"] = self.atr()

        return result

    def rsi(self, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index."""
        return ta.momentum.RSIIndicator(
            close=self.df["Close"], window=period
        ).rsi()

    def macd(
        self, fast: int = 12, slow: int = 26, signal: int = 9
    ) -> Dict[str, pd.Series]:
        """Calculate MACD indicator."""
        macd_indicator = ta.trend.MACD(
            close=self.df["Close"],
            window_fast=fast,
            window_slow=slow,
            window_sign=signal,
        )
        return {
            "macd": macd_indicator.macd(),
            "signal": macd_indicator.macd_signal(),
            "histogram": macd_indicator.macd_diff(),
        }

    def adx(self, period: int = 14) -> Dict[str, pd.Series]:
        """Calculate Average Directional Index."""
        adx_indicator = ta.trend.ADXIndicator(
            high=self.df["High"],
            low=self.df["Low"],
            close=self.df["Close"],
            window=period,
        )
        return {
            "adx": adx_indicator.adx(),
            "di_plus": adx_indicator.adx_pos(),
            "di_minus": adx_indicator.adx_neg(),
        }

    def bollinger_bands(
        self, period: int = 20, std_dev: float = 2.0
    ) -> Dict[str, pd.Series]:
        """Calculate Bollinger Bands."""
        bb = ta.volatility.BollingerBands(
            close=self.df["Close"], window=period, window_dev=std_dev
        )
        return {
            "upper": bb.bollinger_hband(),
            "middle": bb.bollinger_mavg(),
            "lower": bb.bollinger_lband(),
            "width": bb.bollinger_wband(),
            "pct_b": bb.bollinger_pband(),
        }

    def momentum(self, period: int = 10) -> pd.Series:
        """Calculate momentum."""
        return self.df["Close"] - self.df["Close"].shift(period)

    def rate_of_change(self, period: int = 10) -> pd.Series:
        """Calculate Rate of Change."""
        return ta.momentum.ROCIndicator(
            close=self.df["Close"], window=period
        ).roc()

    def volume_sma(self, period: int = 20) -> pd.Series:
        """Calculate volume simple moving average."""
        return self.df["Volume"].rolling(window=period).mean()

    def sma(self, period: int) -> pd.Series:
        """Calculate Simple Moving Average."""
        return ta.trend.SMAIndicator(
            close=self.df["Close"], window=period
        ).sma_indicator()

    def ema(self, period: int) -> pd.Series:
        """Calculate Exponential Moving Average."""
        return ta.trend.EMAIndicator(
            close=self.df["Close"], window=period
        ).ema_indicator()

    def atr(self, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        return ta.volatility.AverageTrueRange(
            high=self.df["High"],
            low=self.df["Low"],
            close=self.df["Close"],
            window=period,
        ).average_true_range()

    def to_series_list(self) -> Dict[str, List[Dict]]:
        """
        Convert all indicators to lists of dicts for JSON serialization.

        Returns:
            Dict with indicator names as keys and list of {timestamp, value} as values
        """
        df_with_indicators = self.calculate_all()
        result = {}

        indicator_columns = [
            "rsi", "macd", "macd_signal", "macd_histogram",
            "adx", "di_plus", "di_minus",
            "bb_upper", "bb_middle", "bb_lower", "bb_width", "bb_pct",
            "momentum", "roc",
            "volume_sma", "volume_ratio",
            "sma_20", "sma_50", "sma_200", "ema_12", "ema_26",
            "atr"
        ]

        for col in indicator_columns:
            if col in df_with_indicators.columns:
                series_data = []
                for idx, value in df_with_indicators[col].items():
                    if pd.notna(value):
                        series_data.append({
                            "timestamp": idx.isoformat() if hasattr(idx, "isoformat") else str(idx),
                            "value": float(value)
                        })
                result[col] = series_data

        return result

    @staticmethod
    def get_indicator_signals(df: pd.DataFrame) -> Dict[str, str]:
        """
        Get current signal status for each indicator.

        Returns dict with indicator name and signal (bullish/bearish/neutral)
        """
        signals = {}
        latest = df.iloc[-1]

        # RSI
        if latest.get("rsi", 50) < 30:
            signals["RSI"] = "oversold"
        elif latest.get("rsi", 50) > 70:
            signals["RSI"] = "overbought"
        else:
            signals["RSI"] = "neutral"

        # MACD
        if latest.get("macd", 0) > latest.get("macd_signal", 0):
            signals["MACD"] = "bullish"
        else:
            signals["MACD"] = "bearish"

        # ADX trend strength
        if latest.get("adx", 0) > 25:
            if latest.get("di_plus", 0) > latest.get("di_minus", 0):
                signals["ADX"] = "strong_bullish"
            else:
                signals["ADX"] = "strong_bearish"
        else:
            signals["ADX"] = "weak_trend"

        # Bollinger Bands
        if latest.get("bb_pct", 0.5) > 1:
            signals["BB"] = "overbought"
        elif latest.get("bb_pct", 0.5) < 0:
            signals["BB"] = "oversold"
        else:
            signals["BB"] = "neutral"

        # Moving averages
        close = latest.get("Close", 0)
        sma50 = latest.get("sma_50", 0)
        sma200 = latest.get("sma_200", 0)
        if close > sma50 > sma200:
            signals["MA"] = "bullish"
        elif close < sma50 < sma200:
            signals["MA"] = "bearish"
        else:
            signals["MA"] = "mixed"

        # Momentum
        if latest.get("momentum", 0) > 0 and latest.get("roc", 0) > 0:
            signals["Momentum"] = "bullish"
        elif latest.get("momentum", 0) < 0 and latest.get("roc", 0) < 0:
            signals["Momentum"] = "bearish"
        else:
            signals["Momentum"] = "neutral"

        return signals
