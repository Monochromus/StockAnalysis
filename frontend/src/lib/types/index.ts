// Ticker types
export interface TickerInfo {
  symbol: string;
  name: string;
  exchange: string | null;
  type: string | null;
  currency: string | null;
}

export interface TickerSearchResult {
  symbol: string;
  name: string;
  exchange: string | null;
  score: number;
}

export interface TickerSearchResponse {
  query: string;
  results: TickerSearchResult[];
  count: number;
}

// Market data types
export interface Candle {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface OHLCVData {
  symbol: string;
  candles: Candle[];
  start_date: string;
  end_date: string;
  interval: string;
  count: number;
}

export interface ProviderMetadata {
  provider_name: string;
  provider_display_name: string;
  from_cache: boolean;
  fetch_time_ms: number | null;
}

export interface ProviderStatus {
  name: string;
  display_name: string;
  available: boolean;
  requires_api_key: boolean;
  capabilities: string[];
  priority: number;
  rate_limits: {
    per_minute: number;
    per_day: number;
    minute_remaining?: number;
    day_remaining?: number;
  };
}

export interface ProvidersStatusResponse {
  providers: ProviderStatus[];
}

export interface MarketDataResponse {
  symbol: string;
  data: OHLCVData;
  provider: ProviderMetadata | null;
  warning: string | null;
}

// Pivot types
export type PivotType = 'high' | 'low';

export interface Pivot {
  timestamp: string;
  price: number;
  type: PivotType;
  index: number;
}

// Wave types
export type WaveType = 'impulse' | 'corrective';
export type WaveLabel = '1' | '2' | '3' | '4' | '5' | 'A' | 'B' | 'C';

export interface Wave {
  label: WaveLabel;
  type: WaveType;
  start_timestamp: string;
  end_timestamp: string;
  start_price: number;
  end_price: number;
  start_index: number;
  end_index: number;
}

export interface ValidationResult {
  rule_name: string;
  rule_description: string;
  passed: boolean;
  details: string | null;
}

export interface FibonacciScore {
  wave_label: WaveLabel;
  expected_ratio: number;
  actual_ratio: number;
  deviation: number;
  score: number;
}

export interface WaveCount {
  waves: Wave[];
  wave_type: WaveType;
  is_complete: boolean;
  validation_results: ValidationResult[];
  fibonacci_scores: FibonacciScore[];
  overall_confidence: number;
  is_primary: boolean;
  projected_zones: ProjectedZone[];
  fibonacci_levels: FibonacciLevel[];
}

export interface RiskReward {
  entry_price: number;
  stop_loss: number;
  risk_reward_ratio: number;
  time_start: string | null;
  stop_time_end: string | null;
}

// Higher Degree Wave types
export type HigherDegreeLabel = '(I)' | '(II)' | '(III)';

export interface HigherDegreeWave {
  label: HigherDegreeLabel;
  start_timestamp: string;
  end_timestamp: string;
  start_price: number;
  end_price: number;
  start_index: number;
  end_index: number;
}

export interface ProjectedZone {
  label: string;
  price_top: number;
  price_bottom: number;
  time_start: string;
  time_end: string;
  start_bar_index?: number | null;
  end_bar_index?: number | null;
  zone_type: 'correction' | 'target' | 'validation';
  zone_style?: 'validation' | 'target' | 'correction';
  id?: string;        // For pin identification
  isPinned?: boolean; // Pinned status
}

export interface FibonacciLevel {
  price: number;
  ratio: number;
  label: string;
  style: 'retracement' | 'extension';
  context?: 'target' | 'correction' | 'default';
  ref_timestamp: string;
  ref_bar_index?: number | null;
}

export interface HigherDegreeAnalysis {
  completed_wave: HigherDegreeWave;
  projected_zones: ProjectedZone[];
  direction: 'up' | 'down';
}

// Analysis types
export interface AnalysisRequest {
  symbol: string;
  period?: string;
  interval?: string;
  zigzag_threshold?: number;
  start_pivot_index?: number;
}

export interface ManualWaveRequest {
  symbol: string;
  period?: string;
  interval?: string;
  pivot_indices: number[];
  zigzag_threshold?: number;
}

export type ElliottWaveMode = 'auto' | 'manual';

export interface AnalysisResponse {
  symbol: string;
  timestamp: string;
  primary_count: WaveCount | null;
  alternative_counts: WaveCount[];
  risk_reward: RiskReward | null;
  pivots: Pivot[];
  explanation: string | null;
  warning: string | null;
  higher_degree: HigherDegreeAnalysis | null;
  projected_zones: ProjectedZone[];
  fibonacci_levels: FibonacciLevel[];
}

export interface PivotResponse {
  pivots: Pivot[];
  warning: string | null;
}

// UI State types
export interface AnalysisState {
  loading: boolean;
  error: string | null;
  data: AnalysisResponse | null;
}

export interface ChartState {
  symbol: string | null;
  candles: Candle[];
  loading: boolean;
  error: string | null;
}

// HMM Types
export type HMMRegimeType =
  | 'Crash'
  | 'Bear'
  | 'Neutral Down'
  | 'Chop'
  | 'Neutral Up'
  | 'Bull'
  | 'Bull Run';

export type SignalType = 'LONG' | 'SHORT' | 'CASH' | 'HOLD';

// Model type and emission distribution enums
export type ModelType = 'hmm_gaussian' | 'hmm_student_t' | 'rs_garch' | 'bayesian_hmm';
export type EmissionDistribution = 'gaussian' | 'student_t';

// Feature configuration for HMM
export interface FeatureConfig {
  // Basic OHLCV features
  log_return: boolean;
  range: boolean;
  volume_change: boolean;

