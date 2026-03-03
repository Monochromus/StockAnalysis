"""XGBoost hybrid forecasting API endpoints."""

from datetime import datetime
from typing import List
import pandas as pd
import logging

from fastapi import APIRouter, Depends, HTTPException

from app.services.data_provider import DataProvider, get_data_provider
from app.services.prophet import (
    ProphetForecaster,
    ProphetConfig,
    ForecastHorizon,
    get_prophet_cache,
    ProphetCache,
)
from app.services.xgboost import (
    XGBoostResidualCorrector,
    XGBoostConfig,
    get_xgboost_cache,
    XGBoostCache,
)
from app.schemas.xgboost import (
    XGBoostAnalysisRequest,
    XGBoostAnalysisResponse,
    XGBoostComparisonResponse,
    XGBoostSettings,
    XGBoostFeatureToggles,
    XGBoostMetricsSchema,
    HybridForecastSeries,
    HybridForecastDataPoint,
    FeatureImportanceItem,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _candles_to_dataframe(candles):
    """Convert candle list to pandas DataFrame for XGBoost."""
    data = []
    for c in candles:
        data.append({
            "timestamp": c.timestamp,
            "open": c.open,
            "high": c.high,
            "low": c.low,
            "close": c.close,
            "volume": c.volume,
        })
    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def _settings_to_config(
    settings: XGBoostSettings,
    toggles: XGBoostFeatureToggles
) -> XGBoostConfig:
    """Convert API settings to XGBoostConfig."""
    return XGBoostConfig(
        n_estimators=settings.n_estimators,
        max_depth=settings.max_depth,
        learning_rate=settings.learning_rate,
        subsample=settings.subsample,
        colsample_bytree=settings.colsample_bytree,
        min_child_weight=settings.min_child_weight,
        reg_alpha=settings.reg_alpha,
        reg_lambda=settings.reg_lambda,
        use_time_features=toggles.use_time_features,
        use_lag_features=toggles.use_lag_features,
        use_rolling_features=toggles.use_rolling_features,
        use_prophet_components=toggles.use_prophet_components,
        use_market_structure=toggles.use_market_structure,
    )


@router.post("/analyze", response_model=XGBoostAnalysisResponse)
async def analyze_hybrid(
    request: XGBoostAnalysisRequest,
    data_provider: DataProvider = Depends(get_data_provider),
    cache: XGBoostCache = Depends(get_xgboost_cache),
    prophet_cache: ProphetCache = Depends(get_prophet_cache),
):
    """
    Perform XGBoost hybrid analysis (Prophet + XGBoost residual correction).

    This endpoint:
    1. Runs Prophet forecast first
    2. Trains XGBoost on Prophet residuals
    3. Returns hybrid forecast with metrics comparison
    """
    # Default settings if not provided
    settings = request.settings or XGBoostSettings()
    toggles = request.feature_toggles or XGBoostFeatureToggles()

    # Check cache first
    if not request.force_refresh:
        cached = cache.get(request.symbol, request.period, request.interval)
        if cached is not None:
            # Return cached result with metrics and feature importance
            hybrid_series = _result_to_hybrid_series(
                cached.result,
                ForecastHorizon.get_defaults()[0]  # long_term
            )

            return XGBoostAnalysisResponse(
                symbol=request.symbol.upper(),
                timestamp=cached.created_at,
                period=request.period,
                interval=request.interval,
                forecast_periods=request.forecast_periods,
                hybrid_forecasts=[hybrid_series],
                metrics=_metrics_to_schema(cached.result.metrics) if cached.result.metrics else None,
                feature_importance=[
                    FeatureImportanceItem(
                        feature_name=f.feature_name,
                        importance=f.importance,
                        rank=f.rank
                    ) for f in cached.result.feature_importance
                ],
                settings=settings,
                feature_toggles=toggles,
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

    # Convert to DataFrame
    df = _candles_to_dataframe(ohlcv_data.candles)

    # Also create OHLCV format for Prophet
    df_prophet = pd.DataFrame({
        "Open": df["open"].values,
        "High": df["high"].values,
        "Low": df["low"].values,
        "Close": df["close"].values,
        "Volume": df["volume"].values,
    }, index=pd.to_datetime(df["timestamp"].values))

    # Step 1: Get all three Prophet forecasts and combine them
    logger.info(f"Getting Prophet forecasts for {request.symbol}...")

    prophet_config = ProphetConfig()
    forecaster = ProphetForecaster(config=prophet_config)

    try:
        # Train all three horizons (long_term, mid_term, short_term)
        price_forecasts = forecaster.forecast_price(df_prophet, request.forecast_periods)

        logger.info(
            f"Prophet forecasts generated: {list(price_forecasts.keys())}"
        )

        # Combine all three horizons with weighted averaging
        # Effects consistent across all horizons get amplified
        # Short-term-only effects get diluted
        # Weights based on years of training data:
        #   long_term: 5 years → weight 5
        #   mid_term: 2 years → weight 2
        #   short_term: 0.5 years → weight 0.5
        combined_result = forecaster.combine_forecasts(price_forecasts)
        prophet_forecast_df = combined_result.forecast_df

        logger.info(
            f"Combined forecast created with {len(prophet_forecast_df)} data points, "
            f"columns: {list(prophet_forecast_df.columns)}, "
            f"ds dtype: {prophet_forecast_df['ds'].dtype}"
        )

        # Check for NaN values in the combined forecast
        nan_count = prophet_forecast_df["yhat"].isna().sum()
        if nan_count > 0:
            logger.warning(f"Combined forecast has {nan_count} NaN values in yhat")

        # Log date range
        if len(prophet_forecast_df) > 0:
            logger.info(
                f"Date range: {prophet_forecast_df['ds'].iloc[0]} to {prophet_forecast_df['ds'].iloc[-1]}"
            )

    except Exception as e:
        logger.error(f"Prophet forecast failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Prophet forecast failed: {str(e)}"
        )

    # Step 2: Train XGBoost on residuals
    logger.info("Training XGBoost residual corrector...")
    xgb_config = _settings_to_config(settings, toggles)
    corrector = XGBoostResidualCorrector(config=xgb_config)

    try:
        # Actual prices
        actual_prices = pd.Series(df["close"].values)

        # Train XGBoost
        metrics = corrector.fit(df, prophet_forecast_df, actual_prices)

        # Generate hybrid predictions
        hybrid_result = corrector.predict_hybrid(df, prophet_forecast_df, actual_prices)

    except Exception as e:
        logger.error(f"XGBoost training failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"XGBoost training failed: {str(e)}"
        )

    # Cache results
    cache.set(
        request.symbol,
        request.period,
        request.interval,
        corrector,
        hybrid_result
    )

    # Convert to response format - use combined horizon config
    horizon_config = ForecastHorizon.get_combined()
    hybrid_series = _result_to_hybrid_series(hybrid_result, horizon_config)

    logger.info(
        f"XGBoost analysis complete for {request.symbol}. "
        f"Hybrid series has {len(hybrid_series.series)} data points, "
        f"horizon: {hybrid_series.horizon}, "
        f"training_end_date: {hybrid_series.training_end_date}"
    )

    return XGBoostAnalysisResponse(
        symbol=request.symbol.upper(),
        timestamp=datetime.utcnow(),
        period=request.period,
        interval=request.interval,
        forecast_periods=request.forecast_periods,
        hybrid_forecasts=[hybrid_series],
        metrics=_metrics_to_schema(hybrid_result.metrics) if hybrid_result.metrics else None,
        feature_importance=[
            FeatureImportanceItem(
                feature_name=f.feature_name,
                importance=f.importance,
                rank=f.rank
            ) for f in hybrid_result.feature_importance
        ],
        settings=settings,
        feature_toggles=toggles,
        from_cache=False,
        warning=warning,
    )


@router.get("/comparison/{symbol}", response_model=XGBoostComparisonResponse)
async def get_comparison(
    symbol: str,
    period: str = "5y",
    interval: str = "1d",
    data_provider: DataProvider = Depends(get_data_provider),
    cache: XGBoostCache = Depends(get_xgboost_cache),
):
    """
    Get Prophet vs Hybrid comparison for a symbol.

    Returns summary metrics and forecast values.
    """
    # Check if we have cached results
    cached = cache.get(symbol, period, interval)

    if cached is None:
        raise HTTPException(
            status_code=404,
            detail="No XGBoost analysis found. Run /analyze first."
        )

    result = cached.result

    # Get forecast values at 30d and 90d if available
    prophet_30d = None
    prophet_90d = None
    hybrid_30d = None
    hybrid_90d = None

    if len(result.prophet_predictions) >= 30:
        prophet_30d = result.prophet_predictions[29]
        hybrid_30d = result.hybrid_predictions[29]

    if len(result.prophet_predictions) >= 90:
        prophet_90d = result.prophet_predictions[89]
        hybrid_90d = result.hybrid_predictions[89]

    return XGBoostComparisonResponse(
        symbol=symbol.upper(),
        timestamp=cached.created_at,
        prophet_last_value=result.prophet_predictions[-1] if result.prophet_predictions else 0,
        prophet_forecast_30d=prophet_30d,
        prophet_forecast_90d=prophet_90d,
        hybrid_last_value=result.hybrid_predictions[-1] if result.hybrid_predictions else 0,
        hybrid_forecast_30d=hybrid_30d,
        hybrid_forecast_90d=hybrid_90d,
        metrics=_metrics_to_schema(result.metrics) if result.metrics else XGBoostMetricsSchema(
            prophet_mae=0, prophet_rmse=0, prophet_mape=0, prophet_r2=0,
            hybrid_mae=0, hybrid_rmse=0, hybrid_mape=0, hybrid_r2=0,
            mae_improvement_pct=0, rmse_improvement_pct=0, mape_improvement_pct=0, r2_improvement_pct=0
        ),
        feature_importance=[
            FeatureImportanceItem(
                feature_name=f.feature_name,
                importance=f.importance,
                rank=f.rank
            ) for f in result.feature_importance
        ],
    )


def _result_to_hybrid_series(
    result,
    horizon_config: ForecastHorizon
) -> HybridForecastSeries:
    """Convert HybridForecastResult to HybridForecastSeries schema."""
    training_end_date = result.training_end_date

    series = []
    for i, date in enumerate(result.dates):
        is_forecast = date > training_end_date if isinstance(date, str) else str(date) > training_end_date

        series.append(HybridForecastDataPoint(
            timestamp=str(date),
            prophet_value=result.prophet_predictions[i],
            hybrid_value=result.hybrid_predictions[i],
            lower=result.lower_bound[i],
            upper=result.upper_bound[i],
            is_forecast=is_forecast,
        ))

    return HybridForecastSeries(
        horizon=horizon_config.name,
        display_name=horizon_config.display_name,
        color="#8B7355",  # Calm brown for hybrid
        training_end_date=result.training_end_date,
        forecast_start_date=result.forecast_start_date,
        series=series,
    )


def _metrics_to_schema(metrics) -> XGBoostMetricsSchema:
    """Convert XGBoostMetrics to schema."""
    return XGBoostMetricsSchema(
        prophet_mae=metrics.prophet_mae,
        prophet_rmse=metrics.prophet_rmse,
        prophet_mape=metrics.prophet_mape,
        prophet_r2=metrics.prophet_r2,
        hybrid_mae=metrics.hybrid_mae,
        hybrid_rmse=metrics.hybrid_rmse,
        hybrid_mape=metrics.hybrid_mape,
        hybrid_r2=metrics.hybrid_r2,
        mae_improvement_pct=metrics.mae_improvement_pct,
        rmse_improvement_pct=metrics.rmse_improvement_pct,
        mape_improvement_pct=metrics.mape_improvement_pct,
        r2_improvement_pct=metrics.r2_improvement_pct,
    )
