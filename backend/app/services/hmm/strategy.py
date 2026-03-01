"""Strategy engine with confirmation system."""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class Signal(Enum):
    """Trading signals."""

    LONG = "LONG"
    SHORT = "SHORT"
    CASH = "CASH"
    HOLD = "HOLD"


@dataclass
class StrategyParams:
    """Configurable strategy parameters."""

    # Confirmation requirements
    required_confirmations: int = 7
    total_conditions: int = 8

    # RSI thresholds
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    rsi_bull_min: float = 40.0
    rsi_bear_max: float = 60.0

    # MACD settings
    macd_threshold: float = 0.0

    # ADX settings
    adx_trend_threshold: float = 25.0

    # Momentum settings
    momentum_threshold: float = 0.0

    # Volume settings
    volume_ratio_threshold: float = 1.0

    # Regime confidence threshold
    regime_confidence_min: float = 0.5

    # Cooldown settings (in periods)
    cooldown_periods: int = 48

    # Bullish regimes for long signals
    bullish_regimes: List[str] = field(
        default_factory=lambda: ["Bull Run", "Bull", "Neutral Up"]
    )

    # Bearish regimes for short signals
    bearish_regimes: List[str] = field(
        default_factory=lambda: ["Crash", "Bear", "Neutral Down"]
    )

    # === NEW PARAMETERS ===

    # Risk Management
    stop_loss_pct: float = 0.0  # 0 = disabled, e.g. 0.05 = 5% stop loss
    take_profit_pct: float = 0.0  # 0 = disabled, e.g. 0.10 = 10% take profit
    trailing_stop_pct: float = 0.0  # 0 = disabled, e.g. 0.03 = 3% trailing stop

    # Position Management
    max_hold_periods: int = 0  # 0 = unlimited, e.g. 50 = max 50 periods

    # Moving Average settings
    ma_period: int = 50  # Period for MA condition (20, 50, 100, 200)

    # Exit behavior
    exit_on_regime_change: bool = True  # Exit when regime becomes unfavorable
    exit_on_opposite_signal: bool = True  # Exit when opposite signal appears

    # Signal filtering
    min_regime_duration: int = 1  # Minimum periods in regime before signal
    require_regime_confirmation: bool = False  # Require regime to persist for 2+ periods


@dataclass
class ConfirmationResult:
    """Result of confirmation check."""

    signal: Signal
    confirmations_met: int
    total_conditions: int
    details: Dict[str, bool]
    regime: str
    confidence: float


