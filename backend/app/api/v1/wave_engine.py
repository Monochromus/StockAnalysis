"""
Wave Engine API endpoints.

Provides endpoints for:
- Full wave analysis with DFA and adaptive thresholds
- DFA-only calculations
- Regime detection
- Threshold calculation
- Configuration management
"""

from datetime import datetime
from typing import Optional
import numpy as np

from fastapi import APIRouter, Query, HTTPException

from app.schemas.wave_engine import (
    WaveEngineRequest,
    WaveEngineResponse,
    DFAOnlyResponse,
    RegimeOnlyResponse,
    ThresholdOnlyResponse,
    ConfigValidationResponse,
    EngineConfigSchema,
    DFAResultSchema,
    RegimeStateSchema,
    ThresholdResultSchema,
    EnhancedPivotSchema,
    RegimeEventSchema,
    ConfidenceComponentsSchema,
    RegimeType as SchemaRegimeType,
    PivotType as SchemaPivotType,
    PivotStatus as SchemaPivotStatus,
)
from app.services.wave_engine import EngineConfig, DFAConfig, ThresholdConfig, RegimeConfig, ConfidenceWeights
from app.services.wave_engine.engine import WaveEngine
from app.services.wave_engine.config import TimeframeLevel
from app.services.data_provider import DataProvider

router = APIRouter()


def _config_schema_to_internal(schema: Optional[EngineConfigSchema]) -> EngineConfig:
    """Convert API schema to internal config."""
    if schema is None:
        return EngineConfig()

    return EngineConfig(
        dfa=DFAConfig(
            window_size=schema.dfa.window_size,
            polynomial_order=schema.dfa.polynomial_order,
            min_segment_size=schema.dfa.min_segment_size,
            max_segment_ratio=schema.dfa.max_segment_ratio,
        ),
        threshold=ThresholdConfig(
            atr_period=schema.threshold.atr_period,
            beta_min=schema.threshold.beta_min,
            beta_max=schema.threshold.beta_max,
            sigmoid_k=schema.threshold.sigmoid_k,
            alpha_mid=schema.threshold.alpha_mid,
        ),
        regime=RegimeConfig(
            ewma_lambda_slow=schema.regime.ewma_lambda_slow,
            ewma_lambda_fast=schema.regime.ewma_lambda_fast,
            regime_change_threshold=schema.regime.regime_change_threshold,
            trending_threshold=schema.regime.trending_threshold,
            mean_reverting_threshold=schema.regime.mean_reverting_threshold,
        ),
        confidence_weights=ConfidenceWeights(
            w1_threshold_distance=schema.confidence_weights.w1_threshold_distance,
            w2_timeframe_consistency=schema.confidence_weights.w2_timeframe_consistency,
            w3_dfa_stability=schema.confidence_weights.w3_dfa_stability,
            w4_structural_validity=schema.confidence_weights.w4_structural_validity,
        ),
        fibonacci_tolerance=schema.fibonacci_tolerance,
        enabled_timeframes=[TimeframeLevel(tf.value) for tf in schema.enabled_timeframes],
    )


def _internal_config_to_schema(config: EngineConfig) -> EngineConfigSchema:
    """Convert internal config to API schema."""
    from app.schemas.wave_engine import (
        DFAConfigSchema,
        ThresholdConfigSchema,
        RegimeConfigSchema,
        ConfidenceWeightsSchema,
        TimeframeLevel as SchemaTimeframeLevel,
    )

    return EngineConfigSchema(
        dfa=DFAConfigSchema(
            window_size=config.dfa.window_size,
            polynomial_order=config.dfa.polynomial_order,
            min_segment_size=config.dfa.min_segment_size,
            max_segment_ratio=config.dfa.max_segment_ratio,
        ),
        threshold=ThresholdConfigSchema(
            atr_period=config.threshold.atr_period,
            beta_min=config.threshold.beta_min,
            beta_max=config.threshold.beta_max,
            sigmoid_k=config.threshold.sigmoid_k,
            alpha_mid=config.threshold.alpha_mid,
        ),
        regime=RegimeConfigSchema(
            ewma_lambda_slow=config.regime.ewma_lambda_slow,
            ewma_lambda_fast=config.regime.ewma_lambda_fast,
            regime_change_threshold=config.regime.regime_change_threshold,
            trending_threshold=config.regime.trending_threshold,
            mean_reverting_threshold=config.regime.mean_reverting_threshold,
        ),
        confidence_weights=ConfidenceWeightsSchema(
            w1_threshold_distance=config.confidence_weights.w1_threshold_distance,
            w2_timeframe_consistency=config.confidence_weights.w2_timeframe_consistency,
            w3_dfa_stability=config.confidence_weights.w3_dfa_stability,
            w4_structural_validity=config.confidence_weights.w4_structural_validity,
        ),
        fibonacci_tolerance=config.fibonacci_tolerance,
        enabled_timeframes=[SchemaTimeframeLevel(tf.value) for tf in config.enabled_timeframes],
    )


