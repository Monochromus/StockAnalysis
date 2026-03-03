"""XGBoost residual correction services for Prophet hybrid forecasting."""

from .config import XGBoostConfig
from .feature_engine import XGBoostFeatureEngine
from .xgboost_model import XGBoostResidualCorrector, HybridForecastResult
from .cache import XGBoostCache, CachedXGBoostResult, get_xgboost_cache

__all__ = [
    # Configuration
    "XGBoostConfig",
    # Feature Engineering
    "XGBoostFeatureEngine",
    # Model
    "XGBoostResidualCorrector",
    "HybridForecastResult",
    # Cache
    "XGBoostCache",
    "CachedXGBoostResult",
    "get_xgboost_cache",
]
