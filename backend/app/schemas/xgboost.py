"""Pydantic schemas for XGBoost residual correction."""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


# ============== Configuration Schemas ==============

class XGBoostSettings(BaseModel):
    """XGBoost hyperparameter settings."""

    n_estimators: int = Field(500, ge=100, le=2000, description="Number of boosting rounds")
    max_depth: int = Field(4, ge=2, le=10, description="Maximum tree depth")
    learning_rate: float = Field(0.05, ge=0.01, le=0.3, description="Learning rate")
    subsample: float = Field(0.8, ge=0.5, le=1.0, description="Row subsampling ratio")
    colsample_bytree: float = Field(0.8, ge=0.5, le=1.0, description="Column subsampling ratio")
    min_child_weight: int = Field(5, ge=1, le=20, description="Minimum child weight")
    reg_alpha: float = Field(0.1, ge=0.0, le=10.0, description="L1 regularization")
    reg_lambda: float = Field(1.0, ge=0.0, le=10.0, description="L2 regularization")


class XGBoostFeatureToggles(BaseModel):
    """Feature group toggles."""

    use_time_features: bool = Field(True, description="Enable time features")
    use_lag_features: bool = Field(True, description="Enable lag features")
    use_rolling_features: bool = Field(True, description="Enable rolling features")
    use_prophet_components: bool = Field(True, description="Enable Prophet component features")
    use_market_structure: bool = Field(True, description="Enable market structure features")


# ============== Request Schemas ==============

class XGBoostAnalysisRequest(BaseModel):
    """Request for XGBoost hybrid analysis."""

    symbol: str = Field(..., description="Ticker symbol")
    period: str = Field("5y", description="Data period for training")
    interval: str = Field("1d", description="Data interval")

    # Prophet settings (reuse from Prophet analysis)
    forecast_periods: int = Field(365, ge=30, le=730, description="Days to forecast")

    # XGBoost settings
    settings: Optional[XGBoostSettings] = Field(None, description="XGBoost hyperparameters")
    feature_toggles: Optional[XGBoostFeatureToggles] = Field(None, description="Feature group toggles")

    # Force recalculation
    force_refresh: bool = Field(False, description="Force recalculation, ignore cache")


# ============== Data Point Schemas ==============

class HybridForecastDataPoint(BaseModel):
    """Single data point for hybrid forecast."""

    timestamp: str
    prophet_value: float
    hybrid_value: float
    lower: float
    upper: float
    is_forecast: bool


class FeatureImportanceItem(BaseModel):
    """Feature importance information."""

    feature_name: str
    importance: float
    rank: int


class XGBoostMetricsSchema(BaseModel):
    """Metrics comparing Prophet vs Hybrid performance."""

    # Prophet-only metrics
    prophet_mae: float
    prophet_rmse: float
    prophet_mape: float
    prophet_r2: float

    # Hybrid metrics
    hybrid_mae: float
    hybrid_rmse: float
    hybrid_mape: float
    hybrid_r2: float

    # Improvement percentages
    mae_improvement_pct: float
    rmse_improvement_pct: float
    mape_improvement_pct: float
    r2_improvement_pct: float


# ============== Response Schemas ==============

class HybridForecastSeries(BaseModel):
    """Complete hybrid forecast series."""

    horizon: str
    display_name: str
    color: str
    training_end_date: str
    forecast_start_date: str
    series: List[HybridForecastDataPoint]


class XGBoostAnalysisResponse(BaseModel):
    """Full XGBoost hybrid analysis response."""

    symbol: str
    timestamp: datetime
    period: str
    interval: str
    forecast_periods: int

    # Hybrid forecasts
    hybrid_forecasts: List[HybridForecastSeries]

    # Metrics comparison
    metrics: Optional[XGBoostMetricsSchema] = None

    # Feature importance (top 10)
    feature_importance: List[FeatureImportanceItem]

    # Settings used
    settings: XGBoostSettings
    feature_toggles: XGBoostFeatureToggles

    # Cache info
    from_cache: bool = False
    warning: Optional[str] = None


class XGBoostComparisonResponse(BaseModel):
    """Comparison between Prophet-only and Hybrid forecasts."""

    symbol: str
    timestamp: datetime

    # Prophet forecast summary
    prophet_last_value: float
    prophet_forecast_30d: Optional[float] = None
    prophet_forecast_90d: Optional[float] = None

    # Hybrid forecast summary
    hybrid_last_value: float
    hybrid_forecast_30d: Optional[float] = None
    hybrid_forecast_90d: Optional[float] = None

    # Metrics
    metrics: XGBoostMetricsSchema

    # Feature importance
    feature_importance: List[FeatureImportanceItem]

    warning: Optional[str] = None
