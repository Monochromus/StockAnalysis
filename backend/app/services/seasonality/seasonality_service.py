"""Seasonality analysis service using Prophet yearly component and historical returns."""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging
import calendar

logger = logging.getLogger(__name__)


@dataclass
class MonthlyReturnData:
    """Monthly return statistics."""

    month: int
    avg_return: float
    median_return: float
    std_dev: float
    positive_pct: float
    sample_size: int


@dataclass
class DailySeasonalityData:
    """Daily seasonality data from Prophet."""

    day_of_year: int
    month: int
    day: int
    value: float
    is_bullish: bool


@dataclass
class SeasonalityResult:
    """Complete seasonality analysis result."""

    monthly_returns: List[MonthlyReturnData]
    daily_seasonality: List[DailySeasonalityData]


class SeasonalityService:
    """
    Service for calculating seasonality patterns from historical data.

    Uses:
    1. Prophet yearly seasonality component for daily patterns
    2. Historical monthly returns for performance statistics
    """

    def __init__(self):
        """Initialize the seasonality service."""
        pass

    def calculate_monthly_returns(self, df: pd.DataFrame) -> List[MonthlyReturnData]:
        """
        Calculate historical monthly return statistics.

        Args:
            df: DataFrame with datetime index and 'Close' column

        Returns:
            List of MonthlyReturnData for each month (1-12)
        """
        # Ensure we have a datetime index
        if not isinstance(df.index, pd.DatetimeIndex):
            df = df.copy()
            df.index = pd.to_datetime(df.index)

        # Calculate monthly returns
        # First, resample to monthly and get last close of each month
        # Use "M" for compatibility with older pandas versions (< 2.2)
        monthly_closes = df["Close"].resample("M").last()

        # Calculate month-over-month returns
        monthly_returns = monthly_closes.pct_change().dropna()

        # Group by calendar month
        monthly_returns_df = pd.DataFrame({
            "return": monthly_returns,
            "month": monthly_returns.index.month,
            "year": monthly_returns.index.year,
        })

        results = []
        for month in range(1, 13):
            month_data = monthly_returns_df[monthly_returns_df["month"] == month]["return"]

            if len(month_data) > 0:
                avg_return = float(month_data.mean() * 100)  # Convert to percentage
                median_return = float(month_data.median() * 100)
                std_dev = float(month_data.std() * 100) if len(month_data) > 1 else 0.0
                positive_pct = float((month_data > 0).sum() / len(month_data) * 100)
                sample_size = len(month_data)
            else:
                avg_return = 0.0
                median_return = 0.0
                std_dev = 0.0
                positive_pct = 0.0
                sample_size = 0

            results.append(MonthlyReturnData(
                month=month,
                avg_return=avg_return,
                median_return=median_return,
                std_dev=std_dev,
                positive_pct=positive_pct,
                sample_size=sample_size,
            ))

        return results

    def extract_yearly_pattern(self, df: pd.DataFrame) -> List[DailySeasonalityData]:
        """
        Calculate actual daily average returns for each day of the year.

        Args:
            df: DataFrame with datetime index and 'Close' column

        Returns:
            List of DailySeasonalityData for each day of the year
        """
        # Ensure we have a datetime index
        if not isinstance(df.index, pd.DatetimeIndex):
            df = df.copy()
            df.index = pd.to_datetime(df.index)

        # Calculate daily returns
        daily_returns = df["Close"].pct_change().dropna() * 100  # Convert to percentage

        # Create a DataFrame with month and day
        returns_df = pd.DataFrame({
            "return": daily_returns,
            "month": daily_returns.index.month,
            "day": daily_returns.index.day,
        })

        # Group by month and day, calculate average return
        daily_avg = returns_df.groupby(["month", "day"])["return"].mean()

        # Build results for all days of a non-leap year
        results = []
        day_of_year = 0

        for month in range(1, 13):
            # Get number of days in this month (use non-leap year)
            days_in_month = calendar.monthrange(2023, month)[1]

            for day in range(1, days_in_month + 1):
                day_of_year += 1

                # Get average return for this day, default to 0 if not enough data
                try:
                    avg_return = float(daily_avg.loc[(month, day)])
                except KeyError:
                    avg_return = 0.0

                results.append(DailySeasonalityData(
                    day_of_year=day_of_year,
                    month=month,
                    day=day,
                    value=avg_return,
                    is_bullish=avg_return > 0,
                ))

        return results

    def analyze(self, df: pd.DataFrame) -> SeasonalityResult:
        """
        Perform full seasonality analysis.

        Args:
            df: DataFrame with datetime index and OHLCV columns

        Returns:
            SeasonalityResult with monthly returns and daily seasonality
        """
        logger.info("Starting seasonality analysis")

        # Calculate monthly returns
        monthly_returns = self.calculate_monthly_returns(df)
        logger.info(f"Calculated monthly returns for {len(monthly_returns)} months")

        # Extract yearly pattern from Prophet
        daily_seasonality = self.extract_yearly_pattern(df)
        logger.info(f"Extracted daily seasonality for {len(daily_seasonality)} days")

        return SeasonalityResult(
            monthly_returns=monthly_returns,
            daily_seasonality=daily_seasonality,
        )
