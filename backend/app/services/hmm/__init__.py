"""HMM regime detection services."""

from .base_detector import (
    BaseRegimeDetector,
    ModelConfig,
    ModelType,
    EmissionDistribution,
    RegimeInfo,
)
from .feature_engine import FeatureEngine, FeatureConfig
from .hmm_model import HMMRegimeDetector
from .student_t_hmm import StudentTHMM
from .hmm_student_t import StudentTRegimeDetector
from .rs_garch import RSGARCHDetector
from .bayesian_hmm import BayesianHMMDetector
from .model_factory import ModelFactory
from .rolling_refit import RollingRefitManager, RefitResult, RollingRefitConfig
from .indicators import TechnicalIndicators
from .strategy import StrategyEngine, StrategyParams, ConfirmationResult, Signal
from .backtester import Backtester, BacktestResult, Trade
from .cache import HMMCache, get_hmm_cache
from .optimizer import (
    BaseOptimizer,
    OptimizationProgress,
    OptimizationResult,
    OptimizationStatus,
    HMMOptimizer,
    StrategyOptimizer,
    optimization_store,
)

__all__ = [
    # Base classes
    "BaseRegimeDetector",
    "ModelConfig",
    "ModelType",
    "EmissionDistribution",
    "RegimeInfo",
    # Feature engineering
    "FeatureEngine",
    "FeatureConfig",
    # HMM detectors
    "HMMRegimeDetector",
    "StudentTHMM",
    "StudentTRegimeDetector",
    "RSGARCHDetector",
    "BayesianHMMDetector",
    "ModelFactory",
    # Rolling refit
    "RollingRefitManager",
    "RefitResult",
    "RollingRefitConfig",
    # Indicators
    "TechnicalIndicators",
    # Strategy
    "StrategyEngine",
    "StrategyParams",
    "ConfirmationResult",
    "Signal",
    # Backtesting
    "Backtester",
    "BacktestResult",
    "Trade",
    # Caching
    "HMMCache",
    "get_hmm_cache",
    # Optimization
    "BaseOptimizer",
    "OptimizationProgress",
    "OptimizationResult",
    "OptimizationStatus",
    "HMMOptimizer",
    "StrategyOptimizer",
    "optimization_store",
]
