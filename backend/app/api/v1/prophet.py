"""Prophet forecasting API endpoints."""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
import pandas as pd

from app.services.data_provider import DataProvider, get_data_provider
from app.services.prophet import (
    ProphetForecaster,
    ProphetConfig,
    ForecastHorizon,
    get_prophet_cache,
    ProphetCache,
    calculate_backtest_metrics,
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
    ProphetBacktestRequest,
    ProphetBacktestResponse,
    ProphetBacktestMetrics,
    BacktestDataPoint,
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


@router.post("/backtest", response_model=ProphetBacktestResponse)
async def backtest_prophet(
    request: ProphetBacktestRequest,
    data_provider: DataProvider = Depends(get_data_provider),
):
    """
    Prophet Backtest: Train on data BEFORE cutoff_date, then compare forecast
    to actual prices.

    CRITICAL: NO data after cutoff_date is used for training!
    This allows validating Prophet's predictive accuracy on historical data.
    """
    # Validate cutoff date
    try:
        cutoff_dt = datetime.strptime(request.cutoff_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="cutoff_date must be in YYYY-MM-DD format"
        )

    today = datetime.utcnow().date()
    if cutoff_dt.date() >= today:
        raise HTTPException(
            status_code=400,
            detail="cutoff_date must be in the past"
        )

    # Fetch market data
    ohlcv_data, warning = data_provider.get_ohlcv(
        request.symbol,
        period=request.period,
        interval=request.interval,
    )

    if not ohlcv_data.candles:
        raise HTTPException(status_code=404, detail="No data available for symbol")

    # Convert to DataFrame
    df, data_tz = _candles_to_dataframe(ohlcv_data.candles)

    # Create timezone-aware cutoff timestamp if data has timezone
    cutoff_ts = pd.Timestamp(cutoff_dt)
    if data_tz is not None and df.index.tz is not None:
        cutoff_ts = cutoff_ts.tz_localize(df.index.tz)

    # Check if we have data before cutoff
    if df.index.min() >= cutoff_ts:
        raise HTTPException(
            status_code=400,
            detail=f"No data available before cutoff_date {request.cutoff_date}"
        )

    # Create Prophet config
    config = ProphetConfig(
        yearly_seasonality=request.yearly_seasonality,
        weekly_seasonality=request.weekly_seasonality,
        changepoint_prior_scale=request.changepoint_prior_scale,
        interval_width=request.interval_width,
    )

    # Create forecaster and run backtest
    forecaster = ProphetForecaster(config=config)

    try:
        result, full_df = forecaster.backtest_forecast(
            df, request.cutoff_date, request.forecast_periods
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Prophet backtest failed: {str(e)}"
        )

    # Get actual prices after cutoff for comparison
    # Reuse cutoff_ts from earlier (already timezone-aware if needed)
    actual_df = full_df[full_df.index >= cutoff_ts].copy()

    # Get forecast data
    forecast_df = result.forecast_df.copy()
    forecast_df["ds"] = pd.to_datetime(forecast_df["ds"])
    forecast_df = forecast_df.set_index("ds")

    # Calculate metrics - compare actual vs forecast
    actual_series = actual_df["Close"]
    forecast_series = forecast_df["yhat"]

    metrics_dict = calculate_backtest_metrics(actual_series, forecast_series)

    metrics = ProphetBacktestMetrics(
        mape=metrics_dict["mape"],
        rmse=metrics_dict["rmse"],
        mae=metrics_dict["mae"],
        correlation=metrics_dict["correlation"],
        r_squared=metrics_dict["r_squared"],
        direction_accuracy=metrics_dict["direction_accuracy"],
        days_forecasted=metrics_dict["days_forecasted"],
        days_with_actual=metrics_dict["days_with_actual"],
    )

    # Create comparison data points
    comparison_data = []
    common_idx = actual_series.index.intersection(forecast_series.index)

    for idx in common_idx:
        actual_val = float(actual_series.loc[idx])
        forecast_val = float(forecast_series.loc[idx])
        lower_val = float(forecast_df.loc[idx, "yhat_lower"])
        upper_val = float(forecast_df.loc[idx, "yhat_upper"])
        error = actual_val - forecast_val
        error_pct = (error / actual_val * 100) if actual_val != 0 else 0

        # Format timestamp
        if data_tz is not None:
            if idx.tzinfo is None:
                if hasattr(data_tz, 'localize'):
                    ts = data_tz.localize(idx)
                else:
                    ts = idx.replace(tzinfo=data_tz)
            else:
                ts = idx
            ts_str = ts.isoformat()
        else:
            ts_str = idx.strftime("%Y-%m-%dT00:00:00+00:00")

        comparison_data.append(BacktestDataPoint(
            timestamp=ts_str,
            actual=actual_val,
            forecast=forecast_val,
            lower=lower_val,
            upper=upper_val,
            error=round(error, 4),
            error_pct=round(error_pct, 4),
        ))

    # Create actual prices series for response
    actual_prices = []
    for idx, row in actual_df.iterrows():
        if data_tz is not None:
            if idx.tzinfo is None:
                if hasattr(data_tz, 'localize'):
                    ts = data_tz.localize(idx)
                else:
                    ts = idx.replace(tzinfo=data_tz)
            else:
                ts = idx
            ts_str = ts.isoformat()
        else:
            ts_str = idx.strftime("%Y-%m-%dT00:00:00+00:00")

        actual_prices.append(ForecastDataPoint(
            timestamp=ts_str,
            value=float(row["Close"]),
            lower=float(row["Close"]),  # Actual has no confidence bands
            upper=float(row["Close"]),
            is_forecast=False,
        ))

    # Create backtest forecast series
    backtest_series = []
    # Use naive cutoff for comparison with forecast_df (Prophet returns naive timestamps)
    cutoff_naive = pd.Timestamp(cutoff_dt)
    for idx, row in forecast_df.iterrows():
        # Compare with naive timestamp (Prophet forecast is tz-naive)
        idx_naive = idx.tz_localize(None) if idx.tzinfo is not None else idx
        if idx_naive < cutoff_naive:
            continue  # Only include forecast period

        if data_tz is not None:
            if idx.tzinfo is None:
                if hasattr(data_tz, 'localize'):
                    ts = data_tz.localize(idx)
                else:
                    ts = idx.replace(tzinfo=data_tz)
            else:
                ts = idx
            ts_str = ts.isoformat()
        else:
            ts_str = idx.strftime("%Y-%m-%dT00:00:00+00:00")

        backtest_series.append(ForecastDataPoint(
            timestamp=ts_str,
            value=float(row["yhat"]),
            lower=float(row["yhat_lower"]),
            upper=float(row["yhat_upper"]),
            is_forecast=True,
        ))

    # Calculate forecast end date
    if len(backtest_series) > 0:
        forecast_end_date = backtest_series[-1].timestamp[:10]
    else:
        forecast_end_date = request.cutoff_date

    backtest_forecast = ForecastSeries(
        horizon="backtest",
        display_name="Backtest",
        color="#9333ea",  # Purple
        training_end_date=result.training_end_date,
        forecast_start_date=request.cutoff_date,
        mape=metrics.mape,
        rmse=metrics.rmse,
        series=backtest_series,
    )

    return ProphetBacktestResponse(
        symbol=request.symbol.upper(),
        timestamp=datetime.utcnow(),
        cutoff_date=request.cutoff_date,
        today_date=today.strftime("%Y-%m-%d"),
        forecast_end_date=forecast_end_date,
        actual_prices=actual_prices,
        backtest_forecast=backtest_forecast,
        metrics=metrics,
        comparison_data=comparison_data,
        from_cache=False,
        warning=warning,
    )