  // Momentum features
  rsi: boolean;
  macd: boolean;
  macd_histogram: boolean;
  momentum_normalized: boolean;
  roc: boolean;

  // Trend features
  adx: boolean;
  di_diff: boolean;

  // Volatility features
  bb_pct: boolean;
  atr_normalized: boolean;

  // Moving average distance features
  sma_20_dist: boolean;
  sma_50_dist: boolean;
  sma_200_dist: boolean;

  // Volume features
  volume_ratio: boolean;
}

export const DEFAULT_FEATURE_CONFIG: FeatureConfig = {
  log_return: true,
  range: true,
  volume_change: true,
  rsi: false,
  macd: false,
  macd_histogram: false,
  momentum_normalized: false,
  roc: false,
  adx: false,
  di_diff: false,
  bb_pct: false,
  atr_normalized: false,
  sma_20_dist: false,
  sma_50_dist: false,
  sma_200_dist: false,
  volume_ratio: false,
};

// Feature metadata for UI display
export interface FeatureInfo {
  key: keyof FeatureConfig;
  label: string;
  group: 'basic' | 'momentum' | 'trend' | 'volatility' | 'ma_distance' | 'volume';
  warmup: number;
}

export const FEATURE_INFO: FeatureInfo[] = [
  // Basic
  { key: 'log_return', label: 'Log Return', group: 'basic', warmup: 1 },
  { key: 'range', label: 'Range', group: 'basic', warmup: 0 },
  { key: 'volume_change', label: 'Volume Change', group: 'basic', warmup: 1 },
  // Momentum
  { key: 'rsi', label: 'RSI', group: 'momentum', warmup: 14 },
  { key: 'macd', label: 'MACD', group: 'momentum', warmup: 26 },
  { key: 'macd_histogram', label: 'MACD Histogram', group: 'momentum', warmup: 26 },
  { key: 'momentum_normalized', label: 'Momentum', group: 'momentum', warmup: 10 },
  { key: 'roc', label: 'ROC', group: 'momentum', warmup: 10 },
  // Trend
  { key: 'adx', label: 'ADX', group: 'trend', warmup: 14 },
  { key: 'di_diff', label: 'DI Diff', group: 'trend', warmup: 14 },
  // Volatility
  { key: 'bb_pct', label: 'BB %B', group: 'volatility', warmup: 20 },
  { key: 'atr_normalized', label: 'ATR', group: 'volatility', warmup: 14 },
  // MA Distance
  { key: 'sma_20_dist', label: 'SMA 20 Dist', group: 'ma_distance', warmup: 20 },
  { key: 'sma_50_dist', label: 'SMA 50 Dist', group: 'ma_distance', warmup: 50 },
  { key: 'sma_200_dist', label: 'SMA 200 Dist', group: 'ma_distance', warmup: 200 },
  // Volume
  { key: 'volume_ratio', label: 'Volume Ratio', group: 'volume', warmup: 20 },
];

export interface RegimeDataPoint {
  timestamp: string;
  regime_id: number;
  regime_name: HMMRegimeType;
  confidence: number;
  color: string;
}

export interface RegimeInfo {
  regime_id: number;
  regime_name: HMMRegimeType;
  confidence: number;
  mean_return: number;
  volatility: number;
}

export interface IndicatorDataPoint {
  timestamp: string;
  value: number;
}

export interface IndicatorSeries {
  rsi: IndicatorDataPoint[];
  macd: IndicatorDataPoint[];
  macd_signal: IndicatorDataPoint[];
  macd_histogram: IndicatorDataPoint[];
  adx: IndicatorDataPoint[];
  di_plus: IndicatorDataPoint[];
  di_minus: IndicatorDataPoint[];
  bb_upper: IndicatorDataPoint[];
  bb_middle: IndicatorDataPoint[];
  bb_lower: IndicatorDataPoint[];
  sma_20: IndicatorDataPoint[];
  sma_50: IndicatorDataPoint[];
  sma_200: IndicatorDataPoint[];
  ema_12: IndicatorDataPoint[];
  ema_26: IndicatorDataPoint[];
  atr: IndicatorDataPoint[];
  volume_ratio: IndicatorDataPoint[];
}

export interface IndicatorSignals {
  RSI: string;
  MACD: string;
  ADX: string;
  BB: string;
  MA: string;
  Momentum: string;
}

export interface ConfirmationDetails {
  regime_bullish?: boolean;
  regime_bearish?: boolean;
  regime_confidence?: boolean;
  rsi_favorable?: boolean;
  macd_bullish?: boolean;
  macd_bearish?: boolean;
  adx_bullish?: boolean;
  adx_bearish?: boolean;
  momentum_positive?: boolean;
  momentum_negative?: boolean;
  volume_strong?: boolean;
  price_above_ma?: boolean;
  price_below_ma?: boolean;
  cooldown_active?: boolean;
  chop_regime?: boolean;
}

export interface TradingSignal {
  signal: SignalType;
  confirmations_met: number;
  total_conditions: number;
  details: ConfirmationDetails;
  regime: string;
  confidence: number;
}

export interface Trade {
  entry_date: string | null;
  exit_date: string | null;
  entry_price: number;
  exit_price: number | null;
  direction: 'LONG' | 'SHORT';
  size: number;
  pnl: number | null;
  pnl_pct: number | null;
  regime_at_entry: string;
}

export interface EquityCurvePoint {
  timestamp: string;
  value: number;
}

export interface BacktestResult {
  total_return: number;
  buy_hold_return: number;
  alpha: number;
  sharpe_ratio: number;
  max_drawdown: number;
  win_rate: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  avg_win: number;
  avg_loss: number;
  profit_factor: number;
  trades: Trade[];
  equity_curve: EquityCurvePoint[];
  drawdown_curve: EquityCurvePoint[];
}

// Strategy Parameters for signal generation
export interface StrategyParams {
  // Confirmation requirements
  required_confirmations: number;

