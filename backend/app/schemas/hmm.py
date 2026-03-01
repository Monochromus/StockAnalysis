"""Pydantic schemas for HMM regime detection."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class HMMRegimeType(str, Enum):
    """HMM regime types."""
    CRASH = "Crash"
    BEAR = "Bear"
    NEUTRAL_DOWN = "Neutral Down"
    CHOP = "Chop"
    NEUTRAL_UP = "Neutral Up"
    BULL = "Bull"
    BULL_RUN = "Bull Run"


class SignalType(str, Enum):
    """Trading signal types."""
    LONG = "LONG"
    SHORT = "SHORT"
    CASH = "CASH"
    HOLD = "HOLD"


class EmissionDistributionType(str, Enum):
    """Emission distribution types for HMM models."""
    GAUSSIAN = "gaussian"
    STUDENT_T = "student_t"


class ModelTypeEnum(str, Enum):
    """Available model types for regime detection."""
    HMM_GAUSSIAN = "hmm_gaussian"
    HMM_STUDENT_T = "hmm_student_t"
    RS_GARCH = "rs_garch"
    BAYESIAN_HMM = "bayesian_hmm"


class FeatureConfigSchema(BaseModel):
    """Configuration for HMM feature selection."""
    # Basic OHLCV features
    log_return: bool = True
    range: bool = True
    volume_change: bool = True

    # Momentum features
    rsi: bool = False
    macd: bool = False
    macd_histogram: bool = False
    momentum_normalized: bool = False
    roc: bool = False

    # Trend features
    adx: bool = False
    di_diff: bool = False

    # Volatility features
    bb_pct: bool = False
    atr_normalized: bool = False

    # Moving average distance features
    sma_20_dist: bool = False
    sma_50_dist: bool = False
    sma_200_dist: bool = False

    # Volume features
    volume_ratio: bool = False


class RegimeDataPoint(BaseModel):
    """Single regime data point for chart visualization."""
    timestamp: str
    regime_id: int
    regime_name: str
    confidence: float = Field(..., ge=0, le=1)
    color: str


class RegimeInfo(BaseModel):
    """Current regime information."""
    regime_id: int
    regime_name: str
    confidence: float = Field(..., ge=0, le=1)
    mean_return: float
    volatility: float


class IndicatorDataPoint(BaseModel):
    """Single indicator value at a timestamp."""
    timestamp: str
    value: float


class IndicatorSeries(BaseModel):
    """Series of indicator values."""
    rsi: List[IndicatorDataPoint] = []
    macd: List[IndicatorDataPoint] = []
    macd_signal: List[IndicatorDataPoint] = []
    macd_histogram: List[IndicatorDataPoint] = []
    adx: List[IndicatorDataPoint] = []
    di_plus: List[IndicatorDataPoint] = []
    di_minus: List[IndicatorDataPoint] = []
    bb_upper: List[IndicatorDataPoint] = []
    bb_middle: List[IndicatorDataPoint] = []
    bb_lower: List[IndicatorDataPoint] = []
    sma_20: List[IndicatorDataPoint] = []
    sma_50: List[IndicatorDataPoint] = []
    sma_200: List[IndicatorDataPoint] = []
    ema_12: List[IndicatorDataPoint] = []
    ema_26: List[IndicatorDataPoint] = []
    atr: List[IndicatorDataPoint] = []
    volume_ratio: List[IndicatorDataPoint] = []


class IndicatorSignals(BaseModel):
    """Current indicator signals summary."""
    RSI: str = "neutral"
    MACD: str = "neutral"
    ADX: str = "neutral"
    BB: str = "neutral"
    MA: str = "neutral"
    Momentum: str = "neutral"


class ConfirmationDetails(BaseModel):
    """Details of strategy confirmations."""
    regime_bullish: Optional[bool] = None
    regime_bearish: Optional[bool] = None
    regime_confidence: Optional[bool] = None
    rsi_favorable: Optional[bool] = None
    macd_bullish: Optional[bool] = None
    macd_bearish: Optional[bool] = None
    adx_bullish: Optional[bool] = None
    adx_bearish: Optional[bool] = None
    momentum_positive: Optional[bool] = None
    momentum_negative: Optional[bool] = None
    volume_strong: Optional[bool] = None
    price_above_ma: Optional[bool] = None
    price_below_ma: Optional[bool] = None
    cooldown_active: Optional[bool] = None
    chop_regime: Optional[bool] = None


class TradingSignal(BaseModel):
    """Current trading signal with confirmations."""
    signal: SignalType
    confirmations_met: int
    total_conditions: int
    details: ConfirmationDetails
    regime: str
    confidence: float


class TradeSchema(BaseModel):
    """Single trade in backtest results."""
    entry_date: Optional[str] = None
    exit_date: Optional[str] = None
    entry_price: float
    exit_price: Optional[float] = None
    direction: str
    size: float
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    regime_at_entry: str = ""


class EquityCurvePoint(BaseModel):
    """Single point in equity curve."""
    timestamp: str
    value: float


class BacktestResponse(BaseModel):
    """Backtest results."""
    total_return: float
    buy_hold_return: float
    alpha: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    profit_factor: float
    trades: List[TradeSchema] = []
    equity_curve: List[EquityCurvePoint] = []
    drawdown_curve: List[EquityCurvePoint] = []


# Request schemas

class HMMAnalysisRequest(BaseModel):
    """Request for HMM analysis."""
    symbol: str = Field(..., description="Ticker symbol")
    period: str = Field("2y", description="Data period for training")
    interval: str = Field("1d", description="Data interval")
    n_states: int = Field(7, ge=3, le=10, description="Number of HMM states")
    n_iter: int = Field(100, ge=10, le=500, description="Training iterations")
    force_retrain: bool = Field(False, description="Force model retraining")

    # Model configuration
    model_type: ModelTypeEnum = Field(
        ModelTypeEnum.HMM_GAUSSIAN,
        description="Model type for regime detection"
    )
    emission_distribution: EmissionDistributionType = Field(
        EmissionDistributionType.GAUSSIAN,
        description="Emission distribution type (for HMM models)"
    )
    student_t_df: float = Field(
        5.0, ge=2.0, le=30.0,
        description="Degrees of freedom for Student-t distribution"
    )

    # Feature selection
    selected_features: List[str] = Field(
        default=["log_return", "range", "volume_change"],
        description="List of features to use for HMM training"
    )

    # Rolling refit configuration
    enable_rolling_refit: bool = Field(False, description="Enable rolling window refit")
    rolling_window_size: int = Field(
        252, ge=63, le=1260,
        description="Rolling window size in trading days"
    )
    refit_interval: int = Field(
        63, ge=21, le=252,
        description="Refit interval in trading days"
    )

    # Strategy parameters for signal generation
    required_confirmations: int = Field(7, ge=1, le=8, description="Required confirmations for signal")
    rsi_oversold: float = Field(30.0, ge=0, le=50, description="RSI oversold threshold")
    rsi_overbought: float = Field(70.0, ge=50, le=100, description="RSI overbought threshold")
    rsi_bull_min: float = Field(40.0, ge=0, le=100, description="Minimum RSI for bullish signal")
    rsi_bear_max: float = Field(60.0, ge=0, le=100, description="Maximum RSI for bearish signal")
    macd_threshold: float = Field(0.0, ge=-10, le=10, description="MACD threshold")
    momentum_threshold: float = Field(0.0, ge=-10, le=10, description="Momentum threshold")
    adx_trend_threshold: float = Field(25.0, ge=0, le=100, description="ADX threshold for trend strength")
    volume_ratio_threshold: float = Field(1.0, ge=0, le=10, description="Volume ratio threshold")
    regime_confidence_min: float = Field(0.5, ge=0, le=1, description="Minimum regime confidence")
    cooldown_periods: int = Field(48, ge=0, le=200, description="Cooldown periods after exit")
    bullish_regimes: List[str] = Field(default=["Bull Run", "Bull", "Neutral Up"])
    bearish_regimes: List[str] = Field(default=["Crash", "Bear", "Neutral Down"])
    stop_loss_pct: float = Field(0.0, ge=0, le=0.5, description="Stop loss percentage")
    take_profit_pct: float = Field(0.0, ge=0, le=1.0, description="Take profit percentage")
    trailing_stop_pct: float = Field(0.0, ge=0, le=0.3, description="Trailing stop percentage")
    max_hold_periods: int = Field(0, ge=0, le=500, description="Maximum hold periods")
    ma_period: int = Field(50, description="MA period for price condition")
    exit_on_regime_change: bool = Field(True, description="Exit on regime change")
    exit_on_opposite_signal: bool = Field(True, description="Exit on opposite signal")


class HMMTrainRequest(BaseModel):
    """Request to train HMM model."""
    symbol: str = Field(..., description="Ticker symbol")
    period: str = Field("2y", description="Data period")
    interval: str = Field("1d", description="Data interval")
    n_states: int = Field(7, ge=3, le=10, description="Number of HMM states")
    n_iter: int = Field(100, ge=10, le=500, description="Training iterations")


class HMMRegimeRequest(BaseModel):
    """Request for regime series."""
    symbol: str = Field(..., description="Ticker symbol")
    period: str = Field("1y", description="Data period")
    interval: str = Field("1d", description="Data interval")
    n_states: int = Field(7, ge=3, le=10, description="Number of HMM states")


class IndicatorRequest(BaseModel):
    """Request for technical indicators."""
    symbol: str = Field(..., description="Ticker symbol")
    period: str = Field("1y", description="Data period")
    interval: str = Field("1d", description="Data interval")


class StrategyParamsSchema(BaseModel):
    """Strategy parameters for signal generation."""
    # Confirmation requirements
    required_confirmations: int = Field(7, ge=1, le=8, description="Required confirmations for signal")

    # RSI thresholds
    rsi_oversold: float = Field(30.0, ge=0, le=50, description="RSI oversold threshold")
    rsi_overbought: float = Field(70.0, ge=50, le=100, description="RSI overbought threshold")
    rsi_bull_min: float = Field(40.0, ge=0, le=100, description="Minimum RSI for bullish signal")
    rsi_bear_max: float = Field(60.0, ge=0, le=100, description="Maximum RSI for bearish signal")

    # MACD settings
    macd_threshold: float = Field(0.0, ge=-10, le=10, description="MACD threshold")

    # ADX settings
    adx_trend_threshold: float = Field(25.0, ge=0, le=100, description="ADX threshold for trend strength")

    # Momentum settings
    momentum_threshold: float = Field(0.0, ge=-10, le=10, description="Momentum threshold")

    # Volume settings
    volume_ratio_threshold: float = Field(1.0, ge=0, le=10, description="Volume ratio threshold")

    # Regime confidence threshold
    regime_confidence_min: float = Field(0.5, ge=0, le=1, description="Minimum regime confidence")

    # Cooldown settings
    cooldown_periods: int = Field(48, ge=0, le=200, description="Cooldown periods after exit")

    # Regime configuration
    bullish_regimes: List[str] = Field(
        default=["Bull Run", "Bull", "Neutral Up"],
        description="Regimes considered bullish"
    )
    bearish_regimes: List[str] = Field(
        default=["Crash", "Bear", "Neutral Down"],
        description="Regimes considered bearish"
    )

    # Risk Management
    stop_loss_pct: float = Field(0.0, ge=0, le=0.5, description="Stop loss percentage (0 = disabled)")
    take_profit_pct: float = Field(0.0, ge=0, le=1.0, description="Take profit percentage (0 = disabled)")
    trailing_stop_pct: float = Field(0.0, ge=0, le=0.3, description="Trailing stop percentage (0 = disabled)")

    # Position Management
    max_hold_periods: int = Field(0, ge=0, le=500, description="Maximum hold periods (0 = unlimited)")

    # Moving Average settings
    ma_period: int = Field(50, description="MA period for price condition")

    # Exit behavior
    exit_on_regime_change: bool = Field(True, description="Exit when regime becomes unfavorable")
    exit_on_opposite_signal: bool = Field(True, description="Exit when opposite signal appears")

    # Signal filtering
    min_regime_duration: int = Field(1, ge=1, le=20, description="Min periods in regime before signal")
    require_regime_confirmation: bool = Field(False, description="Require regime to persist 2+ periods")


class BacktestRequest(BaseModel):
    """Request for backtesting."""
    symbol: str = Field(..., description="Ticker symbol")
    period: str = Field("2y", description="Data period")
    interval: str = Field("1d", description="Data interval")
    n_states: int = Field(7, ge=3, le=10, description="Number of HMM states")
    leverage: float = Field(1.0, ge=1.0, le=10.0, description="Trading leverage")
    slippage_pct: float = Field(0.001, ge=0, le=0.01, description="Slippage percentage")
    commission_pct: float = Field(0.001, ge=0, le=0.01, description="Commission percentage")
    initial_capital: float = Field(10000.0, ge=100, description="Initial capital")

    # HMM Model configuration - CRITICAL for optimization results
    model_type: ModelTypeEnum = Field(
        ModelTypeEnum.HMM_GAUSSIAN,
        description="Model type for regime detection"
    )
    n_iter: int = Field(100, ge=10, le=500, description="Training iterations")
    selected_features: List[str] = Field(
        default=["log_return", "range", "volume_change"],
        description="List of features to use for HMM training"
    )
    student_t_df: float = Field(
        5.0, ge=2.0, le=30.0,
        description="Degrees of freedom for Student-t distribution"
    )
    force_retrain: bool = Field(False, description="Force model retraining")

    # Strategy parameters - Confirmation
    required_confirmations: int = Field(7, ge=1, le=8, description="Required confirmations for signal")

    # RSI thresholds
    rsi_oversold: float = Field(30.0, ge=0, le=50, description="RSI oversold threshold")
    rsi_overbought: float = Field(70.0, ge=50, le=100, description="RSI overbought threshold")
    rsi_bull_min: float = Field(40.0, ge=0, le=100, description="Minimum RSI for bullish signal")
    rsi_bear_max: float = Field(60.0, ge=0, le=100, description="Maximum RSI for bearish signal")

    # MACD & Momentum
    macd_threshold: float = Field(0.0, ge=-10, le=10, description="MACD threshold")
    momentum_threshold: float = Field(0.0, ge=-10, le=10, description="Momentum threshold")

    # ADX & Volume
    adx_trend_threshold: float = Field(25.0, ge=0, le=100, description="ADX threshold for trend strength")
    volume_ratio_threshold: float = Field(1.0, ge=0, le=10, description="Volume ratio threshold")

    # Regime settings
    regime_confidence_min: float = Field(0.5, ge=0, le=1, description="Minimum regime confidence")
    cooldown_periods: int = Field(48, ge=0, le=200, description="Cooldown periods after exit")

    # Regime configuration
    bullish_regimes: List[str] = Field(
        default=["Bull Run", "Bull", "Neutral Up"],
        description="Regimes considered bullish"
    )
    bearish_regimes: List[str] = Field(
        default=["Crash", "Bear", "Neutral Down"],
        description="Regimes considered bearish"
    )

    # Risk Management
    stop_loss_pct: float = Field(0.0, ge=0, le=0.5, description="Stop loss percentage (0 = disabled)")
    take_profit_pct: float = Field(0.0, ge=0, le=1.0, description="Take profit percentage (0 = disabled)")
    trailing_stop_pct: float = Field(0.0, ge=0, le=0.3, description="Trailing stop percentage (0 = disabled)")

    # Position Management
    max_hold_periods: int = Field(0, ge=0, le=500, description="Maximum hold periods (0 = unlimited)")
    ma_period: int = Field(50, description="MA period for price condition")

    # Exit behavior
    exit_on_regime_change: bool = Field(True, description="Exit when regime becomes unfavorable")
    exit_on_opposite_signal: bool = Field(True, description="Exit when opposite signal appears")


class SignalRequest(BaseModel):
    """Request for current trading signal."""
    symbol: str = Field(..., description="Ticker symbol")
    period: str = Field("1y", description="Data period")
    interval: str = Field("1d", description="Data interval")
    n_states: int = Field(7, ge=3, le=10, description="Number of HMM states")
    # Strategy parameters for signal generation
    required_confirmations: int = Field(7, ge=1, le=8, description="Required confirmations for signal")
    rsi_oversold: float = Field(30.0, ge=0, le=50, description="RSI oversold threshold")
    rsi_overbought: float = Field(70.0, ge=50, le=100, description="RSI overbought threshold")
    rsi_bull_min: float = Field(40.0, ge=0, le=100, description="Minimum RSI for bullish signal")
    rsi_bear_max: float = Field(60.0, ge=0, le=100, description="Maximum RSI for bearish signal")
    adx_trend_threshold: float = Field(25.0, ge=0, le=100, description="ADX threshold for trend strength")
    volume_ratio_threshold: float = Field(1.0, ge=0, le=10, description="Volume ratio threshold")
    regime_confidence_min: float = Field(0.5, ge=0, le=1, description="Minimum regime confidence")


# Response schemas

class HMMAnalysisResponse(BaseModel):
    """Full HMM analysis response."""
    symbol: str
    timestamp: datetime
    current_regime: RegimeInfo
    regime_series: List[RegimeDataPoint]
    indicators: IndicatorSeries
    indicator_signals: IndicatorSignals
    current_signal: TradingSignal
    is_model_trained: bool = True
    warning: Optional[str] = None
    # Model metadata
    model_type: Optional[str] = None
    selected_features: List[str] = []
    # Rolling refit data
    refit_timestamps: List[str] = []


class HMMTrainResponse(BaseModel):
    """Response after training HMM model."""
    symbol: str
    success: bool
    n_states: int
    message: str
    regime_mapping: Dict[int, str] = {}


class HMMRegimeResponse(BaseModel):
    """Response with regime series for charting."""
    symbol: str
    regime_series: List[RegimeDataPoint]
    current_regime: RegimeInfo
    warning: Optional[str] = None


class IndicatorResponse(BaseModel):
    """Response with indicator series."""
    symbol: str
    indicators: IndicatorSeries
    indicator_signals: IndicatorSignals
    warning: Optional[str] = None


class SignalResponse(BaseModel):
    """Response with current trading signal."""
    symbol: str
    signal: TradingSignal
    warning: Optional[str] = None


# ============== Optimization Schemas ==============

class OptimizationStatusEnum(str, Enum):
    """Optimization status states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class HMMOptimizationRequest(BaseModel):
    """Request to start HMM parameter optimization."""
    symbol: str = Field(..., description="Ticker symbol")
    period: str = Field("2y", description="Data period for training")
    interval: str = Field("1d", description="Data interval")

    # Current strategy params for evaluation (fixed during HMM optimization)
    required_confirmations: int = Field(7, ge=1, le=8)
    rsi_oversold: float = Field(30.0, ge=0, le=50)
    rsi_overbought: float = Field(70.0, ge=50, le=100)
    rsi_bull_min: float = Field(40.0, ge=0, le=100)
    rsi_bear_max: float = Field(60.0, ge=0, le=100)
    macd_threshold: float = Field(0.0, ge=-10, le=10)
    momentum_threshold: float = Field(0.0, ge=-10, le=10)
    adx_trend_threshold: float = Field(25.0, ge=0, le=100)
    volume_ratio_threshold: float = Field(1.0, ge=0, le=10)
    regime_confidence_min: float = Field(0.5, ge=0, le=1)
    cooldown_periods: int = Field(48, ge=0, le=200)
    bullish_regimes: List[str] = Field(default=["Bull Run", "Bull", "Neutral Up"])
    bearish_regimes: List[str] = Field(default=["Crash", "Bear", "Neutral Down"])
    stop_loss_pct: float = Field(0.0, ge=0, le=0.5)
    take_profit_pct: float = Field(0.0, ge=0, le=1.0)
    trailing_stop_pct: float = Field(0.0, ge=0, le=0.3)
    max_hold_periods: int = Field(0, ge=0, le=500)
    ma_period: int = Field(50)
    exit_on_regime_change: bool = Field(True)
    exit_on_opposite_signal: bool = Field(True)

    # Backtest settings
    leverage: float = Field(1.0, ge=1.0, le=10.0)
    slippage_pct: float = Field(0.001, ge=0, le=0.01)
    commission_pct: float = Field(0.001, ge=0, le=0.01)
    initial_capital: float = Field(10000.0, ge=100)