async def _fetch_market_data(symbol: str, period: str, interval: str):
    """Fetch market data using the data provider."""
    provider = DataProvider()
    data, warning = await provider.get_ohlcv(symbol, period, interval)
    return data, warning


@router.post("", response_model=WaveEngineResponse)
async def analyze_with_wave_engine(request: WaveEngineRequest):
    """
    Perform full wave analysis with DFA and adaptive thresholds.

    This endpoint provides:
    - DFA-based market regime detection
    - Adaptive threshold calculation (τ = ATR × f(α))
    - Enhanced pivot detection with confidence scoring
    - Regime change events
    """
    try:
        # Fetch market data
        data, warning = await _fetch_market_data(request.symbol, request.period, request.interval)

        if not data.candles or len(data.candles) < 50:
            raise HTTPException(
                status_code=422,
                detail=f"Insufficient data: need at least 50 candles, got {len(data.candles) if data.candles else 0}"
            )

        # Convert to numpy arrays
        prices = np.array([c.close for c in data.candles])
        highs = np.array([c.high for c in data.candles])
        lows = np.array([c.low for c in data.candles])
        closes = np.array([c.close for c in data.candles])
        timestamps = [c.timestamp for c in data.candles]

        # Initialize engine with config
        config = _config_schema_to_internal(request.config)
        engine = WaveEngine(config)

        # Run analysis
        result = engine.analyze(
            prices=prices,
            highs=highs,
            lows=lows,
            closes=closes,
            timestamps=timestamps,
            symbol=request.symbol,
            timeframe=request.interval,
        )

        # Convert to response schema
        dfa_schema = DFAResultSchema(
            alpha=result.dfa_result.alpha,
            r_squared=result.dfa_result.r_squared,
            segment_sizes=result.dfa_result.segment_sizes,
            fluctuations=result.dfa_result.fluctuations,
            std_error=result.dfa_result.std_error,
            data_points=result.dfa_result.data_points,
            regime=result.dfa_result.regime,
            confidence_category=result.dfa_result.confidence_category,
        )

        regime_schema = RegimeStateSchema(
            current_regime=SchemaRegimeType(result.regime_state.current_regime.value),
            current_alpha=result.regime_state.current_alpha,
            ewma_alpha=result.regime_state.ewma_alpha,
            regime_duration_bars=result.regime_state.regime_duration_bars,
            regime_start=result.regime_state.regime_start,
            stability_score=result.regime_state.stability_score,
            regime_strength=result.regime_state.regime_strength,
        )

        regime_events = [
            RegimeEventSchema(
                timestamp=e.timestamp,
                from_regime=SchemaRegimeType(e.from_regime.value),
                to_regime=SchemaRegimeType(e.to_regime.value),
                from_alpha=e.from_alpha,
                to_alpha=e.to_alpha,
                confidence=e.confidence,
            )
            for e in result.regime_events
        ]

        threshold_schema = ThresholdResultSchema(
            tau=result.threshold_result.tau,
            atr=result.threshold_result.atr,
            multiplier=result.threshold_result.multiplier,
            alpha=result.threshold_result.alpha,
            tau_percent=result.threshold_result.tau_percent,
            explanation=result.threshold_result.explanation,
        )

        pivots_schema = [
            EnhancedPivotSchema(
                timestamp=p.timestamp,
                price=p.price,
                type=SchemaPivotType(p.type.value),
                index=p.index,
                amplitude=p.amplitude,
                significance=p.significance,
                status=SchemaPivotStatus(p.status.value),
                overall_confidence=p.overall_confidence,
                confidence_components=ConfidenceComponentsSchema(**p.confidence_components) if p.confidence_components else None,
                alpha_at_creation=p.alpha_at_creation,
                tau_at_creation=p.tau_at_creation,
                regime_at_creation=SchemaRegimeType(p.regime_at_creation.value),
                timeframe=p.timeframe,
                pivot_id=p.pivot_id,
                parent_pivot_id=p.parent_pivot_id,
                child_pivot_ids=p.child_pivot_ids,
            )
            for p in result.pivots
        ]

        # Create pivot summary
        pivot_summary = {
            "total": len(result.pivots),
            "confirmed": len([p for p in result.pivots if p.status.value == "confirmed"]),
            "potential": len([p for p in result.pivots if p.status.value == "potential"]),
            "high_confidence": len([p for p in result.pivots if p.overall_confidence >= 70]),
            "average_confidence": sum(p.overall_confidence for p in result.pivots) / len(result.pivots) if result.pivots else 0,
        }

        return WaveEngineResponse(
            symbol=request.symbol,
            timestamp=datetime.now(),
            dfa_result=dfa_schema,
            regime_state=regime_schema,
            regime_events=regime_events,
            threshold_result=threshold_schema,
            pivots=pivots_schema,
            pivot_summary=pivot_summary,
            config_used=_internal_config_to_schema(config),
            warning=warning,
            data_points=len(data.candles),
        )

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/config/default", response_model=EngineConfigSchema)
async def get_default_config():
    """Get the default engine configuration with all parameters."""
    return _internal_config_to_schema(EngineConfig())


