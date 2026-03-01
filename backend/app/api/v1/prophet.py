"""Prophet forecasting API endpoints."""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.services.data_provider import DataProvider, get_data_provider
from app.services.prophet import (
    ProphetForecaster,
    ProphetConfig,
    ForecastHorizon,
    get_prophet_cache,
    ProphetCache,
)
from app.schemas.prophet import (
    ProphetAnalysisRequest,
    ProphetAnalysisResponse,
    ProphetPriceRequest,
    ProphetPriceResponse,
    ProphetIndicatorsRequest,
    ProphetIndicatorsResponse,
    ProphetComponentsResponse,
    ForecastSeries,
    ForecastDataPoint,
    ComponentSeries,
    ComponentDataPoint,
    ProphetHorizonSummary,
    ProphetForecastMetrics,
)

router = APIRouter()


def _candles_to_dataframe(candles):
    """Convert candle list to pandas DataFrame.

    Returns:
        Tuple of (DataFrame, timezone) where timezone is from the candle data
    """
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

    # Extract timezone from the first candle
    data_tz = None
    if len(candles) > 0 and hasattr(candles[0].timestamp, 'tzinfo'):
        data_tz = candles[0].timestamp.tzinfo

    return df, data_tz


def _forecast_result_to_series(
    result,
    horizon_config: ForecastHorizon,
    data_timezone=None
) -> ForecastSeries:
    """Convert ForecastResult to ForecastSeries schema.

    Args:
        result: ForecastResult from ProphetForecaster
        horizon_config: Horizon configuration
        data_timezone: Timezone from original candle data (optional)
    """
    import pandas as pd
    import pytz

    df = result.forecast_df
    training_end = pd.to_datetime(result.training_end_date)

    series = []
    for _, row in df.iterrows():
        ts = row["ds"]
        # Format timestamp with timezone if available
        if data_timezone is not None:
            # Localize naive datetime to the data timezone
            if ts.tzinfo is None:
                # Check if it's a pytz timezone (has localize method) or stdlib timezone
                if hasattr(data_timezone, 'localize'):
                    ts = data_timezone.localize(ts)
                else:
                    # Standard library timezone (e.g., datetime.timezone.utc)
                    ts = ts.replace(tzinfo=data_timezone)
            ts_str = ts.isoformat()
        else:
            # Fallback to UTC
            ts_str = ts.strftime("%Y-%m-%dT00:00:00+00:00")

        series.append(ForecastDataPoint(
            timestamp=ts_str,
            value=float(row["yhat"]),
            lower=float(row["yhat_lower"]),
            upper=float(row["yhat_upper"]),
            is_forecast=row["ds"] > training_end,
        ))

    return ForecastSeries(
        horizon=horizon_config.name,
        display_name=horizon_config.display_name,
        color=horizon_config.color,
        training_end_date=result.training_end_date,
        forecast_start_date=result.forecast_start_date,
        mape=result.mape,
        rmse=result.rmse,
        series=series,
    )


def _create_horizon_summary(
    result,
    horizon_config: ForecastHorizon,
    last_actual_value: float
) -> ProphetHorizonSummary:
    """Create summary for a forecast horizon."""
    import pandas as pd

    df = result.forecast_df
    training_end = pd.to_datetime(result.training_end_date)

    # Get forecast values at specific horizons
    forecast_only = df[df["ds"] > training_end]

    forecast_30d = None
    forecast_90d = None
    forecast_365d = None

    if len(forecast_only) >= 30:
        forecast_30d = float(forecast_only.iloc[29]["yhat"])
    if len(forecast_only) >= 90:
        forecast_90d = float(forecast_only.iloc[89]["yhat"])
    if len(forecast_only) >= 365:
        forecast_365d = float(forecast_only.iloc[364]["yhat"])

    return ProphetHorizonSummary(
        horizon=horizon_config.name,
        display_name=horizon_config.display_name,
        color=horizon_config.color,
        training_end_date=result.training_end_date,
        forecast_start_date=result.forecast_start_date,
        metrics=ProphetForecastMetrics(
            mape=result.mape,
            rmse=result.rmse,
        ),
        last_actual_value=last_actual_value,
        forecast_30d=forecast_30d,
        forecast_90d=forecast_90d,
        forecast_365d=forecast_365d,
    )