  // RSI thresholds
  rsi_oversold: number;
  rsi_overbought: number;
  rsi_bull_min: number;
  rsi_bear_max: number;

  // MACD & Momentum
  macd_threshold: number;
  momentum_threshold: number;

  // ADX & Volume
  adx_trend_threshold: number;
  volume_ratio_threshold: number;

  // Regime settings
  regime_confidence_min: number;
  cooldown_periods: number;

  // Regime configuration
  bullish_regimes: string[];
  bearish_regimes: string[];

  // Risk Management
  stop_loss_pct: number;
  take_profit_pct: number;
  trailing_stop_pct: number;

  // Position Management
  max_hold_periods: number;
  ma_period: number;

  // Exit behavior
  exit_on_regime_change: boolean;
  exit_on_opposite_signal: boolean;

  // Signal filtering
  min_regime_duration: number;
  require_regime_confirmation: boolean;
}

export const DEFAULT_STRATEGY_PARAMS: StrategyParams = {
  // Confirmation requirements
  required_confirmations: 7,

  // RSI thresholds
  rsi_oversold: 30,
  rsi_overbought: 70,
  rsi_bull_min: 40,
  rsi_bear_max: 60,

  // MACD & Momentum
  macd_threshold: 0,
  momentum_threshold: 0,

  // ADX & Volume
  adx_trend_threshold: 25,
  volume_ratio_threshold: 1.0,

  // Regime settings
  regime_confidence_min: 0.5,
  cooldown_periods: 48,

  // Regime configuration
  bullish_regimes: ['Bull Run', 'Bull', 'Neutral Up'],
  bearish_regimes: ['Crash', 'Bear', 'Neutral Down'],

  // Risk Management
  stop_loss_pct: 0,
  take_profit_pct: 0,
  trailing_stop_pct: 0,

  // Position Management
  max_hold_periods: 0,
  ma_period: 50,

  // Exit behavior
  exit_on_regime_change: true,
  exit_on_opposite_signal: true,

  // Signal filtering
  min_regime_duration: 1,
  require_regime_confirmation: false,
};

// HMM Request types
export interface HMMAnalysisRequest {
  symbol: string;
  period?: string;
  interval?: string;
  n_states?: number;
  n_iter?: number;
  force_retrain?: boolean;
  // Model configuration
  model_type?: ModelType;
  emission_distribution?: EmissionDistribution;
  student_t_df?: number;
  selected_features?: string[];
  // Rolling refit
  enable_rolling_refit?: boolean;
  rolling_window_size?: number;
  refit_interval?: number;
  // Strategy parameters
  required_confirmations?: number;
  rsi_oversold?: number;
  rsi_overbought?: number;
  rsi_bull_min?: number;
  rsi_bear_max?: number;
  adx_trend_threshold?: number;
  volume_ratio_threshold?: number;
  regime_confidence_min?: number;
}

export interface HMMTrainRequest {
  symbol: string;
  period?: string;
  interval?: string;
  n_states?: number;
  n_iter?: number;
}

// HMM Training Parameters
export interface HMMTrainingParams {
  nStates: number;
  nIter: number;
}

export interface HMMRegimeRequest {
  symbol: string;
  period?: string;
  interval?: string;
  n_states?: number;
}

export interface IndicatorRequest {
  symbol: string;
  period?: string;
  interval?: string;
}

export interface BacktestRequest {
  symbol: string;
  period?: string;
  interval?: string;
  n_states?: number;
  leverage?: number;
  slippage_pct?: number;
  commission_pct?: number;
  initial_capital?: number;
  // HMM Model configuration - CRITICAL for optimization results
  model_type?: ModelType;
  n_iter?: number;
  selected_features?: string[];
  student_t_df?: number;
  force_retrain?: boolean;
  // Strategy parameters - Confirmation
  required_confirmations?: number;
  // RSI
  rsi_oversold?: number;
  rsi_overbought?: number;
  rsi_bull_min?: number;
  rsi_bear_max?: number;
  // MACD & Momentum
  macd_threshold?: number;
  momentum_threshold?: number;
  // ADX & Volume
  adx_trend_threshold?: number;
  volume_ratio_threshold?: number;
  // Regime settings
  regime_confidence_min?: number;
  cooldown_periods?: number;
  // Regime configuration
  bullish_regimes?: string[];
  bearish_regimes?: string[];
  // Risk Management
  stop_loss_pct?: number;
  take_profit_pct?: number;
  trailing_stop_pct?: number;
  // Position Management
  max_hold_periods?: number;
  ma_period?: number;
  // Exit behavior
  exit_on_regime_change?: boolean;
  exit_on_opposite_signal?: boolean;
}

export interface SignalRequest {
  symbol: string;
  period?: string;
  interval?: string;
  n_states?: number;
  // Strategy parameters
  required_confirmations?: number;
  rsi_oversold?: number;
  rsi_overbought?: number;
  rsi_bull_min?: number;
  rsi_bear_max?: number;
  adx_trend_threshold?: number;
  volume_ratio_threshold?: number;
  regime_confidence_min?: number;
}

// HMM Response types
export interface HMMAnalysisResponse {
  symbol: string;
  timestamp: string;
  current_regime: RegimeInfo;
  regime_series: RegimeDataPoint[];
  indicators: IndicatorSeries;
  indicator_signals: IndicatorSignals;
  current_signal: TradingSignal;
  is_model_trained: boolean;
  warning: string | null;
  // Model metadata
  model_type?: string;
  selected_features?: string[];
  // Rolling refit data
  refit_timestamps?: string[];
}

export interface HMMTrainResponse {
  symbol: string;
  success: boolean;
  n_states: number;
  message: string;
  regime_mapping: Record<number, string>;
}

export interface HMMRegimeResponse {
  symbol: string;
  regime_series: RegimeDataPoint[];
  current_regime: RegimeInfo;
  warning: string | null;
}

export interface IndicatorResponse {
  symbol: string;
  indicators: IndicatorSeries;
  indicator_signals: IndicatorSignals;
  warning: string | null;
}

export interface SignalResponse {
  symbol: string;
  signal: TradingSignal;
  warning: string | null;
}

// Indicator Toggle State for UI
export interface IndicatorToggleState {
  // Overlays (on main chart)
  sma_20: boolean;
  sma_50: boolean;
  sma_200: boolean;
  ema_12: boolean;
  ema_26: boolean;
  bollinger: boolean;
  // Subplots
  volume: boolean;
  rsi: boolean;
  macd: boolean;
  adx: boolean;
  atr: boolean;
}

export const DEFAULT_INDICATOR_TOGGLES: IndicatorToggleState = {
  sma_20: false,
  sma_50: true,
  sma_200: true,
  ema_12: false,
  ema_26: false,
  bollinger: false,
  volume: true,
  rsi: true,
  macd: false,
  adx: false,
  atr: false,
};

// ============== Optimization Types ==============

export type OptimizationStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface OptimizationProgress {
  optimization_id: string;
  status: OptimizationStatus;
  current_trial: number;
  total_trials: number;
  best_alpha: number;
  best_params: Record<string, unknown>;
  elapsed_seconds: number;
  message: string;
}

export interface OptimizationResult {
  success: boolean;
  best_params: Record<string, unknown>;
  best_alpha: number;
  best_sharpe: number;
  best_total_return: number;
  best_max_drawdown: number;
  total_trials_evaluated: number;
  optimization_time_seconds: number;
  error_message: string | null;
}

export interface HMMOptimizationRequest {
  symbol: string;
  period?: string;
  interval?: string;
  // Current strategy params for evaluation
  required_confirmations?: number;
  rsi_oversold?: number;
  rsi_overbought?: number;
  rsi_bull_min?: number;
  rsi_bear_max?: number;
  macd_threshold?: number;
  momentum_threshold?: number;
  adx_trend_threshold?: number;
  volume_ratio_threshold?: number;
  regime_confidence_min?: number;
  cooldown_periods?: number;
  bullish_regimes?: string[];
  bearish_regimes?: string[];
  stop_loss_pct?: number;
  take_profit_pct?: number;
  trailing_stop_pct?: number;
  max_hold_periods?: number;
  ma_period?: number;
  exit_on_regime_change?: boolean;
  exit_on_opposite_signal?: boolean;
  // Backtest settings
  leverage?: number;
  slippage_pct?: number;
  commission_pct?: number;
  initial_capital?: number;
}

export interface StrategyOptimizationRequest {
  symbol: string;
  period?: string;
  interval?: string;
  // HMM model settings
  n_states?: number;
  n_iter?: number;
  model_type?: ModelType;
  emission_distribution?: EmissionDistribution;
  student_t_df?: number;
  selected_features?: string[];
  // Optimization settings
  n_trials?: number;
  timeout_seconds?: number;
  // Backtest settings
  leverage?: number;
  slippage_pct?: number;
  commission_pct?: number;
  initial_capital?: number;
}

export interface OptimizationStartResponse {
  optimization_id: string;
  status: OptimizationStatus;
  estimated_trials: number;
  message: string;
}

export interface OptimizationState {
  isRunning: boolean;
  optimizationId: string | null;
  progress: OptimizationProgress | null;
  result: OptimizationResult | null;
}

// ============== Preset Types ==============

export interface PresetSaveRequest {
  name?: string;
  symbol: string;
  period: string;
  interval: string;
  // HMM Model Settings
  n_states: number;
  n_iter: number;
  model_type: ModelType;
  student_t_df: number;
  selected_features: string[];
  // Strategy Parameters
  required_confirmations: number;
  rsi_oversold: number;
  rsi_overbought: number;
  rsi_bull_min: number;
  rsi_bear_max: number;
  macd_threshold: number;
  momentum_threshold: number;
  adx_trend_threshold: number;
  volume_ratio_threshold: number;
  regime_confidence_min: number;
  cooldown_periods: number;
  bullish_regimes: string[];
  bearish_regimes: string[];
  stop_loss_pct: number;
  take_profit_pct: number;
  trailing_stop_pct: number;
  max_hold_periods: number;
  ma_period: number;
  exit_on_regime_change: boolean;
  exit_on_opposite_signal: boolean;
  // Backtest Settings
  leverage: number;
  slippage_pct: number;
  commission_pct: number;
  initial_capital: number;
  // Performance metrics
  saved_alpha?: number;
  saved_sharpe?: number;
  saved_total_return?: number;
}

export interface Preset {
  name: string;
  created_at: string;
  updated_at: string;
  symbol: string;
  period: string;
  interval: string;
  // HMM Model Settings
  n_states: number;
  n_iter: number;
  model_type: string;
  student_t_df: number;
  selected_features: string[];
  // Strategy Parameters
  required_confirmations: number;
  rsi_oversold: number;
  rsi_overbought: number;
  rsi_bull_min: number;
  rsi_bear_max: number;
  macd_threshold: number;
  momentum_threshold: number;
  adx_trend_threshold: number;
  volume_ratio_threshold: number;
  regime_confidence_min: number;
  cooldown_periods: number;
  bullish_regimes: string[];
  bearish_regimes: string[];
  stop_loss_pct: number;
  take_profit_pct: number;
  trailing_stop_pct: number;
  max_hold_periods: number;
  ma_period: number;
  exit_on_regime_change: boolean;
  exit_on_opposite_signal: boolean;
  // Backtest Settings
  leverage: number;
  slippage_pct: number;
  commission_pct: number;
  initial_capital: number;
  // Performance metrics
  saved_alpha?: number;
  saved_sharpe?: number;
  saved_total_return?: number;
}

export interface PresetListResponse {
  presets: Preset[];
  count: number;
}

// ============== Prophet Types ==============

export interface ProphetForecastDataPoint {
  timestamp: string;
  value: number;
  lower: number;
  upper: number;
  is_forecast: boolean;
}

export interface ProphetComponentDataPoint {
  ds: string;
  value: number;
}

export interface ProphetForecastSeries {
  horizon: string;  // "long_term", "mid_term", "short_term"
  display_name: string;  // "Langfristig", "Mittelfristig", "Kurzfristig"
  color: string;
  training_end_date: string;
  forecast_start_date: string;
  mape: number | null;
  rmse: number | null;
  series: ProphetForecastDataPoint[];
}

export interface ProphetComponentSeries {
  trend: ProphetComponentDataPoint[];
  weekly: ProphetComponentDataPoint[] | null;
  monthly: ProphetComponentDataPoint[] | null;
  yearly: ProphetComponentDataPoint[] | null;
}

export interface ProphetForecastMetrics {
  mape: number | null;
  rmse: number | null;
}

export interface ProphetHorizonSummary {
  horizon: string;
  display_name: string;
  color: string;
  training_end_date: string;
  forecast_start_date: string;
  metrics: ProphetForecastMetrics;
  last_actual_value: number;
  forecast_30d: number | null;
  forecast_90d: number | null;
  forecast_365d: number | null;
}

// Prophet Request types
export interface ProphetAnalysisRequest {
  symbol: string;
  period?: string;
  interval?: string;
  forecast_periods?: number;
  yearly_seasonality?: boolean;
  weekly_seasonality?: boolean;
  changepoint_prior_scale?: number;
  interval_width?: number;
  force_refresh?: boolean;
}

export interface ProphetPriceRequest {
  symbol: string;
  period?: string;
  interval?: string;
  forecast_periods?: number;
}

export interface ProphetIndicatorsRequest {
  symbol: string;
  period?: string;
  interval?: string;
  forecast_periods?: number;
}

// Prophet Response types
export interface ProphetAnalysisResponse {
  symbol: string;
  timestamp: string;
  period: string;
  interval: string;
  forecast_periods: number;
  price_forecasts: ProphetForecastSeries[];
  volatility_forecasts: ProphetForecastSeries[];
  rsi_forecasts: ProphetForecastSeries[];
  price_summaries: ProphetHorizonSummary[];
  from_cache: boolean;
  warning: string | null;
}

export interface ProphetPriceResponse {
  symbol: string;
  timestamp: string;
  forecasts: ProphetForecastSeries[];
  summaries: ProphetHorizonSummary[];
  warning: string | null;
}

export interface ProphetIndicatorsResponse {
  symbol: string;
  timestamp: string;
  volatility_forecasts: ProphetForecastSeries[];
  rsi_forecasts: ProphetForecastSeries[];
  warning: string | null;
}

export interface ProphetComponentsResponse {
  symbol: string;
  horizon: string;
  components: ProphetComponentSeries;
  warning: string | null;
}

// Prophet UI state types
export interface ProphetHorizonToggles {
  long_term: boolean;
  mid_term: boolean;
  short_term: boolean;
}

export const DEFAULT_PROPHET_HORIZON_TOGGLES: ProphetHorizonToggles = {
  long_term: true,
  mid_term: true,
  short_term: true,
};

// Prophet Backtest types
export interface ProphetBacktestRequest {
  symbol: string;
  cutoff_date: string;  // YYYY-MM-DD - training ends BEFORE this date
  period?: string;
  interval?: string;
  forecast_periods?: number;
  yearly_seasonality?: boolean;
  weekly_seasonality?: boolean;
  changepoint_prior_scale?: number;
  interval_width?: number;
}

export interface ProphetBacktestMetrics {
  mape: number;
  rmse: number;
  mae: number;
  correlation: number;
  r_squared: number;
  direction_accuracy: number;
  days_forecasted: number;
  days_with_actual: number;
}

export interface BacktestDataPoint {
  timestamp: string;
  actual: number | null;
  forecast: number;
  lower: number;
  upper: number;
  error: number | null;
  error_pct: number | null;
}

export interface ProphetBacktestResponse {
  symbol: string;
  timestamp: string;
  cutoff_date: string;
  today_date: string;
  forecast_end_date: string;
  actual_prices: ProphetForecastDataPoint[];
  backtest_forecast: ProphetForecastSeries;
  metrics: ProphetBacktestMetrics;
  comparison_data: BacktestDataPoint[];
  from_cache: boolean;
  warning: string | null;
}

export interface ProphetSettings {
  period: string;
  interval: string;
  forecast_periods: number;
  yearly_seasonality: boolean;
  weekly_seasonality: boolean;
  changepoint_prior_scale: number;
  interval_width: number;
}

export const DEFAULT_PROPHET_SETTINGS: ProphetSettings = {
  period: '5y',
  interval: '1d',
  forecast_periods: 365,
  yearly_seasonality: true,
  weekly_seasonality: true,
  changepoint_prior_scale: 0.05,
  interval_width: 0.80,  // 80% confidence interval
};

// ============== XGBoost Types ==============

export interface XGBoostSettings {
  n_estimators: number;
  max_depth: number;
  learning_rate: number;
  subsample: number;
  colsample_bytree: number;
  min_child_weight: number;
  reg_alpha: number;
  reg_lambda: number;
}

export const DEFAULT_XGBOOST_SETTINGS: XGBoostSettings = {
  n_estimators: 500,
  max_depth: 4,
  learning_rate: 0.05,
  subsample: 0.8,
  colsample_bytree: 0.8,
  min_child_weight: 5,
  reg_alpha: 0.1,
  reg_lambda: 1.0,
};

export interface XGBoostFeatureToggles {
  use_time_features: boolean;
  use_lag_features: boolean;
  use_rolling_features: boolean;
  use_prophet_components: boolean;
  use_market_structure: boolean;
}

export const DEFAULT_XGBOOST_FEATURE_TOGGLES: XGBoostFeatureToggles = {
  use_time_features: true,
  use_lag_features: true,
  use_rolling_features: true,
  use_prophet_components: true,
  use_market_structure: true,
};

export interface XGBoostMetrics {
  // Prophet-only metrics
  prophet_mae: number;
  prophet_rmse: number;
  prophet_mape: number;
  prophet_r2: number;
  // Hybrid metrics
  hybrid_mae: number;
  hybrid_rmse: number;
  hybrid_mape: number;
  hybrid_r2: number;
  // Improvement percentages
  mae_improvement_pct: number;
  rmse_improvement_pct: number;
  mape_improvement_pct: number;
  r2_improvement_pct: number;
}

export interface FeatureImportance {
  feature_name: string;
  importance: number;
  rank: number;
}

export interface HybridForecastDataPoint {
  timestamp: string;
  prophet_value: number;
  hybrid_value: number;
  lower: number;
  upper: number;
  is_forecast: boolean;
}

export interface HybridForecastSeries {
  horizon: string;
  display_name: string;
  color: string;
  training_end_date: string;
  forecast_start_date: string;
  series: HybridForecastDataPoint[];
}

// XGBoost Request types
export interface XGBoostAnalysisRequest {
  symbol: string;
  period?: string;
  interval?: string;
  forecast_periods?: number;
  settings?: XGBoostSettings;
  feature_toggles?: XGBoostFeatureToggles;
  force_refresh?: boolean;
}

// XGBoost Response types
export interface XGBoostAnalysisResponse {
  symbol: string;
  timestamp: string;
  period: string;
  interval: string;
  forecast_periods: number;
  hybrid_forecasts: HybridForecastSeries[];
  metrics: XGBoostMetrics | null;
  feature_importance: FeatureImportance[];
  settings: XGBoostSettings;
  feature_toggles: XGBoostFeatureToggles;
  from_cache: boolean;
  warning: string | null;
}

export interface XGBoostComparisonResponse {
  symbol: string;
  timestamp: string;
  prophet_last_value: number;
  prophet_forecast_30d: number | null;
  prophet_forecast_90d: number | null;
  hybrid_last_value: number;
  hybrid_forecast_30d: number | null;
  hybrid_forecast_90d: number | null;
  metrics: XGBoostMetrics;
  feature_importance: FeatureImportance[];
  warning: string | null;
}

// ============== Seasonality Types ==============

export interface MonthlyReturn {
  month: number;  // 1-12
  avg_return: number;
  median_return: number;
  std_dev: number;
  positive_pct: number;  // 0-100
  sample_size: number;
}

export interface DailySeasonality {
  day_of_year: number;  // 1-366
  month: number;  // 1-12
  day: number;  // 1-31
  value: number;  // Prophet yearly component
  is_bullish: boolean;  // value > 0
}

export interface SeasonalityAnalysisRequest {
  symbol: string;
  period?: string;
  interval?: string;
}

export interface SeasonalityAnalysisResponse {
  symbol: string;
  timestamp: string;
  monthly_returns: MonthlyReturn[];
  daily_seasonality: DailySeasonality[];
  warning: string | null;
}

// Watchlist item stored in localStorage
export interface WatchlistItem {
  symbol: string;
  name?: string;
  addedAt: string;  // ISO timestamp
}

// View mode for switching between chart, calendar, and news
export type ViewMode = 'chart' | 'calendar' | 'news';

// ============== News Dashboard Types ==============

export type MarketSentiment = 'bullish' | 'bearish' | 'neutral';
export type ImpactLevel = 'high' | 'medium' | 'low';

export interface SourceLink {
  title: string;
  url: string;
  grounding_score: number | null;
}

export interface UpcomingEvent {
  date: string;
  description: string;
  impact: ImpactLevel;
  source: string | null;
  grounding_score: number | null;
}

export interface MarketAssessment {
  summary: string;
  sentiment: MarketSentiment;
  confidence: number;
  key_factors: string[];
}

export interface SupplyDemandInfo {
  supply_summary: string;
  demand_summary: string;
  balance_outlook: string;
}

export interface MacroFactors {
  factors: string[];
  summary: string;
}

export interface CommodityNewsAnalysis {
  symbol: string;
  commodity_name: string;
  timestamp: string;
  market_assessment: MarketAssessment;
  news_summary: string;
  news_highlights: string[];
  supply_demand: SupplyDemandInfo | null;
  macro_factors: MacroFactors | null;
  upcoming_events: UpcomingEvent[];
  sources: SourceLink[];
  rendered_content: string | null;
  from_cache: boolean;
  cache_timestamp: string | null;
}

// News Request/Response types
export interface NewsAnalysisResponse {
  success: boolean;
  analysis: CommodityNewsAnalysis | null;
  error: string | null;
}

export interface NewsDashboardResponse {
  success: boolean;
  analyses: CommodityNewsAnalysis[];
  errors: Record<string, string>;
  timestamp: string;
}

export interface NewsStatusResponse {
  available: boolean;
  api_key_configured: boolean;
  model_name: string;
  cache_enabled: boolean;
  cache_ttl_seconds: number;
  error: string | null;
}