@router.post("/config/validate", response_model=ConfigValidationResponse)
async def validate_config(config: EngineConfigSchema):
    """
    Validate a configuration and return any warnings.

    Checks for:
    - Parameter range violations
    - Inconsistent parameter combinations
    - Performance concerns
    """
    errors = []
    warnings = []

    # Check weight sum
    weight_sum = (
        config.confidence_weights.w1_threshold_distance +
        config.confidence_weights.w2_timeframe_consistency +
        config.confidence_weights.w3_dfa_stability +
        config.confidence_weights.w4_structural_validity
    )
    if not 0.95 <= weight_sum <= 1.05:
        warnings.append(f"Confidence weights sum to {weight_sum:.2f}, ideally should be 1.0")

    # Check threshold config
    if config.threshold.beta_min >= config.threshold.beta_max:
        errors.append("beta_min must be less than beta_max")

    # Check regime config
    if config.regime.mean_reverting_threshold >= config.regime.trending_threshold:
        errors.append("mean_reverting_threshold must be less than trending_threshold")

    # Performance warnings
    if config.dfa.window_size > 300:
        warnings.append("Large DFA window (>300) may impact performance")

    if len(config.enabled_timeframes) > 3:
        warnings.append("Many timeframes enabled may impact performance")

    try:
        effective = _config_schema_to_internal(config)
        effective_schema = _internal_config_to_schema(effective)
    except Exception as e:
        errors.append(f"Configuration error: {str(e)}")
        effective_schema = None

    return ConfigValidationResponse(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        effective_config=effective_schema,
    )