@router.post("/analyze", response_model=ProphetAnalysisResponse)
async def analyze_prophet(
    request: ProphetAnalysisRequest,
    data_provider: DataProvider = Depends(get_data_provider),
    cache: ProphetCache = Depends(get_prophet_cache),
):
    """
    Perform full Prophet analysis including price, volatility, and RSI forecasts.

    This is the main endpoint for Prophet analysis. It returns forecasts for
    all three metrics across all horizons (long-term, mid-term, short-term).
    """
    # Check cache first
    if not request.force_refresh:
        cached = cache.get(request.symbol, request.period, request.interval)
        if cached is not None:
            return ProphetAnalysisResponse(
                symbol=request.symbol.upper(),
                timestamp=cached.created_at,
                period=request.period,
                interval=request.interval,
                forecast_periods=cached.forecast_periods,
                price_forecasts=cached.forecasts["price_series"],
                volatility_forecasts=cached.forecasts["volatility_series"],
                rsi_forecasts=cached.forecasts["rsi_series"],
                price_summaries=cached.forecasts["price_summaries"],
                from_cache=True,
            )

    # Fetch market data
    ohlcv_data, warning = data_provider.get_ohlcv(
        request.symbol,
        period=request.period,
        interval=request.interval,
    )

    if not ohlcv_data.candles:
        raise HTTPException(status_code=404, detail="No data available for symbol")

    # Convert to DataFrame and extract timezone
    df, data_tz = _candles_to_dataframe(ohlcv_data.candles)

    # Create Prophet config
    config = ProphetConfig(
        yearly_seasonality=request.yearly_seasonality,
        weekly_seasonality=request.weekly_seasonality,
        changepoint_prior_scale=request.changepoint_prior_scale,
        interval_width=request.interval_width,
    )

    # Create forecaster and run analysis
    forecaster = ProphetForecaster(config=config)
    horizons = ForecastHorizon.get_defaults()

    try:
        all_forecasts = forecaster.forecast_all_horizons(df, request.forecast_periods)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Prophet forecast failed: {str(e)}"
        )

    # Convert to response format
    price_series = []
    volatility_series = []
    rsi_series = []
    price_summaries = []

    last_price = float(df["Close"].iloc[-1])

    for horizon in horizons:
        # Price forecasts
        if horizon.name in all_forecasts["price"]:
            result = all_forecasts["price"][horizon.name]
            price_series.append(_forecast_result_to_series(result, horizon, data_tz))
            price_summaries.append(_create_horizon_summary(result, horizon, last_price))

        # Volatility forecasts
        if horizon.name in all_forecasts["volatility"]:
            result = all_forecasts["volatility"][horizon.name]
            volatility_series.append(_forecast_result_to_series(result, horizon, data_tz))

        # RSI forecasts
        if horizon.name in all_forecasts["rsi"]:
            result = all_forecasts["rsi"][horizon.name]
            rsi_series.append(_forecast_result_to_series(result, horizon, data_tz))

    # Cache results
    cache.set(
        request.symbol,
        request.period,
        request.interval,
        {
            "price_series": price_series,
            "volatility_series": volatility_series,
            "rsi_series": rsi_series,
            "price_summaries": price_summaries,
        },
        request.forecast_periods,
    )

    return ProphetAnalysisResponse(
        symbol=request.symbol.upper(),
        timestamp=datetime.utcnow(),
        period=request.period,
        interval=request.interval,
        forecast_periods=request.forecast_periods,
        price_forecasts=price_series,
        volatility_forecasts=volatility_series,
        rsi_forecasts=rsi_series,
        price_summaries=price_summaries,
        from_cache=False,
        warning=warning,
    )


@router.post("/forecast/price", response_model=ProphetPriceResponse)
async def forecast_price(
    request: ProphetPriceRequest,
    data_provider: DataProvider = Depends(get_data_provider),
):
    """
    Forecast prices only, without volatility and RSI.

    Use this for faster analysis when only price forecasts are needed.
    """
    # Fetch market data
    ohlcv_data, warning = data_provider.get_ohlcv(
        request.symbol,
        period=request.period,
        interval=request.interval,
    )

    if not ohlcv_data.candles:
        raise HTTPException(status_code=404, detail="No data available for symbol")

    # Convert to DataFrame and extract timezone
    df, data_tz = _candles_to_dataframe(ohlcv_data.candles)

    # Create forecaster
    forecaster = ProphetForecaster()
    horizons = ForecastHorizon.get_defaults()

    try:
        price_forecasts = forecaster.forecast_price(df, request.forecast_periods)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Prophet price forecast failed: {str(e)}"
        )

    # Convert to response format
    forecast_series = []
    summaries = []
    last_price = float(df["Close"].iloc[-1])

    for horizon in horizons:
        if horizon.name in price_forecasts:
            result = price_forecasts[horizon.name]
            forecast_series.append(_forecast_result_to_series(result, horizon, data_tz))
            summaries.append(_create_horizon_summary(result, horizon, last_price))

    return ProphetPriceResponse(
        symbol=request.symbol.upper(),
        timestamp=datetime.utcnow(),
        forecasts=forecast_series,
        summaries=summaries,
        warning=warning,
    )