class StrategyEngine:
    """
    Strategy engine with confirmation-based signal generation.

    Uses a X of Y confirmation system where X conditions must be met
    out of Y total conditions to generate a signal.
    """

    def __init__(self, params: Optional[StrategyParams] = None):
        """Initialize strategy with parameters."""
        self.params = params or StrategyParams()
        self._last_signal: Optional[Signal] = None
        self._cooldown_counter: int = 0

    def check_long_conditions(
        self, row: pd.Series, regime: str, confidence: float
    ) -> Dict[str, bool]:
        """
        Check all conditions for a LONG signal.

        Returns dict of condition name -> met (True/False)
        """
        conditions = {}

        # 1. Regime is bullish
        conditions["regime_bullish"] = regime in self.params.bullish_regimes

        # 2. Regime confidence high enough
        conditions["regime_confidence"] = confidence >= self.params.regime_confidence_min

        # 3. RSI not overbought and above bull minimum
        conditions["rsi_favorable"] = (
            self.params.rsi_bull_min <= row.get("rsi", 50) <= self.params.rsi_overbought
        )

        # 4. MACD bullish (above signal line)
        conditions["macd_bullish"] = (
            row.get("macd", 0) > row.get("macd_signal", 0)
        )

        # 5. ADX showing trend with DI+ dominant
        conditions["adx_bullish"] = (
            row.get("adx", 0) > self.params.adx_trend_threshold
            and row.get("di_plus", 0) > row.get("di_minus", 0)
        )

        # 6. Positive momentum
        conditions["momentum_positive"] = row.get("momentum", 0) > self.params.momentum_threshold

        # 7. Volume above average
        conditions["volume_strong"] = row.get("volume_ratio", 1) > self.params.volume_ratio_threshold

        # 8. Price above key moving average (configurable period)
        ma_key = f"sma_{self.params.ma_period}"
        ma_value = row.get(ma_key, row.get("sma_50", 0))  # Fallback to sma_50
        conditions["price_above_ma"] = row.get("Close", 0) > ma_value

        return conditions

    def check_short_conditions(
        self, row: pd.Series, regime: str, confidence: float
    ) -> Dict[str, bool]:
        """
        Check all conditions for a SHORT signal.

        Returns dict of condition name -> met (True/False)
        """
        conditions = {}

        # 1. Regime is bearish
        conditions["regime_bearish"] = regime in self.params.bearish_regimes

        # 2. Regime confidence high enough
        conditions["regime_confidence"] = confidence >= self.params.regime_confidence_min

        # 3. RSI not oversold and below bear maximum
        conditions["rsi_favorable"] = (
            self.params.rsi_oversold <= row.get("rsi", 50) <= self.params.rsi_bear_max
        )

        # 4. MACD bearish (below signal line)
        conditions["macd_bearish"] = (
            row.get("macd", 0) < row.get("macd_signal", 0)
        )

        # 5. ADX showing trend with DI- dominant
        conditions["adx_bearish"] = (
            row.get("adx", 0) > self.params.adx_trend_threshold
            and row.get("di_minus", 0) > row.get("di_plus", 0)
        )

        # 6. Negative momentum
        conditions["momentum_negative"] = row.get("momentum", 0) < -self.params.momentum_threshold

        # 7. Volume above average
        conditions["volume_strong"] = row.get("volume_ratio", 1) > self.params.volume_ratio_threshold

        # 8. Price below key moving average (configurable period)
        ma_key = f"sma_{self.params.ma_period}"
        ma_value = row.get(ma_key, row.get("sma_50", 0))  # Fallback to sma_50
        conditions["price_below_ma"] = row.get("Close", 0) < ma_value

        return conditions

    def generate_signal(
        self, df: pd.DataFrame, regimes: pd.DataFrame
    ) -> ConfirmationResult:
        """
        Generate trading signal for the current (latest) bar.

        Args:
            df: DataFrame with OHLCV and indicators
            regimes: DataFrame with regime_id, regime_name, confidence

        Returns:
            ConfirmationResult with signal and details
        """
        # Get latest data point
        latest = df.iloc[-1]

        # Align regimes with price data
        regime_row = regimes.iloc[-1] if len(regimes) > 0 else None

        if regime_row is None:
            return ConfirmationResult(
                signal=Signal.HOLD,
                confirmations_met=0,
                total_conditions=self.params.total_conditions,
                details={},
                regime="Unknown",
                confidence=0.0,
            )

        current_regime = regime_row["regime_name"]
        confidence = regime_row["confidence"]

        # Check cooldown
        if self._cooldown_counter > 0:
            self._cooldown_counter -= 1
            return ConfirmationResult(
                signal=Signal.HOLD,
                confirmations_met=0,
                total_conditions=self.params.total_conditions,
                details={"cooldown_active": True},
                regime=current_regime,
                confidence=confidence,
            )

        # Check long conditions
        long_conditions = self.check_long_conditions(latest, current_regime, confidence)
        long_confirmations = sum(long_conditions.values())

        # Check short conditions
        short_conditions = self.check_short_conditions(latest, current_regime, confidence)
        short_confirmations = sum(short_conditions.values())

        # Determine signal based on confirmations
        if long_confirmations >= self.params.required_confirmations:
            signal = Signal.LONG
            details = long_conditions
            confirmations = long_confirmations
        elif short_confirmations >= self.params.required_confirmations:
            signal = Signal.SHORT
            details = short_conditions
            confirmations = short_confirmations
        elif current_regime == "Chop":
            signal = Signal.CASH
            details = {"chop_regime": True}
            confirmations = 0
        else:
            signal = Signal.HOLD
            details = {**long_conditions, **short_conditions}
            confirmations = max(long_confirmations, short_confirmations)

        return ConfirmationResult(
            signal=signal,
            confirmations_met=confirmations,
            total_conditions=self.params.total_conditions,
            details=details,
            regime=current_regime,
            confidence=confidence,
        )

    def generate_signals_series(
        self, df: pd.DataFrame, regimes: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Generate signals for entire dataset.

        Args:
            df: DataFrame with OHLCV and indicators
            regimes: DataFrame with regime info

        Returns:
            DataFrame with signals for each row
        """
        signals = []

        # Align indices
        common_idx = df.index.intersection(regimes.index)
        df_aligned = df.loc[common_idx]
        regimes_aligned = regimes.loc[common_idx]

        for i in range(len(df_aligned)):
            row = df_aligned.iloc[i]
            regime_row = regimes_aligned.iloc[i]

            # Check long conditions
            long_conditions = self.check_long_conditions(
                row, regime_row["regime_name"], regime_row["confidence"]
            )
            long_conf = sum(long_conditions.values())

            # Check short conditions
            short_conditions = self.check_short_conditions(
                row, regime_row["regime_name"], regime_row["confidence"]
            )
            short_conf = sum(short_conditions.values())

            # Determine signal
            if long_conf >= self.params.required_confirmations:
                signal = Signal.LONG.value
            elif short_conf >= self.params.required_confirmations:
                signal = Signal.SHORT.value
            elif regime_row["regime_name"] == "Chop":
                signal = Signal.CASH.value
            else:
                signal = Signal.HOLD.value

            signals.append(
                {
                    "signal": signal,
                    "long_confirmations": long_conf,
                    "short_confirmations": short_conf,
                    "regime": regime_row["regime_name"],
                    "confidence": regime_row["confidence"],
                }
            )

        result = pd.DataFrame(signals, index=df_aligned.index)
        return result

    def reset_cooldown(self):
        """Start cooldown period after exit."""
        self._cooldown_counter = self.params.cooldown_periods