@router.get("/dfa/{symbol}", response_model=DFAOnlyResponse)
async def get_dfa(
    symbol: str,
    period: str = Query("1y", description="Data period"),
    interval: str = Query("1d", description="Data interval"),
    window: int = Query(150, ge=50, le=500, description="DFA window size"),
):
    """Get DFA analysis for a symbol."""
    try:
        data, _ = await _fetch_market_data(symbol, period, interval)

        if not data.candles or len(data.candles) < 50:
            raise HTTPException(status_code=422, detail="Insufficient data")

        prices = np.array([c.close for c in data.candles])
        timestamps = [c.timestamp for c in data.candles]

        config = EngineConfig(dfa=DFAConfig(window_size=window))
        engine = WaveEngine(config)

        dfa_result, regime_state = engine.get_dfa_only(prices, timestamps)

        return DFAOnlyResponse(
            symbol=symbol,
            timestamp=datetime.now(),
            dfa_result=DFAResultSchema(
                alpha=dfa_result.alpha,
                r_squared=dfa_result.r_squared,
                segment_sizes=dfa_result.segment_sizes,
                fluctuations=dfa_result.fluctuations,
                std_error=dfa_result.std_error,
                data_points=dfa_result.data_points,
                regime=dfa_result.regime,
                confidence_category=dfa_result.confidence_category,
            ),
            regime_state=RegimeStateSchema(
                current_regime=SchemaRegimeType(regime_state.current_regime.value),
                current_alpha=regime_state.current_alpha,
                ewma_alpha=regime_state.ewma_alpha,
                regime_duration_bars=regime_state.regime_duration_bars,
                regime_start=regime_state.regime_start,
                stability_score=regime_state.stability_score,
                regime_strength=regime_state.regime_strength,
            ),
        )

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/regime/{symbol}", response_model=RegimeOnlyResponse)
async def get_regime(
    symbol: str,
    period: str = Query("1y", description="Data period"),
    interval: str = Query("1d", description="Data interval"),
):
    """Get current market regime for a symbol."""
    try:
        data, _ = await _fetch_market_data(symbol, period, interval)

        if not data.candles or len(data.candles) < 50:
            raise HTTPException(status_code=422, detail="Insufficient data")

        prices = np.array([c.close for c in data.candles])
        timestamps = [c.timestamp for c in data.candles]

        engine = WaveEngine()
        _, regime_state = engine.get_dfa_only(prices, timestamps)

        return RegimeOnlyResponse(
            symbol=symbol,
            timestamp=datetime.now(),
            regime_state=RegimeStateSchema(
                current_regime=SchemaRegimeType(regime_state.current_regime.value),
                current_alpha=regime_state.current_alpha,
                ewma_alpha=regime_state.ewma_alpha,
                regime_duration_bars=regime_state.regime_duration_bars,
                regime_start=regime_state.regime_start,
                stability_score=regime_state.stability_score,
                regime_strength=regime_state.regime_strength,
            ),
            regime_events=[
                RegimeEventSchema(
                    timestamp=e.timestamp,
                    from_regime=SchemaRegimeType(e.from_regime.value),
                    to_regime=SchemaRegimeType(e.to_regime.value),
                    from_alpha=e.from_alpha,
                    to_alpha=e.to_alpha,
                    confidence=e.confidence,
                )
                for e in engine._state.regime_detector.get_regime_events()
            ] if engine._state else [],
        )

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/threshold/{symbol}", response_model=ThresholdOnlyResponse)
async def get_threshold(
    symbol: str,
    period: str = Query("1y", description="Data period"),
    interval: str = Query("1d", description="Data interval"),
):
    """Get adaptive threshold calculation for a symbol."""
    try:
        data, _ = await _fetch_market_data(symbol, period, interval)

        if not data.candles or len(data.candles) < 50:
            raise HTTPException(status_code=422, detail="Insufficient data")

        prices = np.array([c.close for c in data.candles])
        highs = np.array([c.high for c in data.candles])
        lows = np.array([c.low for c in data.candles])
        closes = np.array([c.close for c in data.candles])
        timestamps = [c.timestamp for c in data.candles]

        engine = WaveEngine()

        # Get DFA first
        dfa_result, regime_state = engine.get_dfa_only(prices, timestamps)

        # Then calculate threshold
        threshold_result = engine.get_threshold_only(highs, lows, closes, regime_state.ewma_alpha)

        return ThresholdOnlyResponse(
            symbol=symbol,
            timestamp=datetime.now(),
            threshold_result=ThresholdResultSchema(
                tau=threshold_result.tau,
                atr=threshold_result.atr,
                multiplier=threshold_result.multiplier,
                alpha=threshold_result.alpha,
                tau_percent=threshold_result.tau_percent,
                explanation=threshold_result.explanation,
            ),
            dfa_alpha=regime_state.ewma_alpha,
            regime=SchemaRegimeType(regime_state.current_regime.value),
        )

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