class StrategyOptimizationRequest(BaseModel):
    """Request to start strategy parameter optimization."""
    symbol: str = Field(..., description="Ticker symbol")
    period: str = Field("2y", description="Data period for training")
    interval: str = Field("1d", description="Data interval")

    # HMM model settings (fixed during strategy optimization)
    n_states: int = Field(7, ge=3, le=10)
    n_iter: int = Field(100, ge=10, le=500)
    model_type: ModelTypeEnum = Field(ModelTypeEnum.HMM_GAUSSIAN)
    emission_distribution: EmissionDistributionType = Field(EmissionDistributionType.GAUSSIAN)
    student_t_df: float = Field(5.0, ge=2.0, le=30.0)
    selected_features: List[str] = Field(default=["log_return", "range", "volume_change"])

    # Optimization settings
    n_trials: int = Field(200, ge=50, le=500, description="Number of optimization trials")
    timeout_seconds: int = Field(300, ge=60, le=600, description="Maximum optimization time")

    # Backtest settings
    leverage: float = Field(1.0, ge=1.0, le=10.0)
    slippage_pct: float = Field(0.001, ge=0, le=0.01)
    commission_pct: float = Field(0.001, ge=0, le=0.01)
    initial_capital: float = Field(10000.0, ge=100)


class OptimizationStartResponse(BaseModel):
    """Response when starting an optimization."""
    optimization_id: str
    status: OptimizationStatusEnum
    estimated_trials: int
    message: str


