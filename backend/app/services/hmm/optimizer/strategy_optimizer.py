"""Strategy Parameter Optimizer using Optuna Bayesian Optimization."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING
import pandas as pd
import numpy as np

try:
    import optuna
    from optuna.samplers import TPESampler
    from optuna.pruners import MedianPruner
    OPTUNA_AVAILABLE = True
except ImportError:
    optuna = None  # type: ignore
    OPTUNA_AVAILABLE = False

if TYPE_CHECKING:
    import optuna as optuna_types

from .base_optimizer import (
    BaseOptimizer,
    OptimizationResult,
    OptimizationStatus,
)
from ..base_detector import BaseRegimeDetector
from ..strategy import StrategyEngine, StrategyParams
from ..backtester import Backtester


# Regime configuration presets
REGIME_PRESETS = {
    "aggressive": {
        "bullish_regimes": ["Bull Run", "Bull", "Neutral Up", "Chop"],
        "bearish_regimes": ["Crash", "Bear", "Neutral Down", "Chop"],
    },
    "moderate": {
        "bullish_regimes": ["Bull Run", "Bull", "Neutral Up"],
        "bearish_regimes": ["Crash", "Bear", "Neutral Down"],
    },
    "conservative": {
        "bullish_regimes": ["Bull Run", "Bull"],
        "bearish_regimes": ["Crash", "Bear"],
    },
}


class StrategyOptimizer(BaseOptimizer):
    """
    Optimizer for Strategy parameters using Optuna's TPE sampler.

    Uses Bayesian Optimization for efficient exploration of the
    high-dimensional strategy parameter space.
    """

    # Default optimization settings
    DEFAULT_N_TRIALS = 200
    DEFAULT_TIMEOUT = 300  # 5 minutes

    def __init__(
        self,
        df: pd.DataFrame,
        df_with_indicators: pd.DataFrame,
        regime_df: pd.DataFrame,
        leverage: float = 1.0,
        slippage_pct: float = 0.001,
        commission_pct: float = 0.001,
        initial_capital: float = 10000.0,
    ):
        """
        Initialize the Strategy optimizer.

        Args:
            df: DataFrame with OHLCV data
            df_with_indicators: DataFrame with calculated indicators
            regime_df: DataFrame with regime predictions
            leverage: Backtesting leverage
            slippage_pct: Slippage percentage
            commission_pct: Commission percentage
            initial_capital: Initial capital for backtesting
        """
        super().__init__()

        if not OPTUNA_AVAILABLE:
            raise ImportError(
                "Optuna is required for strategy optimization. "
                "Install it with: pip install optuna"
            )

        self.df = df
        self.df_with_indicators = df_with_indicators
        self.regime_df = regime_df
        self.leverage = leverage
        self.slippage_pct = slippage_pct
        self.commission_pct = commission_pct
        self.initial_capital = initial_capital

        # Tracking
        self._best_alpha = float("-inf")
        self._best_params: Dict[str, Any] = {}
        self._best_metrics: Dict[str, float] = {}
        self._trial_count = 0
        self._n_trials = self.DEFAULT_N_TRIALS
        self._study: Optional[optuna.Study] = None

    def _create_strategy_params(self, trial: "optuna.Trial") -> StrategyParams:
        """Create StrategyParams from Optuna trial suggestions."""
        # Regime preset (instead of 128 individual combinations)
        regime_preset = trial.suggest_categorical(
            "regime_preset", ["aggressive", "moderate", "conservative"]
        )
        preset = REGIME_PRESETS[regime_preset]

        params = StrategyParams(
            # Confirmation requirements
            required_confirmations=trial.suggest_int("required_confirmations", 1, 8),

            # RSI thresholds
            rsi_oversold=trial.suggest_float("rsi_oversold", 20.0, 40.0),
            rsi_overbought=trial.suggest_float("rsi_overbought", 60.0, 80.0),
            rsi_bull_min=trial.suggest_float("rsi_bull_min", 30.0, 50.0),
            rsi_bear_max=trial.suggest_float("rsi_bear_max", 50.0, 70.0),

            # MACD settings
            macd_threshold=trial.suggest_float("macd_threshold", -2.0, 2.0),

            # ADX settings
            adx_trend_threshold=trial.suggest_float("adx_trend_threshold", 15.0, 40.0),

            # Momentum settings
            momentum_threshold=trial.suggest_float("momentum_threshold", -2.0, 2.0),

            # Volume settings
            volume_ratio_threshold=trial.suggest_float("volume_ratio_threshold", 0.5, 2.0),

            # Regime confidence
            regime_confidence_min=trial.suggest_float("regime_confidence_min", 0.3, 0.8),

            # Cooldown
            cooldown_periods=trial.suggest_int("cooldown_periods", 0, 50),

            # Regime configuration (from preset)
            bullish_regimes=preset["bullish_regimes"],
            bearish_regimes=preset["bearish_regimes"],

            # Risk Management
            stop_loss_pct=trial.suggest_float("stop_loss_pct", 0.0, 0.15, step=0.01),
            take_profit_pct=trial.suggest_float("take_profit_pct", 0.0, 0.30, step=0.01),
            trailing_stop_pct=trial.suggest_float("trailing_stop_pct", 0.0, 0.10, step=0.005),

            # Position Management
            max_hold_periods=trial.suggest_int("max_hold_periods", 0, 100, step=5),
            ma_period=trial.suggest_categorical("ma_period", [20, 50, 100, 200]),

            # Exit behavior
            exit_on_regime_change=trial.suggest_categorical("exit_on_regime_change", [True, False]),
            exit_on_opposite_signal=trial.suggest_categorical("exit_on_opposite_signal", [True, False]),
        )

        return params

    def _objective(self, trial: "optuna.Trial") -> float:
        """Optuna objective function to maximize Alpha."""
        # Check cancellation
        if self._check_cancelled():
            raise optuna.TrialPruned()

        self._trial_count += 1

        try:
            # Create strategy params from trial
            strategy_params = self._create_strategy_params(trial)

            # Generate signals
            strategy = StrategyEngine(params=strategy_params)
            signals_df = strategy.generate_signals_series(
                self.df_with_indicators, self.regime_df
            )

            # Run backtest
            backtester = Backtester(
                leverage=self.leverage,
                slippage_pct=self.slippage_pct,
                commission_pct=self.commission_pct,
                initial_capital=self.initial_capital,
                strategy_params=strategy_params,
            )

            result = backtester.run(self.df, signals_df)

            # Prune trials with too few trades
            if result.total_trades < 5:
                raise optuna.TrialPruned()

            # Track best result
            if result.alpha > self._best_alpha:
                self._best_alpha = result.alpha
                self._best_params = self._params_to_dict(strategy_params, trial)
                self._best_metrics = {
                    "sharpe": result.sharpe_ratio,
                    "total_return": result.total_return,
                    "max_drawdown": result.max_drawdown,
                    "total_trades": result.total_trades,
                    "win_rate": result.win_rate,
                }

            # Update progress
            self._update_progress(
                current_trial=self._trial_count,
                total_trials=self._n_trials,
                best_alpha=self._best_alpha,
                best_params=self._best_params,
                message=f"Trial {self._trial_count}: Alpha={result.alpha:.2f}%",
            )

            return result.alpha

        except optuna.TrialPruned:
            raise
        except Exception as e:
            # Return very negative value for failed trials
            return float("-inf")

    def _params_to_dict(
        self,
        params: StrategyParams,
        trial: "optuna.Trial"
    ) -> Dict[str, Any]:
        """Convert StrategyParams to dictionary."""
        return {
            "required_confirmations": params.required_confirmations,
            "rsi_oversold": params.rsi_oversold,
            "rsi_overbought": params.rsi_overbought,
            "rsi_bull_min": params.rsi_bull_min,
            "rsi_bear_max": params.rsi_bear_max,
            "macd_threshold": params.macd_threshold,
            "adx_trend_threshold": params.adx_trend_threshold,
            "momentum_threshold": params.momentum_threshold,
            "volume_ratio_threshold": params.volume_ratio_threshold,
            "regime_confidence_min": params.regime_confidence_min,
            "cooldown_periods": params.cooldown_periods,
            "bullish_regimes": params.bullish_regimes,
            "bearish_regimes": params.bearish_regimes,
            "stop_loss_pct": params.stop_loss_pct,
            "take_profit_pct": params.take_profit_pct,
            "trailing_stop_pct": params.trailing_stop_pct,
            "max_hold_periods": params.max_hold_periods,
            "ma_period": params.ma_period,
            "exit_on_regime_change": params.exit_on_regime_change,
            "exit_on_opposite_signal": params.exit_on_opposite_signal,
            "regime_preset": trial.params.get("regime_preset", "moderate"),
        }

    def optimize(
        self,
        n_trials: int = DEFAULT_N_TRIALS,
        timeout: Optional[int] = DEFAULT_TIMEOUT,
        **kwargs
    ) -> OptimizationResult:
        """
        Run Bayesian optimization for strategy parameters.

        Args:
            n_trials: Maximum number of trials
            timeout: Maximum optimization time in seconds

        Returns:
            OptimizationResult with best parameters and metrics
        """
        start_time = time.time()
        self._n_trials = n_trials
        self._trial_count = 0

        try:
            # Initial progress
            self._update_progress(
                current_trial=0,
                total_trials=n_trials,
                best_alpha=float("-inf"),
                best_params={},
                message="Initializing Bayesian Optimization...",
            )

            # Create Optuna study
            sampler = TPESampler(seed=42, multivariate=True)
            pruner = MedianPruner(n_startup_trials=10, n_warmup_steps=5)

            self._study = optuna.create_study(
                direction="maximize",
                sampler=sampler,
                pruner=pruner,
            )

            # Suppress Optuna logs
            optuna.logging.set_verbosity(optuna.logging.WARNING)

            # Run optimization
            self._study.optimize(
                self._objective,
                n_trials=n_trials,
                timeout=timeout,
                catch=(Exception,),
                show_progress_bar=False,
            )

            # Check if cancelled
            if self._check_cancelled():
                return self._create_cancelled_result(start_time)

            # Get best results
            if self._study.best_trial is not None and self._best_alpha != float("-inf"):
                self._update_progress(
                    current_trial=self._trial_count,
                    total_trials=n_trials,
                    best_alpha=self._best_alpha,
                    best_params=self._best_params,
                    message="Optimization complete!",
                    status=OptimizationStatus.COMPLETED,
                )

                return OptimizationResult(
                    success=True,
                    best_params=self._best_params,
                    best_alpha=self._best_alpha,
                    best_sharpe=self._best_metrics.get("sharpe", 0.0),
                    best_total_return=self._best_metrics.get("total_return", 0.0),
                    best_max_drawdown=self._best_metrics.get("max_drawdown", 0.0),
                    total_trials_evaluated=self._trial_count,
                    optimization_time_seconds=time.time() - start_time,
                )
            else:
                return OptimizationResult(
                    success=False,
                    best_params={},
                    best_alpha=0.0,
                    best_sharpe=0.0,
                    best_total_return=0.0,
                    best_max_drawdown=0.0,
                    total_trials_evaluated=self._trial_count,
                    optimization_time_seconds=time.time() - start_time,
                    error_message="No valid trials completed",
                )

        except Exception as e:
            elapsed = time.time() - start_time
            self._update_progress(
                current_trial=self._trial_count,
                total_trials=n_trials,
                best_alpha=self._best_alpha if self._best_alpha != float("-inf") else 0.0,
                best_params=self._best_params,
                message=f"Error: {str(e)}",
                status=OptimizationStatus.FAILED,
            )
            return OptimizationResult(
                success=False,
                best_params=self._best_params,
                best_alpha=self._best_alpha if self._best_alpha != float("-inf") else 0.0,
                best_sharpe=self._best_metrics.get("sharpe", 0.0),
                best_total_return=self._best_metrics.get("total_return", 0.0),
                best_max_drawdown=self._best_metrics.get("max_drawdown", 0.0),
                total_trials_evaluated=self._trial_count,
                optimization_time_seconds=elapsed,
                error_message=str(e),
            )

    def _create_cancelled_result(self, start_time: float) -> OptimizationResult:
        """Create a result for cancelled optimization."""
        self._update_progress(
            current_trial=self._trial_count,
            total_trials=self._n_trials,
            best_alpha=self._best_alpha if self._best_alpha != float("-inf") else 0.0,
            best_params=self._best_params,
            message="Optimization cancelled by user",
            status=OptimizationStatus.CANCELLED,
        )
        return OptimizationResult(
            success=False,
            best_params=self._best_params,
            best_alpha=self._best_alpha if self._best_alpha != float("-inf") else 0.0,
            best_sharpe=self._best_metrics.get("sharpe", 0.0),
            best_total_return=self._best_metrics.get("total_return", 0.0),
            best_max_drawdown=self._best_metrics.get("max_drawdown", 0.0),
            total_trials_evaluated=self._trial_count,
            optimization_time_seconds=time.time() - start_time,
            error_message="Cancelled by user",
        )