@router.post("/forecast/indicators", response_model=ProphetIndicatorsResponse)
async def forecast_indicators(
    request: ProphetIndicatorsRequest,
    data_provider: DataProvider = Depends(get_data_provider),
):
    """
    Forecast volatility and RSI only.

    Use this for indicator-focused analysis.
    """
    # Fetch market data
    ohlcv_data, warning = data_provider.get_ohlcv(
        request.symbol,
        period=request.period,
        interval=request.interval,
    )

    if not ohlcv_data.candles:
        raise HTTPException(status_code=404, detail="No data available for symbol")

    # Convert to DataFrame and extract timezone
    df, data_tz = _candles_to_dataframe(ohlcv_data.candles)

    # Create forecaster
    forecaster = ProphetForecaster()
    horizons = ForecastHorizon.get_defaults()

    try:
        indicator_forecasts = forecaster.forecast_indicators(df, request.forecast_periods)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Prophet indicator forecast failed: {str(e)}"
        )

    # Convert to response format
    volatility_series = []
    rsi_series = []

    for horizon in horizons:
        if horizon.name in indicator_forecasts["volatility"]:
            result = indicator_forecasts["volatility"][horizon.name]
            volatility_series.append(_forecast_result_to_series(result, horizon, data_tz))

        if horizon.name in indicator_forecasts["rsi"]:
            result = indicator_forecasts["rsi"][horizon.name]
            rsi_series.append(_forecast_result_to_series(result, horizon, data_tz))

    return ProphetIndicatorsResponse(
        symbol=request.symbol.upper(),
        timestamp=datetime.utcnow(),
        volatility_forecasts=volatility_series,
        rsi_forecasts=rsi_series,
        warning=warning,
    )


@router.get("/components/{symbol}", response_model=ProphetComponentsResponse)
async def get_components(
    symbol: str,
    horizon: str = "long_term",
    period: str = "5y",
    interval: str = "1d",
    data_provider: DataProvider = Depends(get_data_provider),
):
    """
    Get seasonal components (trend, weekly, monthly, yearly) for a symbol.

    Components are extracted from a trained Prophet model.
    """
    valid_horizons = ["long_term", "mid_term", "short_term"]
    if horizon not in valid_horizons:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid horizon. Must be one of: {valid_horizons}"
        )

    # Fetch market data
    ohlcv_data, warning = data_provider.get_ohlcv(
        symbol,
        period=period,
        interval=interval,
    )

    if not ohlcv_data.candles:
        raise HTTPException(status_code=404, detail="No data available for symbol")

    # Convert to DataFrame (timezone not needed for components)
    df, _ = _candles_to_dataframe(ohlcv_data.candles)

    # Create forecaster and train model
    forecaster = ProphetForecaster()

    try:
        forecaster.forecast_price(df, periods=365)
        components = forecaster.get_components(horizon)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get components: {str(e)}"
        )

    if components is None:
        raise HTTPException(
            status_code=404,
            detail=f"No components available for horizon: {horizon}"
        )

    # Convert to response format
    component_series = ComponentSeries(
        trend=[ComponentDataPoint(ds=p["ds"], value=p["value"]) for p in components.trend],
        weekly=[ComponentDataPoint(ds=p["ds"], value=p["value"]) for p in components.weekly] if components.weekly else None,
        monthly=[ComponentDataPoint(ds=p["ds"], value=p["value"]) for p in components.monthly] if components.monthly else None,
        yearly=[ComponentDataPoint(ds=p["ds"], value=p["value"]) for p in components.yearly] if components.yearly else None,
    )

    return ProphetComponentsResponse(
        symbol=symbol.upper(),
        horizon=horizon,
        components=component_series,
        warning=warning,
    )
