"""HMM Parameter Optimizer using Grid Search and Forward Feature Selection."""

import time
import itertools
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

from .base_optimizer import (
    BaseOptimizer,
    OptimizationResult,
    OptimizationStatus,
)
from ..base_detector import ModelConfig, ModelType
from ..model_factory import ModelFactory
from ..indicators import TechnicalIndicators
from ..strategy import StrategyEngine, StrategyParams
from ..backtester import Backtester, BacktestResult


class HMMOptimizer(BaseOptimizer):
    """
    Optimizer for HMM model parameters.

    Uses Grid Search over n_states, n_iter, and model_type,
    followed by Forward Feature Selection to find optimal features.
    """

    # Grid search parameter space (optimized for speed)
    # 8 × 3 × 2 = 48 combinations (~3-5 min instead of 14 min)
    N_STATES_RANGE = list(range(3, 11))  # 3-10 states (8 values) - important for accuracy
    N_ITER_RANGE = [100, 200, 300]  # Reduced from 10 to 3 values - diminishing returns after 100
    MODEL_TYPES = [
        ModelType.HMM_GAUSSIAN,
        ModelType.HMM_STUDENT_T,
        # RS_GARCH and BAYESIAN_HMM excluded - too slow and/or buggy
    ]

    # Core features (always included)
    CORE_FEATURES = ["log_return", "range", "volume_change"]

    # Additional features for forward selection
    ADDITIONAL_FEATURES = [
        "rsi",
        "macd",
        "macd_histogram",
        "momentum_normalized",
        "adx",
        "di_diff",
        "bb_pct",
        "atr_normalized",
        "volume_ratio",
        "sma_20_dist",
        "sma_50_dist",
    ]

    # Maximum features to select
    MAX_FEATURES = 8

    # Minimum alpha improvement to add a feature
    MIN_ALPHA_IMPROVEMENT = 0.1  # 0.1%

    def __init__(
        self,
        df: pd.DataFrame,
        strategy_params: Optional[StrategyParams] = None,
        leverage: float = 1.0,
        slippage_pct: float = 0.001,
        commission_pct: float = 0.001,
        initial_capital: float = 10000.0,
    ):
        """
        Initialize the HMM optimizer.

        Args:
            df: DataFrame with OHLCV data
            strategy_params: Strategy parameters to use for evaluation
            leverage: Backtesting leverage
            slippage_pct: Slippage percentage
            commission_pct: Commission percentage
            initial_capital: Initial capital for backtesting
        """
        super().__init__()
        self.df = df
        self.strategy_params = strategy_params or StrategyParams()
        self.leverage = leverage
        self.slippage_pct = slippage_pct
        self.commission_pct = commission_pct
        self.initial_capital = initial_capital

        # Calculate indicators once
        self.indicators = TechnicalIndicators(df)
        self.df_with_indicators = self.indicators.calculate_all()

        # Best results tracking
        self._best_alpha = float("-inf")
        self._best_params: Dict[str, Any] = {}
        self._best_metrics: Dict[str, float] = {}

    def _evaluate_params(
        self,
        n_states: int,
        n_iter: int,
        model_type: ModelType,
        selected_features: List[str],
    ) -> Tuple[float, Dict[str, float]]:
        """
        Evaluate a single parameter combination.

        Returns:
            Tuple of (alpha, metrics_dict)
        """
        try:
            # Create model configuration
            config = ModelConfig(
                n_states=n_states,
                selected_features=selected_features,
                n_iter=n_iter,
            )

            # Create and train model
            detector = ModelFactory.create(model_type, config)
            success = detector.train(
                self.df,
                df_indicators=self.df_with_indicators,
                n_iter=n_iter,
            )

            if not success:
                return float("-inf"), {}

            # Get regime series
            regime_df = detector.get_regime_series(self.df, self.df_with_indicators)

            # Generate signals
            strategy = StrategyEngine(params=self.strategy_params)
            signals_df = strategy.generate_signals_series(
                self.df_with_indicators, regime_df
            )

            # Run backtest
            backtester = Backtester(
                leverage=self.leverage,
                slippage_pct=self.slippage_pct,
                commission_pct=self.commission_pct,
                initial_capital=self.initial_capital,
                strategy_params=self.strategy_params,
            )

            result = backtester.run(self.df, signals_df)

            # Check for minimum trades
            if result.total_trades < 5:
                return float("-inf"), {}

            metrics = {
                "alpha": result.alpha,
                "sharpe": result.sharpe_ratio,
                "total_return": result.total_return,
                "max_drawdown": result.max_drawdown,
                "total_trades": result.total_trades,
                "win_rate": result.win_rate,
            }

            return result.alpha, metrics

        except Exception as e:
            return float("-inf"), {}

    def _run_grid_search(self) -> Tuple[Dict[str, Any], float, Dict[str, float]]:
        """
        Run grid search over core parameters.

        Returns:
            Tuple of (best_params, best_alpha, best_metrics)
        """
        # Calculate total combinations
        total_combinations = (
            len(self.N_STATES_RANGE) *
            len(self.N_ITER_RANGE) *
            len(self.MODEL_TYPES)
        )

        best_params = {}
        best_alpha = float("-inf")
        best_metrics = {}

        trial = 0
        for n_states in self.N_STATES_RANGE:
            for n_iter in self.N_ITER_RANGE:
                for model_type in self.MODEL_TYPES:
                    # Check cancellation
                    if self._check_cancelled():
                        return best_params, best_alpha, best_metrics

                    trial += 1

                    # Evaluate with core features
                    alpha, metrics = self._evaluate_params(
                        n_states=n_states,
                        n_iter=n_iter,
                        model_type=model_type,
                        selected_features=self.CORE_FEATURES,
                    )

                    if alpha > best_alpha:
                        best_alpha = alpha
                        best_params = {
                            "n_states": n_states,
                            "n_iter": n_iter,
                            "model_type": model_type.value,
                            "selected_features": self.CORE_FEATURES.copy(),
                        }
                        best_metrics = metrics

                    # Update progress
                    self._update_progress(
                        current_trial=trial,
                        total_trials=total_combinations,
                        best_alpha=best_alpha,
                        best_params=best_params,
                        message=f"Grid Search: n_states={n_states}, n_iter={n_iter}, model={model_type.value}",
                    )

        return best_params, best_alpha, best_metrics

    def _run_forward_feature_selection(
        self,
        base_params: Dict[str, Any],
        base_alpha: float,
        grid_search_trials: int,
    ) -> Tuple[Dict[str, Any], float, Dict[str, float]]:
        """
        Run forward feature selection on top of best grid search params.

        Returns:
            Tuple of (best_params, best_alpha, best_metrics)
        """
        current_features = self.CORE_FEATURES.copy()
        best_alpha = base_alpha
        best_params = base_params.copy()
        best_metrics = {}

        remaining_features = self.ADDITIONAL_FEATURES.copy()
        feature_trial = 0
        max_feature_trials = len(self.ADDITIONAL_FEATURES)
        total_trials = grid_search_trials + max_feature_trials

        while remaining_features and len(current_features) < self.MAX_FEATURES:
            # Check cancellation
            if self._check_cancelled():
                break

            best_new_feature = None
            best_new_alpha = best_alpha

            for feature in remaining_features:
                # Check cancellation
                if self._check_cancelled():
                    break

                feature_trial += 1
                test_features = current_features + [feature]

                alpha, metrics = self._evaluate_params(
                    n_states=base_params["n_states"],
                    n_iter=base_params["n_iter"],
                    model_type=ModelType(base_params["model_type"]),
                    selected_features=test_features,
                )

                # Update progress
                self._update_progress(
                    current_trial=grid_search_trials + feature_trial,
                    total_trials=total_trials,
                    best_alpha=best_alpha,
                    best_params=best_params,
                    message=f"Feature Selection: Testing {feature}",
                )

                if alpha > best_new_alpha + self.MIN_ALPHA_IMPROVEMENT:
                    best_new_alpha = alpha
                    best_new_feature = feature
                    best_metrics = metrics

            if best_new_feature is not None:
                current_features.append(best_new_feature)
                remaining_features.remove(best_new_feature)
                best_alpha = best_new_alpha
                best_params["selected_features"] = current_features.copy()
            else:
                # No improvement, stop feature selection
                break

        return best_params, best_alpha, best_metrics

    def optimize(self, **kwargs) -> OptimizationResult:
        """
        Run the full HMM optimization.

        Steps:
        1. Grid search over n_states, n_iter, model_type
        2. Forward feature selection with best core params
        """
        start_time = time.time()

        # Calculate total grid search combinations
        grid_search_trials = (
            len(self.N_STATES_RANGE) *
            len(self.N_ITER_RANGE) *
            len(self.MODEL_TYPES)
        )  # 8 × 3 × 2 = 48

        try:
            # Phase 1: Grid Search
            self._update_progress(
                current_trial=0,
                total_trials=grid_search_trials,
                best_alpha=float("-inf"),
                best_params={},
                message="Starting Grid Search over HMM parameters...",
            )

            grid_params, grid_alpha, grid_metrics = self._run_grid_search()

            if self._check_cancelled():
                return self._create_cancelled_result(start_time)

            if not grid_params:
                return OptimizationResult(
                    success=False,
                    best_params={},
                    best_alpha=0.0,
                    best_sharpe=0.0,
                    best_total_return=0.0,
                    best_max_drawdown=0.0,
                    total_trials_evaluated=grid_search_trials,
                    optimization_time_seconds=time.time() - start_time,
                    error_message="Grid search found no valid parameter combinations",
                )

            # Phase 2: Forward Feature Selection
            total_trials = grid_search_trials + len(self.ADDITIONAL_FEATURES)
            self._update_progress(
                current_trial=grid_search_trials,
                total_trials=total_trials,
                best_alpha=grid_alpha,
                best_params=grid_params,
                message="Starting Forward Feature Selection...",
            )

            final_params, final_alpha, final_metrics = self._run_forward_feature_selection(
                grid_params, grid_alpha, grid_search_trials
            )

            if self._check_cancelled():
                return self._create_cancelled_result(start_time)

            # Final progress update
            self._update_progress(
                current_trial=total_trials,
                total_trials=total_trials,
                best_alpha=final_alpha,
                best_params=final_params,
                message="Optimization complete!",
                status=OptimizationStatus.COMPLETED,
            )

            return OptimizationResult(
                success=True,
                best_params=final_params,
                best_alpha=final_alpha,
                best_sharpe=final_metrics.get("sharpe", 0.0),
                best_total_return=final_metrics.get("total_return", 0.0),
                best_max_drawdown=final_metrics.get("max_drawdown", 0.0),
                total_trials_evaluated=total_trials,
                optimization_time_seconds=time.time() - start_time,
            )

        except Exception as e:
            elapsed = time.time() - start_time
            self._update_progress(
                current_trial=0,
                total_trials=0,
                best_alpha=0.0,
                best_params={},
                message=f"Error: {str(e)}",
                status=OptimizationStatus.FAILED,
            )
            return OptimizationResult(
                success=False,
                best_params={},
                best_alpha=0.0,
                best_sharpe=0.0,
                best_total_return=0.0,
                best_max_drawdown=0.0,
                total_trials_evaluated=0,
                optimization_time_seconds=elapsed,
                error_message=str(e),
            )

    def _create_cancelled_result(self, start_time: float) -> OptimizationResult:
        """Create a result for cancelled optimization."""
        self._update_progress(
            current_trial=0,
            total_trials=0,
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
            total_trials_evaluated=0,
            optimization_time_seconds=time.time() - start_time,
            error_message="Cancelled by user",
        )
