"""Seasonality analysis API endpoints."""

from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException

from app.services.data_provider import DataProvider, get_data_provider
from app.services.seasonality import SeasonalityService
from app.schemas.seasonality import (
    SeasonalityAnalysisRequest,
    SeasonalityAnalysisResponse,
    MonthlyReturn,
    DailySeasonality,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _candles_to_dataframe(candles):
    """Convert candle list to pandas DataFrame."""
    import pandas as pd

    data = []
    for c in candles:
        data.append({
            "Open": c.open,
            "High": c.high,
            "Low": c.low,
            "Close": c.close,
            "Volume": c.volume,
        })
    df = pd.DataFrame(data, index=[c.timestamp for c in candles])
    df.index = pd.to_datetime(df.index)
    return df


@router.post("/analyze", response_model=SeasonalityAnalysisResponse)
async def analyze_seasonality(
    request: SeasonalityAnalysisRequest,
    data_provider: DataProvider = Depends(get_data_provider),
):
    """
    Perform seasonality analysis for a symbol.

    Returns:
    - Monthly return statistics (avg, median, std dev, positive %)
    - Daily seasonality pattern from Prophet yearly component
    """
    logger.info(f"Seasonality analysis requested for {request.symbol}")

    # Fetch market data
    ohlcv_data, warning = data_provider.get_ohlcv(
        request.symbol,
        period=request.period,
        interval=request.interval,
    )

    if not ohlcv_data.candles:
        raise HTTPException(status_code=404, detail="No data available for symbol")

    # Convert to DataFrame
    df = _candles_to_dataframe(ohlcv_data.candles)

    # Create service and analyze
    service = SeasonalityService()

    try:
        result = service.analyze(df)
    except Exception as e:
        logger.error(f"Seasonality analysis failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Seasonality analysis failed: {str(e)}"
        )

    # Convert to response format
    monthly_returns = [
        MonthlyReturn(
            month=mr.month,
            avg_return=mr.avg_return,
            median_return=mr.median_return,
            std_dev=mr.std_dev,
            positive_pct=mr.positive_pct,
            sample_size=mr.sample_size,
        )
        for mr in result.monthly_returns
    ]

    daily_seasonality = [
        DailySeasonality(
            day_of_year=ds.day_of_year,
            month=ds.month,
            day=ds.day,
            value=ds.value,
            is_bullish=ds.is_bullish,
        )
        for ds in result.daily_seasonality
    ]

    return SeasonalityAnalysisResponse(
        symbol=request.symbol.upper(),
        timestamp=datetime.utcnow(),
        monthly_returns=monthly_returns,
        daily_seasonality=daily_seasonality,
        warning=warning,
    )