class OptimizationProgressResponse(BaseModel):
    """Response for optimization progress polling."""
    optimization_id: str
    status: OptimizationStatusEnum
    current_trial: int
    total_trials: int
    best_alpha: float
    best_params: Dict[str, Any]
    elapsed_seconds: float
    message: str


class OptimizationResultResponse(BaseModel):
    """Response with final optimization results."""
    success: bool
    best_params: Dict[str, Any]
    best_alpha: float
    best_sharpe: float
    best_total_return: float
    best_max_drawdown: float
    total_trials_evaluated: int
    optimization_time_seconds: float
    error_message: Optional[str] = None


# ============== Preset Schemas ==============

class PresetSaveRequest(BaseModel):
    """Request to save a preset."""
    name: Optional[str] = Field(None, description="Preset name (auto-generated if not provided)")

    # Metadata
    symbol: str = Field(..., description="Symbol this preset was created for")
    period: str = Field("1y", description="Data period")
    interval: str = Field("1d", description="Data interval")

    # HMM Model Settings
    n_states: int = Field(7, ge=3, le=10)
    n_iter: int = Field(100, ge=10, le=500)
    model_type: ModelTypeEnum = Field(ModelTypeEnum.HMM_GAUSSIAN)
    student_t_df: float = Field(5.0, ge=2.0, le=30.0)
    selected_features: List[str] = Field(default=["log_return", "range", "volume_change"])

    # Strategy Parameters
    required_confirmations: int = Field(7, ge=1, le=8)
    rsi_oversold: float = Field(30.0, ge=0, le=50)
    rsi_overbought: float = Field(70.0, ge=50, le=100)
    rsi_bull_min: float = Field(40.0, ge=0, le=100)
    rsi_bear_max: float = Field(60.0, ge=0, le=100)
    macd_threshold: float = Field(0.0, ge=-10, le=10)
    momentum_threshold: float = Field(0.0, ge=-10, le=10)
    adx_trend_threshold: float = Field(25.0, ge=0, le=100)
    volume_ratio_threshold: float = Field(1.0, ge=0, le=10)
    regime_confidence_min: float = Field(0.5, ge=0, le=1)
    cooldown_periods: int = Field(48, ge=0, le=200)
    bullish_regimes: List[str] = Field(default=["Bull Run", "Bull", "Neutral Up"])
    bearish_regimes: List[str] = Field(default=["Crash", "Bear", "Neutral Down"])
    stop_loss_pct: float = Field(0.0, ge=0, le=0.5)
    take_profit_pct: float = Field(0.0, ge=0, le=1.0)
    trailing_stop_pct: float = Field(0.0, ge=0, le=0.3)
    max_hold_periods: int = Field(0, ge=0, le=500)
    ma_period: int = Field(50)
    exit_on_regime_change: bool = Field(True)
    exit_on_opposite_signal: bool = Field(True)

    # Backtest Settings
    leverage: float = Field(1.0, ge=1.0, le=10.0)
    slippage_pct: float = Field(0.001, ge=0, le=0.01)
    commission_pct: float = Field(0.001, ge=0, le=0.01)
    initial_capital: float = Field(10000.0, ge=100)

    # Performance metrics (optional)
    saved_alpha: Optional[float] = None
    saved_sharpe: Optional[float] = None
    saved_total_return: Optional[float] = None


