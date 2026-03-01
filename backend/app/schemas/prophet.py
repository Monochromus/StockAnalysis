"""Pydantic schemas for Prophet forecasting."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ============== Data Point Schemas ==============

class ForecastDataPoint(BaseModel):
    """Single forecast data point."""

    timestamp: str
    value: float
    lower: float  # Lower confidence bound
    upper: float  # Upper confidence bound
    is_forecast: bool  # True if this is a forecast (not historical fit)


class ComponentDataPoint(BaseModel):
    """Single component data point for seasonality visualization."""

    ds: str  # Date string
    value: float


# ============== Forecast Series Schemas ==============

class ForecastSeries(BaseModel):
    """Complete forecast series for a single horizon."""

    horizon: str  # "long_term", "mid_term", "short_term"
    display_name: str  # "Langfristig", "Mittelfristig", "Kurzfristig"
    color: str  # Hex color code
    training_end_date: str
    forecast_start_date: str
    mape: Optional[float] = None  # Mean Absolute Percentage Error
    rmse: Optional[float] = None  # Root Mean Square Error
    series: List[ForecastDataPoint]


class ComponentSeries(BaseModel):
    """Seasonal components for visualization."""

    trend: List[ComponentDataPoint]
    weekly: Optional[List[ComponentDataPoint]] = None
    monthly: Optional[List[ComponentDataPoint]] = None
    yearly: Optional[List[ComponentDataPoint]] = None


# ============== Request Schemas ==============

class ProphetAnalysisRequest(BaseModel):
    """Request for Prophet analysis."""

    symbol: str = Field(..., description="Ticker symbol")
    period: str = Field("5y", description="Data period for training")
    interval: str = Field("1d", description="Data interval")
    forecast_periods: int = Field(365, ge=30, le=730, description="Days to forecast")

    # Prophet configuration
    yearly_seasonality: bool = Field(True, description="Include yearly seasonality")
    weekly_seasonality: bool = Field(True, description="Include weekly seasonality")
    changepoint_prior_scale: float = Field(
        0.05, ge=0.001, le=0.5,
        description="Flexibility of changepoints"
    )
    interval_width: float = Field(
        0.95, ge=0.5, le=0.99,
        description="Confidence interval width"
    )

    # Force recalculation
    force_refresh: bool = Field(False, description="Force recalculation, ignore cache")


class ProphetPriceRequest(BaseModel):
    """Request for price-only forecast."""

    symbol: str = Field(..., description="Ticker symbol")
    period: str = Field("5y", description="Data period for training")
    interval: str = Field("1d", description="Data interval")
    forecast_periods: int = Field(365, ge=30, le=730, description="Days to forecast")


class ProphetIndicatorsRequest(BaseModel):
    """Request for indicator forecasts (volatility, RSI)."""

    symbol: str = Field(..., description="Ticker symbol")
    period: str = Field("5y", description="Data period for training")
    interval: str = Field("1d", description="Data interval")
    forecast_periods: int = Field(365, ge=30, le=730, description="Days to forecast")


# ============== Response Schemas ==============

class ProphetForecastMetrics(BaseModel):
    """Metrics for a forecast."""

    mape: Optional[float] = Field(None, description="Mean Absolute Percentage Error (%)")
    rmse: Optional[float] = Field(None, description="Root Mean Square Error")


class ProphetHorizonSummary(BaseModel):
    """Summary of forecast for a single horizon."""

    horizon: str
    display_name: str
    color: str
    training_end_date: str
    forecast_start_date: str
    metrics: ProphetForecastMetrics
    last_actual_value: float
    forecast_30d: Optional[float] = None
    forecast_90d: Optional[float] = None
    forecast_365d: Optional[float] = None


class ProphetAnalysisResponse(BaseModel):
    """Full Prophet analysis response."""

    symbol: str
    timestamp: datetime
    period: str
    interval: str
    forecast_periods: int

    # Forecasts by type
    price_forecasts: List[ForecastSeries]
    volatility_forecasts: List[ForecastSeries]
    rsi_forecasts: List[ForecastSeries]

    # Summaries for quick display
    price_summaries: List[ProphetHorizonSummary]

    # Cache info
    from_cache: bool = False
    warning: Optional[str] = None


class ProphetPriceResponse(BaseModel):
    """Price-only forecast response."""

    symbol: str
    timestamp: datetime
    forecasts: List[ForecastSeries]
    summaries: List[ProphetHorizonSummary]
    warning: Optional[str] = None


class ProphetIndicatorsResponse(BaseModel):
    """Indicator forecast response."""

    symbol: str
    timestamp: datetime
    volatility_forecasts: List[ForecastSeries]
    rsi_forecasts: List[ForecastSeries]
    warning: Optional[str] = None


class ProphetComponentsResponse(BaseModel):
    """Response with seasonal components."""

    symbol: str
    horizon: str
    components: ComponentSeries
    warning: Optional[str] = None
