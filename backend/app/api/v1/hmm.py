"""HMM regime detection API endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from app.services.data_provider import DataProvider, get_data_provider
from app.services.hmm import (
    HMMRegimeDetector,
    TechnicalIndicators,
    StrategyEngine,
    StrategyParams,
    Backtester,
    HMMCache,
    get_hmm_cache,
    ModelConfig,
    ModelType,
    EmissionDistribution,
    FeatureEngine,
    ModelFactory,
    RollingRefitManager,
    HMMOptimizer,
    StrategyOptimizer,
    optimization_store,
    OptimizationStatus,
)
from app.schemas.hmm import (
    HMMAnalysisRequest,
    HMMAnalysisResponse,
    HMMTrainRequest,
    HMMTrainResponse,
    HMMRegimeRequest,
    HMMRegimeResponse,
    IndicatorRequest,
    IndicatorResponse,
    BacktestRequest,
    BacktestResponse,
    SignalRequest,
    SignalResponse,
    RegimeInfo as RegimeInfoSchema,
    RegimeDataPoint,
    IndicatorSeries,
    IndicatorSignals,
    IndicatorDataPoint,
    TradingSignal,
    ConfirmationDetails,
    SignalType,
    TradeSchema,
    EquityCurvePoint,
    HMMOptimizationRequest,
    StrategyOptimizationRequest,
    OptimizationStartResponse,
    OptimizationProgressResponse,
    OptimizationResultResponse,
    OptimizationStatusEnum,
    PresetSaveRequest,
    PresetResponse,
    PresetListResponse,
)
from app.services.hmm.presets import HMMPreset, get_preset_manager

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


def _get_or_train_model(
    symbol: str,
    interval: str,
    n_states: int,
    df,
    cache: HMMCache,
    force_retrain: bool = False,
    n_iter: int = 100,
    selected_features: list = None,
    df_indicators=None,
    model_type: str = "hmm_gaussian",
    student_t_df: float = 5.0,
):
    """Get cached model or train new one."""
    if selected_features is None:
        selected_features = ["log_return", "range", "volume_change"]

    # Create cache key that includes features and model type
    feature_key = "_".join(sorted(selected_features))
    cache_key_suffix = f"{model_type}:{feature_key}"

    if not force_retrain:
        cached = cache.get(symbol, interval, n_states)
        if cached is not None and cached.is_trained:
            # Check if model type and features match
            if hasattr(cached, 'feature_engine') and hasattr(cached, 'get_model_type'):
                cached_features = set(cached.feature_engine.selected_features)
                cached_type = cached.get_model_type().value
                if cached_features == set(selected_features) and cached_type == model_type:
                    return cached

    # Create model configuration
    config = ModelConfig(
        n_states=n_states,
        selected_features=selected_features,
        n_iter=n_iter,
        student_t_df=student_t_df,
    )

    # Create model using factory
    try:
        model_type_enum = ModelType(model_type)
        detector = ModelFactory.create(model_type_enum, config)
    except ValueError as e:
        # Fall back to Gaussian HMM if model type is invalid
        detector = HMMRegimeDetector(config=config)

    # Train the model
    success = detector.train(df, df_indicators=df_indicators, n_iter=n_iter)

    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to train {model_type} model")

    cache.set(symbol, interval, detector)
    return detector


@router.post("/analyze", response_model=HMMAnalysisResponse)
async def analyze_hmm(
    request: HMMAnalysisRequest,
    data_provider: DataProvider = Depends(get_data_provider),
    cache: HMMCache = Depends(get_hmm_cache),
):
    """
    Perform full HMM analysis including regime detection, indicators, and signals.

    Returns current regime, regime series for charting, all indicators,
    and current trading signal with confirmation details.
    """
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

    # Calculate indicators first (needed for multivariate features)
    indicators = TechnicalIndicators(df)
    df_with_indicators = indicators.calculate_all()

    # Initialize refit timestamps
    refit_timestamps = []

    if request.enable_rolling_refit:
        # Use rolling refit manager
        refit_manager = RollingRefitManager(
            window_size=request.rolling_window_size,
            refit_interval=request.refit_interval,
        )

        # Factory function to create models
        def create_model():
            config = ModelConfig(
                n_states=request.n_states,
                selected_features=request.selected_features,
                n_iter=request.n_iter,
                student_t_df=request.student_t_df,
            )
            try:
                model_type_enum = ModelType(request.model_type.value)
                return ModelFactory.create(model_type_enum, config)
            except ValueError:
                return HMMRegimeDetector(config=config)

        # Run rolling analysis
        detector, _, _ = refit_manager.run_rolling_analysis(
            create_model,
            df,
            df_with_indicators,
            n_iter=request.n_iter,
        )

        if detector is None or not detector.is_trained:
            raise HTTPException(status_code=500, detail="Rolling refit failed to train any model")

        refit_timestamps = refit_manager.get_refit_timestamps()
        cache.set(request.symbol, request.interval, detector)
    else:
        # Get or train model with selected features (standard mode)
        detector = _get_or_train_model(
            request.symbol,
            request.interval,
            request.n_states,
            df,
            cache,
            request.force_retrain,
            request.n_iter,
            selected_features=request.selected_features,
            df_indicators=df_with_indicators,
            model_type=request.model_type.value,
            student_t_df=request.student_t_df,
        )

    # Get current regime (pass indicators if feature engine needs them)
    current_regime_info = detector.get_current_regime(df, df_with_indicators)

    # Get regime series for charting
    regime_series = detector.get_regime_series_as_list(df, df_with_indicators)

    # Get indicator series for charting
    indicator_series_dict = indicators.to_series_list()

    # Get indicator signals
    indicator_signals_dict = TechnicalIndicators.get_indicator_signals(df_with_indicators)

    # Get regime DataFrame for strategy
    regime_df = detector.get_regime_series(df)

    # Generate current signal with strategy parameters
    strategy_params = StrategyParams(
        required_confirmations=request.required_confirmations,
        rsi_oversold=request.rsi_oversold,
        rsi_overbought=request.rsi_overbought,
        rsi_bull_min=request.rsi_bull_min,
        rsi_bear_max=request.rsi_bear_max,
        adx_trend_threshold=request.adx_trend_threshold,
        volume_ratio_threshold=request.volume_ratio_threshold,
        regime_confidence_min=request.regime_confidence_min,
    )
    strategy = StrategyEngine(params=strategy_params)
    confirmation_result = strategy.generate_signal(df_with_indicators, regime_df)

    # Convert to response schemas
    current_regime = RegimeInfoSchema(
        regime_id=current_regime_info.regime_id,
        regime_name=current_regime_info.regime_name,
        confidence=current_regime_info.confidence,
        mean_return=current_regime_info.mean_return,
        volatility=current_regime_info.volatility,
    )

    regime_data_points = [RegimeDataPoint(**r) for r in regime_series]

    # Convert indicator series
    indicator_series = IndicatorSeries(
        rsi=[IndicatorDataPoint(**p) for p in indicator_series_dict.get("rsi", [])],
        macd=[IndicatorDataPoint(**p) for p in indicator_series_dict.get("macd", [])],
        macd_signal=[IndicatorDataPoint(**p) for p in indicator_series_dict.get("macd_signal", [])],
        macd_histogram=[IndicatorDataPoint(**p) for p in indicator_series_dict.get("macd_histogram", [])],
        adx=[IndicatorDataPoint(**p) for p in indicator_series_dict.get("adx", [])],
        di_plus=[IndicatorDataPoint(**p) for p in indicator_series_dict.get("di_plus", [])],
        di_minus=[IndicatorDataPoint(**p) for p in indicator_series_dict.get("di_minus", [])],
        bb_upper=[IndicatorDataPoint(**p) for p in indicator_series_dict.get("bb_upper", [])],
        bb_middle=[IndicatorDataPoint(**p) for p in indicator_series_dict.get("bb_middle", [])],
        bb_lower=[IndicatorDataPoint(**p) for p in indicator_series_dict.get("bb_lower", [])],
        sma_20=[IndicatorDataPoint(**p) for p in indicator_series_dict.get("sma_20", [])],
        sma_50=[IndicatorDataPoint(**p) for p in indicator_series_dict.get("sma_50", [])],
        sma_200=[IndicatorDataPoint(**p) for p in indicator_series_dict.get("sma_200", [])],
        ema_12=[IndicatorDataPoint(**p) for p in indicator_series_dict.get("ema_12", [])],
        ema_26=[IndicatorDataPoint(**p) for p in indicator_series_dict.get("ema_26", [])],
        atr=[IndicatorDataPoint(**p) for p in indicator_series_dict.get("atr", [])],
        volume_ratio=[IndicatorDataPoint(**p) for p in indicator_series_dict.get("volume_ratio", [])],
    )

    indicator_signals = IndicatorSignals(**indicator_signals_dict)

    current_signal = TradingSignal(
        signal=SignalType(confirmation_result.signal.value),
        confirmations_met=confirmation_result.confirmations_met,
        total_conditions=confirmation_result.total_conditions,
        details=ConfirmationDetails(**confirmation_result.details),
        regime=confirmation_result.regime,
        confidence=confirmation_result.confidence,
    )

    return HMMAnalysisResponse(
        symbol=request.symbol.upper(),
        timestamp=datetime.utcnow(),
        current_regime=current_regime,
        regime_series=regime_data_points,
        indicators=indicator_series,
        indicator_signals=indicator_signals,
        current_signal=current_signal,
        is_model_trained=True,
        warning=warning,
        model_type=detector.get_model_type().value,
        selected_features=request.selected_features,
        refit_timestamps=refit_timestamps,
    )


@router.post("/train", response_model=HMMTrainResponse)
async def train_hmm(
    request: HMMTrainRequest,
    data_provider: DataProvider = Depends(get_data_provider),
    cache: HMMCache = Depends(get_hmm_cache),
):
    """
    Train a new HMM model for a symbol.

    Forces retraining even if a model is cached.
    """
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

    # Invalidate existing cache
    cache.invalidate(request.symbol, request.interval, request.n_states)

    # Train new model
    detector = HMMRegimeDetector(n_states=request.n_states)
    success = detector.train(df, n_iter=request.n_iter)

    if not success:
        return HMMTrainResponse(
            symbol=request.symbol.upper(),
            success=False,
            n_states=request.n_states,
            message="Training failed - insufficient data or convergence issues",
            regime_mapping={},
        )

    # Cache the model
    cache.set(request.symbol, request.interval, detector)

    return HMMTrainResponse(
        symbol=request.symbol.upper(),
        success=True,
        n_states=request.n_states,
        message=f"Successfully trained HMM with {request.n_states} states",
        regime_mapping=detector.regime_mapping,
    )


@router.post("/regimes", response_model=HMMRegimeResponse)
async def get_regimes(
    request: HMMRegimeRequest,
    data_provider: DataProvider = Depends(get_data_provider),
    cache: HMMCache = Depends(get_hmm_cache),
):
    """
    Get regime series for chart visualization.

    Returns regime data points with colors for each timestamp.
    """
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

    # Get or train model
    detector = _get_or_train_model(
        request.symbol,
        request.interval,
        request.n_states,
        df,
        cache,
    )

    # Get regime data
    current_regime_info = detector.get_current_regime(df)
    regime_series = detector.get_regime_series_as_list(df)

    current_regime = RegimeInfoSchema(
        regime_id=current_regime_info.regime_id,
        regime_name=current_regime_info.regime_name,
        confidence=current_regime_info.confidence,
        mean_return=current_regime_info.mean_return,
        volatility=current_regime_info.volatility,
    )

    regime_data_points = [RegimeDataPoint(**r) for r in regime_series]

    return HMMRegimeResponse(
        symbol=request.symbol.upper(),
        regime_series=regime_data_points,
        current_regime=current_regime,
        warning=warning,
    )


@router.post("/indicators", response_model=IndicatorResponse)
async def get_indicators(
    request: IndicatorRequest,
    data_provider: DataProvider = Depends(get_data_provider),
):
    """
    Get technical indicator series for chart overlays and subplots.

    Returns all calculated indicators (RSI, MACD, ADX, BB, MA, etc.)
    and current indicator signals.
    """
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

    # Calculate indicators
    indicators = TechnicalIndicators(df)
    df_with_indicators = indicators.calculate_all()
    indicator_series_dict = indicators.to_series_list()

    # Get indicator signals
    indicator_signals_dict = TechnicalIndicators.get_indicator_signals(df_with_indicators)

    # Convert indicator series
    indicator_series = IndicatorSeries(
        rsi=[IndicatorDataPoint(**p) for p in indicator_series_dict.get("rsi", [])],
        macd=[IndicatorDataPoint(**p) for p in indicator_series_dict.get("macd", [])],
        macd_signal=[IndicatorDataPoint(**p) for p in indicator_series_dict.get("macd_signal", [])],
        macd_histogram=[IndicatorDataPoint(**p) for p in indicator_series_dict.get("macd_histogram", [])],
        adx=[IndicatorDataPoint(**p) for p in indicator_series_dict.get("adx", [])],
        di_plus=[IndicatorDataPoint(**p) for p in indicator_series_dict.get("di_plus", [])],
        di_minus=[IndicatorDataPoint(**p) for p in indicator_series_dict.get("di_minus", [])],
        bb_upper=[IndicatorDataPoint(**p) for p in indicator_series_dict.get("bb_upper", [])],
        bb_middle=[IndicatorDataPoint(**p) for p in indicator_series_dict.get("bb_middle", [])],
        bb_lower=[IndicatorDataPoint(**p) for p in indicator_series_dict.get("bb_lower", [])],
        sma_20=[IndicatorDataPoint(**p) for p in indicator_series_dict.get("sma_20", [])],
        sma_50=[IndicatorDataPoint(**p) for p in indicator_series_dict.get("sma_50", [])],
        sma_200=[IndicatorDataPoint(**p) for p in indicator_series_dict.get("sma_200", [])],
        ema_12=[IndicatorDataPoint(**p) for p in indicator_series_dict.get("ema_12", [])],
        ema_26=[IndicatorDataPoint(**p) for p in indicator_series_dict.get("ema_26", [])],
        atr=[IndicatorDataPoint(**p) for p in indicator_series_dict.get("atr", [])],
        volume_ratio=[IndicatorDataPoint(**p) for p in indicator_series_dict.get("volume_ratio", [])],
    )

    indicator_signals = IndicatorSignals(**indicator_signals_dict)

    return IndicatorResponse(
        symbol=request.symbol.upper(),
        indicators=indicator_series,
        indicator_signals=indicator_signals,
        warning=warning,
    )


@router.post("/backtest", response_model=BacktestResponse)
async def run_backtest(
    request: BacktestRequest,
    data_provider: DataProvider = Depends(get_data_provider),
    cache: HMMCache = Depends(get_hmm_cache),
):
    """
    Run backtest on HMM regime-based strategy.

    Returns performance metrics, trades, and equity curve.
    """
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

    # Calculate indicators first (needed for model training with multivariate features)
    indicators = TechnicalIndicators(df)
    df_with_indicators = indicators.calculate_all()

    # Get or train model with FULL HMM parameters
    # This is critical for optimization results to be reproducible
    detector = _get_or_train_model(
        request.symbol,
        request.interval,
        request.n_states,
        df,
        cache,
        force_retrain=request.force_retrain,
        n_iter=request.n_iter,
        selected_features=request.selected_features,
        df_indicators=df_with_indicators,
        model_type=request.model_type.value,
        student_t_df=request.student_t_df,
    )

    # Get regime series (pass indicators for multivariate models)
    regime_df = detector.get_regime_series(df, df_with_indicators)

    # Generate signals series with strategy parameters
    strategy_params = StrategyParams(
        required_confirmations=request.required_confirmations,
        rsi_oversold=request.rsi_oversold,
        rsi_overbought=request.rsi_overbought,
        rsi_bull_min=request.rsi_bull_min,
        rsi_bear_max=request.rsi_bear_max,
        macd_threshold=request.macd_threshold,
        momentum_threshold=request.momentum_threshold,
        adx_trend_threshold=request.adx_trend_threshold,
        volume_ratio_threshold=request.volume_ratio_threshold,
        regime_confidence_min=request.regime_confidence_min,
        cooldown_periods=request.cooldown_periods,
        bullish_regimes=request.bullish_regimes,
        bearish_regimes=request.bearish_regimes,
        stop_loss_pct=request.stop_loss_pct,
        take_profit_pct=request.take_profit_pct,
        trailing_stop_pct=request.trailing_stop_pct,
        max_hold_periods=request.max_hold_periods,
        ma_period=request.ma_period,
        exit_on_regime_change=request.exit_on_regime_change,
        exit_on_opposite_signal=request.exit_on_opposite_signal,
    )
    strategy = StrategyEngine(params=strategy_params)
    signals_df = strategy.generate_signals_series(df_with_indicators, regime_df)

    # Run backtest with strategy params for risk management
    backtester = Backtester(
        leverage=request.leverage,
        slippage_pct=request.slippage_pct,
        commission_pct=request.commission_pct,
        initial_capital=request.initial_capital,
        strategy_params=strategy_params,
    )

    result = backtester.run(df, signals_df)
    result_dict = result.to_dict()

    # Convert to response schema
    trades = [TradeSchema(**t) for t in result_dict["trades"]]
    equity_curve = [EquityCurvePoint(**p) for p in result_dict["equity_curve"]]
    drawdown_curve = [EquityCurvePoint(**p) for p in result_dict["drawdown_curve"]]

    return BacktestResponse(
        total_return=result_dict["total_return"],
        buy_hold_return=result_dict["buy_hold_return"],
        alpha=result_dict["alpha"],
        sharpe_ratio=result_dict["sharpe_ratio"],
        max_drawdown=result_dict["max_drawdown"],
        win_rate=result_dict["win_rate"],
        total_trades=result_dict["total_trades"],
        winning_trades=result_dict["winning_trades"],
        losing_trades=result_dict["losing_trades"],
        avg_win=result_dict["avg_win"],
        avg_loss=result_dict["avg_loss"],
        profit_factor=result_dict["profit_factor"],
        trades=trades,
        equity_curve=equity_curve,
        drawdown_curve=drawdown_curve,
    )


@router.post("/signal", response_model=SignalResponse)
async def get_signal(
    request: SignalRequest,
    data_provider: DataProvider = Depends(get_data_provider),
    cache: HMMCache = Depends(get_hmm_cache),
):
    """
    Get current trading signal based on HMM regime and indicator confirmations.
    """
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

    # Get or train model
    detector = _get_or_train_model(
        request.symbol,
        request.interval,
        request.n_states,
        df,
        cache,
    )

    # Calculate indicators
    indicators = TechnicalIndicators(df)
    df_with_indicators = indicators.calculate_all()

    # Get regime series
    regime_df = detector.get_regime_series(df)

    # Generate current signal with strategy parameters
    strategy_params = StrategyParams(
        required_confirmations=request.required_confirmations,
        rsi_oversold=request.rsi_oversold,
        rsi_overbought=request.rsi_overbought,
        rsi_bull_min=request.rsi_bull_min,
        rsi_bear_max=request.rsi_bear_max,
        adx_trend_threshold=request.adx_trend_threshold,
        volume_ratio_threshold=request.volume_ratio_threshold,
        regime_confidence_min=request.regime_confidence_min,
    )
    strategy = StrategyEngine(params=strategy_params)
    confirmation_result = strategy.generate_signal(df_with_indicators, regime_df)

    current_signal = TradingSignal(
        signal=SignalType(confirmation_result.signal.value),
        confirmations_met=confirmation_result.confirmations_met,
        total_conditions=confirmation_result.total_conditions,
        details=ConfirmationDetails(**confirmation_result.details),
        regime=confirmation_result.regime,
        confidence=confirmation_result.confidence,
    )

    return SignalResponse(
        symbol=request.symbol.upper(),
        signal=current_signal,
        warning=warning,
    )


# ============== Optimization Endpoints ==============

@router.post("/optimize/hmm/start", response_model=OptimizationStartResponse)
async def start_hmm_optimization(
    request: HMMOptimizationRequest,
    data_provider: DataProvider = Depends(get_data_provider),
):
    """
    Start HMM parameter optimization asynchronously.

    Uses Grid Search over n_states, n_iter, and model_type,
    followed by Forward Feature Selection.
    """
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

    # Create strategy params for evaluation
    strategy_params = StrategyParams(
        required_confirmations=request.required_confirmations,
        rsi_oversold=request.rsi_oversold,
        rsi_overbought=request.rsi_overbought,
        rsi_bull_min=request.rsi_bull_min,
        rsi_bear_max=request.rsi_bear_max,
        macd_threshold=request.macd_threshold,
        momentum_threshold=request.momentum_threshold,
        adx_trend_threshold=request.adx_trend_threshold,
        volume_ratio_threshold=request.volume_ratio_threshold,
        regime_confidence_min=request.regime_confidence_min,
        cooldown_periods=request.cooldown_periods,
        bullish_regimes=request.bullish_regimes,
        bearish_regimes=request.bearish_regimes,
        stop_loss_pct=request.stop_loss_pct,
        take_profit_pct=request.take_profit_pct,
        trailing_stop_pct=request.trailing_stop_pct,
        max_hold_periods=request.max_hold_periods,
        ma_period=request.ma_period,
        exit_on_regime_change=request.exit_on_regime_change,
        exit_on_opposite_signal=request.exit_on_opposite_signal,
    )

    # Create optimizer
    optimizer = HMMOptimizer(
        df=df,
        strategy_params=strategy_params,
        leverage=request.leverage,
        slippage_pct=request.slippage_pct,
        commission_pct=request.commission_pct,
        initial_capital=request.initial_capital,
    )

    # Start async optimization
    optimization_id = optimizer.start_async()

    return OptimizationStartResponse(
        optimization_id=optimization_id,
        status=OptimizationStatusEnum.RUNNING,
        estimated_trials=59,  # 48 grid search (8×3×2) + 11 feature selection
        message="HMM optimization started. Use progress endpoint to track status.",
    )


@router.post("/optimize/strategy/start", response_model=OptimizationStartResponse)
async def start_strategy_optimization(
    request: StrategyOptimizationRequest,
    data_provider: DataProvider = Depends(get_data_provider),
    cache: HMMCache = Depends(get_hmm_cache),
):
    """
    Start strategy parameter optimization asynchronously.

    Uses Bayesian Optimization (Optuna TPE) for efficient search
    over the strategy parameter space.
    """
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

    # Calculate indicators
    indicators = TechnicalIndicators(df)
    df_with_indicators = indicators.calculate_all()

    # Get or train model
    detector = _get_or_train_model(
        request.symbol,
        request.interval,
        request.n_states,
        df,
        cache,
        force_retrain=False,
        n_iter=request.n_iter,
        selected_features=request.selected_features,
        df_indicators=df_with_indicators,
        model_type=request.model_type.value,
        student_t_df=request.student_t_df,
    )

    # Get regime series
    regime_df = detector.get_regime_series(df, df_with_indicators)

    # Create optimizer
    optimizer = StrategyOptimizer(
        df=df,
        df_with_indicators=df_with_indicators,
        regime_df=regime_df,
        leverage=request.leverage,
        slippage_pct=request.slippage_pct,
        commission_pct=request.commission_pct,
        initial_capital=request.initial_capital,
    )

    # Start async optimization
    optimization_id = optimizer.start_async(
        n_trials=request.n_trials,
        timeout=request.timeout_seconds,
    )

    return OptimizationStartResponse(
        optimization_id=optimization_id,
        status=OptimizationStatusEnum.RUNNING,
        estimated_trials=request.n_trials,
        message="Strategy optimization started. Use progress endpoint to track status.",
    )


@router.get("/optimize/{optimization_id}/progress", response_model=OptimizationProgressResponse)
async def get_optimization_progress(optimization_id: str):
    """
    Get current progress of an optimization run.

    Poll this endpoint to track optimization progress.
    """
    progress = optimization_store.get_progress(optimization_id)

    if progress is None:
        raise HTTPException(
            status_code=404,
            detail=f"Optimization {optimization_id} not found"
        )

    return OptimizationProgressResponse(
        optimization_id=progress.optimization_id,
        status=OptimizationStatusEnum(progress.status.value),
        current_trial=progress.current_trial,
        total_trials=progress.total_trials,
        best_alpha=progress.best_alpha if progress.best_alpha != float("-inf") else 0.0,
        best_params=progress.best_params,
        elapsed_seconds=progress.elapsed_seconds,
        message=progress.message,
    )


@router.get("/optimize/{optimization_id}/result", response_model=OptimizationResultResponse)
async def get_optimization_result(optimization_id: str):
    """
    Get final result of a completed optimization.

    Returns the best parameters found and performance metrics.
    """
    result = optimization_store.get_result(optimization_id)

    if result is None:
        # Check if still running
        progress = optimization_store.get_progress(optimization_id)
        if progress is not None and progress.status == OptimizationStatus.RUNNING:
            raise HTTPException(
                status_code=202,
                detail="Optimization still in progress"
            )
        raise HTTPException(
            status_code=404,
            detail=f"Optimization result for {optimization_id} not found"
        )

    return OptimizationResultResponse(
        success=result.success,
        best_params=result.best_params,
        best_alpha=result.best_alpha,
        best_sharpe=result.best_sharpe,
        best_total_return=result.best_total_return,
        best_max_drawdown=result.best_max_drawdown,
        total_trials_evaluated=result.total_trials_evaluated,
        optimization_time_seconds=result.optimization_time_seconds,
        error_message=result.error_message,
    )


@router.post("/optimize/{optimization_id}/cancel")
async def cancel_optimization(optimization_id: str):
    """
    Cancel a running optimization.

    The optimization will stop at the next checkpoint and return
    the best parameters found so far.
    """
    success = optimization_store.request_cancel(optimization_id)

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Optimization {optimization_id} not found"
        )

    return {"message": "Cancellation requested", "optimization_id": optimization_id}


# ============== Preset Endpoints ==============

@router.post("/presets", response_model=PresetResponse)
async def save_preset(request: PresetSaveRequest):
    """
    Save current HMM and strategy settings as a preset.

    If name is not provided, generates one from symbol_interval_period.
    """
    preset_manager = get_preset_manager()

    # Generate name if not provided
    name = request.name
    if not name:
        name = preset_manager.generate_default_name(
            request.symbol,
            request.interval,
            request.period
        )

    # Create preset
    preset = HMMPreset(
        name=name,
        symbol=request.symbol,
        period=request.period,
        interval=request.interval,
        n_states=request.n_states,
        n_iter=request.n_iter,
        model_type=request.model_type.value,
        student_t_df=request.student_t_df,
        selected_features=request.selected_features,
        required_confirmations=request.required_confirmations,
        rsi_oversold=request.rsi_oversold,
        rsi_overbought=request.rsi_overbought,
        rsi_bull_min=request.rsi_bull_min,
        rsi_bear_max=request.rsi_bear_max,
        macd_threshold=request.macd_threshold,
        momentum_threshold=request.momentum_threshold,
        adx_trend_threshold=request.adx_trend_threshold,
        volume_ratio_threshold=request.volume_ratio_threshold,
        regime_confidence_min=request.regime_confidence_min,
        cooldown_periods=request.cooldown_periods,
        bullish_regimes=request.bullish_regimes,
        bearish_regimes=request.bearish_regimes,
        stop_loss_pct=request.stop_loss_pct,
        take_profit_pct=request.take_profit_pct,
        trailing_stop_pct=request.trailing_stop_pct,
        max_hold_periods=request.max_hold_periods,
        ma_period=request.ma_period,
        exit_on_regime_change=request.exit_on_regime_change,
        exit_on_opposite_signal=request.exit_on_opposite_signal,
        leverage=request.leverage,
        slippage_pct=request.slippage_pct,
        commission_pct=request.commission_pct,
        initial_capital=request.initial_capital,
        saved_alpha=request.saved_alpha,
        saved_sharpe=request.saved_sharpe,
        saved_total_return=request.saved_total_return,
    )

    saved_preset = preset_manager.save_preset(preset)

    return PresetResponse(**saved_preset.model_dump())


@router.get("/presets", response_model=PresetListResponse)
async def list_presets():
    """
    List all saved presets.

    Returns presets sorted by updated_at descending (most recent first).
    """
    preset_manager = get_preset_manager()
    presets = preset_manager.list_presets()

    return PresetListResponse(
        presets=[PresetResponse(**p.model_dump()) for p in presets],
        count=len(presets),
    )


@router.get("/presets/{name}", response_model=PresetResponse)
async def get_preset(name: str):
    """
    Get a specific preset by name.
    """
    preset_manager = get_preset_manager()
    preset = preset_manager.get_preset(name)

    if preset is None:
        raise HTTPException(
            status_code=404,
            detail=f"Preset '{name}' not found"
        )

    return PresetResponse(**preset.model_dump())


@router.delete("/presets/{name}")
async def delete_preset(name: str):
    """
    Delete a preset by name.
    """
    preset_manager = get_preset_manager()
    success = preset_manager.delete_preset(name)

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Preset '{name}' not found"
        )

    return {"message": f"Preset '{name}' deleted", "name": name}