class PresetResponse(BaseModel):
    """Response with preset data."""
    name: str
    created_at: str
    updated_at: str

    # Metadata
    symbol: str
    period: str
    interval: str

    # HMM Model Settings
    n_states: int
    n_iter: int
    model_type: str
    student_t_df: float
    selected_features: List[str]

    # Strategy Parameters
    required_confirmations: int
    rsi_oversold: float
    rsi_overbought: float
    rsi_bull_min: float
    rsi_bear_max: float
    macd_threshold: float
    momentum_threshold: float
    adx_trend_threshold: float
    volume_ratio_threshold: float
    regime_confidence_min: float
    cooldown_periods: int
    bullish_regimes: List[str]
    bearish_regimes: List[str]
    stop_loss_pct: float
    take_profit_pct: float
    trailing_stop_pct: float
    max_hold_periods: int
    ma_period: int
    exit_on_regime_change: bool
    exit_on_opposite_signal: bool

    # Backtest Settings
    leverage: float
    slippage_pct: float
    commission_pct: float
    initial_capital: float

    # Performance metrics
    saved_alpha: Optional[float] = None
    saved_sharpe: Optional[float] = None
    saved_total_return: Optional[float] = None


class PresetListResponse(BaseModel):
    """Response with list of presets."""
    presets: List[PresetResponse]
    count: int
