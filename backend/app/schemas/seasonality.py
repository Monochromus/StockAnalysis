"""Pydantic schemas for seasonality analysis."""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class MonthlyReturn(BaseModel):
    """Monthly return statistics."""

    month: int = Field(..., ge=1, le=12, description="Month number (1-12)")
    avg_return: float = Field(..., description="Average monthly return")
    median_return: float = Field(..., description="Median monthly return")
    std_dev: float = Field(..., description="Standard deviation of returns")
    positive_pct: float = Field(..., ge=0, le=100, description="Percentage of positive returns")
    sample_size: int = Field(..., ge=0, description="Number of years sampled")


class DailySeasonality(BaseModel):
    """Daily seasonality data point from Prophet yearly component."""

    day_of_year: int = Field(..., ge=1, le=366, description="Day of year (1-366)")
    month: int = Field(..., ge=1, le=12, description="Month number (1-12)")
    day: int = Field(..., ge=1, le=31, description="Day of month (1-31)")
    value: float = Field(..., description="Prophet yearly component value")
    is_bullish: bool = Field(..., description="True if value > 0 (bullish seasonality)")


class SeasonalityAnalysisRequest(BaseModel):
    """Request for seasonality analysis."""

    symbol: str = Field(..., description="Ticker symbol")
    period: str = Field("5y", description="Historical data period")
    interval: str = Field("1d", description="Data interval")


class SeasonalityAnalysisResponse(BaseModel):
    """Full seasonality analysis response."""

    symbol: str = Field(..., description="Ticker symbol")
    timestamp: datetime = Field(..., description="Analysis timestamp")
    monthly_returns: List[MonthlyReturn] = Field(..., description="Monthly return statistics")
    daily_seasonality: List[DailySeasonality] = Field(..., description="Daily seasonality from Prophet")
    warning: Optional[str] = Field(None, description="Warning message if any")
