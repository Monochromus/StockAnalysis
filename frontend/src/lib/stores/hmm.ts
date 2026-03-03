/**
 * HMM Store for regime detection, indicators, signals, and backtesting.
 */

import { writable, derived } from 'svelte/store';
import type {
  RegimeInfo,
  RegimeDataPoint,
  IndicatorSeries,
  IndicatorSignals,
  TradingSignal,
  BacktestResult,
  IndicatorToggleState,
  HMMAnalysisResponse,
  StrategyParams,
  FeatureConfig,
  ModelType,
  EmissionDistribution,
  OptimizationState,
  OptimizationProgress,
  OptimizationResult,
  Preset,
} from '$lib/types';
import { DEFAULT_STRATEGY_PARAMS, DEFAULT_FEATURE_CONFIG, FEATURE_INFO } from '$lib/types';
import {
  analyzeHMM,
  trainHMM,
  getRegimeSeries,
  getIndicators,
  runBacktest,
  getSignal,
  startHMMOptimization,
  startStrategyOptimization,
  getOptimizationProgress,
  getOptimizationResult,
  cancelOptimization,
  savePreset as apiSavePreset,
  listPresets as apiListPresets,
  deletePreset as apiDeletePreset,
} from '$lib/api/hmm';
import { debugStore } from './debug';

interface HMMState {
  // Analysis results
  currentRegime: RegimeInfo | null;
  regimeSeries: RegimeDataPoint[];
  indicators: IndicatorSeries | null;
  indicatorSignals: IndicatorSignals | null;
  currentSignal: TradingSignal | null;
  backtestResult: BacktestResult | null;

  // UI state
  indicatorToggles: IndicatorToggleState;
  hmmEnabled: boolean;
  isModelTrained: boolean;
  showTradeMarkers: boolean;

  // Loading states
  loading: boolean;
  trainingLoading: boolean;
  backtestLoading: boolean;

  // Error state
  error: string | null;
  warning: string | null;

  // HMM Model Settings (Training)
  settings: {
    symbol: string | null;
    period: string;
    interval: string;
    nStates: number;
    nIter: number;
  };

  // Model configuration
  modelConfig: {
    modelType: ModelType;
    emissionDistribution: EmissionDistribution;
    studentTDf: number;
  };

  // Feature configuration
  featureConfig: FeatureConfig;

  // Rolling refit configuration
  rollingRefitConfig: {
    enabled: boolean;
    windowSize: number;
    refitInterval: number;
  };

  // Refit timestamps from analysis
  refitTimestamps: string[];

  // Strategy Parameters (Signal Generation)
  strategyParams: StrategyParams;

  // Backtest settings (Execution)
  backtestSettings: {
    leverage: number;
    slippagePct: number;
    commissionPct: number;
    initialCapital: number;
  };

  // Optimization state
  hmmOptimization: OptimizationState;
  strategyOptimization: OptimizationState;

  // Presets
  presets: Preset[];
  presetsLoading: boolean;
}

const defaultIndicatorToggles: IndicatorToggleState = {
  sma_20: false,
  sma_50: false,
  sma_200: false,
  ema_12: false,
  ema_26: false,
  bollinger: true,   // Bollinger Bands as overlay
  volume: true,      // Volume as overlay in main chart
  rsi: false,
  macd: true,        // MACD as subplot
  adx: false,
  atr: false,
};

const initialState: HMMState = {
  currentRegime: null,
  regimeSeries: [],
  indicators: null,
  indicatorSignals: null,
  currentSignal: null,
  backtestResult: null,

  indicatorToggles: { ...defaultIndicatorToggles },
  hmmEnabled: false,
  isModelTrained: false,
  showTradeMarkers: false,

  loading: false,
  trainingLoading: false,
  backtestLoading: false,

  error: null,
  warning: null,

  settings: {
    symbol: null,
    period: '1y',    // Matches default chart period
    interval: '1d',  // Matches default chart interval
    nStates: 7,
    nIter: 100,      // Training iterations
  },

  modelConfig: {
    modelType: 'hmm_gaussian',
    emissionDistribution: 'gaussian',
    studentTDf: 5.0,
  },

  featureConfig: { ...DEFAULT_FEATURE_CONFIG },

  rollingRefitConfig: {
    enabled: false,
    windowSize: 252,   // 1 year
    refitInterval: 63, // Quarterly
  },

  refitTimestamps: [],

  strategyParams: { ...DEFAULT_STRATEGY_PARAMS },

  backtestSettings: {
    leverage: 1.0,
    slippagePct: 0.001,
    commissionPct: 0.001,
    initialCapital: 10000,
  },

  hmmOptimization: {
    isRunning: false,
    optimizationId: null,
    progress: null,
    result: null,
  },

  strategyOptimization: {
    isRunning: false,
    optimizationId: null,
    progress: null,
    result: null,
  },

  presets: [],
  presetsLoading: false,
};

function log(message: string, data?: unknown) {
  if (typeof import.meta !== 'undefined' && !import.meta.env?.DEV) return;
  const entry = { timestamp: new Date().toISOString(), source: 'HMMStore', message, data };
  console.log(`[HMMStore] ${message}`, data ?? '');
  debugStore.addLog(entry);
}

function createHMMStore() {
  const { subscribe, set, update } = writable<HMMState>(initialState);

  return {
    subscribe,

    /**
     * Enable/disable HMM mode.
     */
    setHMMEnabled(enabled: boolean) {
      log('HMM mode changed', { enabled });
      update((state) => ({
        ...state,
        hmmEnabled: enabled,
      }));
    },

    /**
     * Toggle trade markers visibility.
     */
    toggleTradeMarkers() {
      log('Trade markers toggled');
      update((state) => ({
        ...state,
        showTradeMarkers: !state.showTradeMarkers,
      }));
    },

    /**
     * Perform full HMM analysis for a symbol.
     */
    async analyze(symbol: string, forceRetrain = false) {
      log('analyze called', { symbol, forceRetrain });

      update((state) => ({
        ...state,
        loading: true,
        error: null,
        settings: { ...state.settings, symbol },
      }));

      try {
        let settings: HMMState['settings'];
        let strategyParams: HMMState['strategyParams'];
        const unsub = subscribe((s) => {
          settings = s.settings;
          strategyParams = s.strategyParams;
        });
        unsub();

        // Get additional state for model config
        let modelConfig: HMMState['modelConfig'];
        let featureConfig: HMMState['featureConfig'];
        let rollingRefitConfig: HMMState['rollingRefitConfig'];
        const unsub2 = subscribe((s) => {
          modelConfig = s.modelConfig;
          featureConfig = s.featureConfig;
          rollingRefitConfig = s.rollingRefitConfig;
        });
        unsub2();

        // Convert feature config to list of selected features
        const selectedFeatures = FEATURE_INFO
          .filter(f => featureConfig![f.key])
          .map(f => f.key);

        const response = await analyzeHMM({
          symbol,
          period: settings!.period,
          interval: settings!.interval,
          n_states: settings!.nStates,
          n_iter: settings!.nIter,
          force_retrain: forceRetrain,
          // Model configuration
          model_type: modelConfig!.modelType,
          emission_distribution: modelConfig!.emissionDistribution,
          student_t_df: modelConfig!.studentTDf,
          selected_features: selectedFeatures.length > 0 ? selectedFeatures : ['log_return', 'range', 'volume_change'],
          // Rolling refit
          enable_rolling_refit: rollingRefitConfig!.enabled,
          rolling_window_size: rollingRefitConfig!.windowSize,
          refit_interval: rollingRefitConfig!.refitInterval,
          // Strategy parameters
          required_confirmations: strategyParams!.required_confirmations,
          rsi_oversold: strategyParams!.rsi_oversold,
          rsi_overbought: strategyParams!.rsi_overbought,
          rsi_bull_min: strategyParams!.rsi_bull_min,
          rsi_bear_max: strategyParams!.rsi_bear_max,
          adx_trend_threshold: strategyParams!.adx_trend_threshold,
          volume_ratio_threshold: strategyParams!.volume_ratio_threshold,
          regime_confidence_min: strategyParams!.regime_confidence_min,
        });

        log('Analysis response received', {
          regime: response.current_regime?.regime_name,
          signal: response.current_signal?.signal,
          regimeSeriesLength: response.regime_series?.length,
        });

        update((state) => ({
          ...state,
          currentRegime: response.current_regime,
          regimeSeries: response.regime_series,
          indicators: response.indicators,
          indicatorSignals: response.indicator_signals,
          currentSignal: response.current_signal,
          isModelTrained: response.is_model_trained,
          loading: false,
          warning: response.warning,
          hmmEnabled: true,
          refitTimestamps: response.refit_timestamps || [],
        }));

        // Automatically run backtest after successful analysis to show trades on chart
        if (response.is_model_trained) {
          // Run backtest in background without blocking
          this.runBacktest(symbol).catch((err) => {
            log('Auto-backtest failed', { error: err });
          });
        }

        return response;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'HMM analysis failed';
        log('ERROR in analyze', { error: errorMessage });
        update((state) => ({
          ...state,
          loading: false,
          error: errorMessage,
        }));
        return null;
      }
    },

    /**
     * Train a new HMM model.
     */
    async train(symbol: string) {
      log('train called', { symbol });

      update((state) => ({
        ...state,
        trainingLoading: true,
        error: null,
      }));

      try {
        let settings: HMMState['settings'];
        const unsub = subscribe((s) => { settings = s.settings; });
        unsub();

        const response = await trainHMM({
          symbol,
          period: settings!.period,
          interval: settings!.interval,
          n_states: settings!.nStates,
          n_iter: settings!.nIter,
        });

        log('Training response received', {
          success: response.success,
          message: response.message,
        });

        update((state) => ({
          ...state,
          trainingLoading: false,
          isModelTrained: response.success,
          error: response.success ? null : response.message,
        }));

        // If training succeeded, run analysis
        if (response.success) {
          await this.analyze(symbol);
        }

        return response;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Training failed';
        log('ERROR in train', { error: errorMessage });
        update((state) => ({
          ...state,
          trainingLoading: false,
          error: errorMessage,
        }));
        return null;
      }
    },

    /**
     * Run backtest with current settings.
     */
    async runBacktest(symbol: string) {
      log('runBacktest called', { symbol });

      update((state) => ({
        ...state,
        backtestLoading: true,
        error: null,
      }));

      try {
        let settings: HMMState['settings'];
        let backtestSettings: HMMState['backtestSettings'];
        let strategyParams: HMMState['strategyParams'];
        let modelConfig: HMMState['modelConfig'];
        let featureConfig: HMMState['featureConfig'];
        const unsub = subscribe((s) => {
          settings = s.settings;
          backtestSettings = s.backtestSettings;
          strategyParams = s.strategyParams;
          modelConfig = s.modelConfig;
          featureConfig = s.featureConfig;
        });
        unsub();

        // Convert feature config to list of selected features
        const selectedFeatures = FEATURE_INFO
          .filter(f => featureConfig![f.key])
          .map(f => f.key);

        const result = await runBacktest({
          symbol,
          period: settings!.period,
          interval: settings!.interval,
          n_states: settings!.nStates,
          leverage: backtestSettings!.leverage,
          slippage_pct: backtestSettings!.slippagePct,
          commission_pct: backtestSettings!.commissionPct,
          initial_capital: backtestSettings!.initialCapital,
          // HMM Model configuration - CRITICAL for optimization results
          model_type: modelConfig!.modelType,
          n_iter: settings!.nIter,
          selected_features: selectedFeatures.length > 0 ? selectedFeatures : ['log_return', 'range', 'volume_change'],
          student_t_df: modelConfig!.studentTDf,
          force_retrain: true, // Force retrain to ensure optimized params are used
          // Strategy parameters - Confirmation
          required_confirmations: strategyParams!.required_confirmations,
          // RSI
          rsi_oversold: strategyParams!.rsi_oversold,
          rsi_overbought: strategyParams!.rsi_overbought,
          rsi_bull_min: strategyParams!.rsi_bull_min,
          rsi_bear_max: strategyParams!.rsi_bear_max,
          // MACD & Momentum
          macd_threshold: strategyParams!.macd_threshold,
          momentum_threshold: strategyParams!.momentum_threshold,
          // ADX & Volume
          adx_trend_threshold: strategyParams!.adx_trend_threshold,
          volume_ratio_threshold: strategyParams!.volume_ratio_threshold,
          // Regime settings
          regime_confidence_min: strategyParams!.regime_confidence_min,
          cooldown_periods: strategyParams!.cooldown_periods,
          // Regime configuration
          bullish_regimes: strategyParams!.bullish_regimes,
          bearish_regimes: strategyParams!.bearish_regimes,
          // Risk Management
          stop_loss_pct: strategyParams!.stop_loss_pct,
          take_profit_pct: strategyParams!.take_profit_pct,
          trailing_stop_pct: strategyParams!.trailing_stop_pct,
          // Position Management
          max_hold_periods: strategyParams!.max_hold_periods,
          ma_period: strategyParams!.ma_period,
          // Exit behavior
          exit_on_regime_change: strategyParams!.exit_on_regime_change,
          exit_on_opposite_signal: strategyParams!.exit_on_opposite_signal,
        });

        log('Backtest result received', {
          totalReturn: result.total_return,
          sharpe: result.sharpe_ratio,
          totalTrades: result.total_trades,
        });

        update((state) => ({
          ...state,
          backtestResult: result,
          backtestLoading: false,
        }));

        return result;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Backtest failed';
        log('ERROR in runBacktest', { error: errorMessage });
        update((state) => ({
          ...state,
          backtestLoading: false,
          error: errorMessage,
        }));
        return null;
      }
    },

    /**
     * Toggle an indicator on/off.
     */
    toggleIndicator(indicator: keyof IndicatorToggleState) {
      log('toggleIndicator', { indicator });
      update((state) => ({
        ...state,
        indicatorToggles: {
          ...state.indicatorToggles,
          [indicator]: !state.indicatorToggles[indicator],
        },
      }));
    },

    /**
     * Set multiple indicator toggles at once.
     */
    setIndicatorToggles(toggles: Partial<IndicatorToggleState>) {
      log('setIndicatorToggles', { toggles });
      update((state) => ({
        ...state,
        indicatorToggles: {
          ...state.indicatorToggles,
          ...toggles,
        },
      }));
    },

    /**
     * Update HMM settings.
     */
    updateSettings(settings: Partial<HMMState['settings']>) {
      update((state) => ({
        ...state,
        settings: { ...state.settings, ...settings },
      }));
    },

    /**
     * Update backtest settings.
     */
    updateBacktestSettings(settings: Partial<HMMState['backtestSettings']>) {
      update((state) => ({
        ...state,
        backtestSettings: { ...state.backtestSettings, ...settings },
      }));
    },

    /**
     * Update strategy parameters.
     */
    updateStrategyParams(params: Partial<StrategyParams>) {
      log('updateStrategyParams', { params });
      update((state) => ({
        ...state,
        strategyParams: { ...state.strategyParams, ...params },
      }));
    },

    /**
     * Reset strategy parameters to defaults.
     */
    resetStrategyParams() {
      log('resetStrategyParams');
      update((state) => ({
        ...state,
        strategyParams: { ...DEFAULT_STRATEGY_PARAMS },
      }));
    },

    /**
     * Update model configuration.
     */
    updateModelConfig(config: Partial<HMMState['modelConfig']>) {
      log('updateModelConfig', { config });
      update((state) => ({
        ...state,
        modelConfig: { ...state.modelConfig, ...config },
      }));
    },

    /**
     * Update feature configuration.
     */
    updateFeatureConfig(config: Partial<FeatureConfig>) {
      log('updateFeatureConfig', { config });
      update((state) => ({
        ...state,
        featureConfig: { ...state.featureConfig, ...config },
      }));
    },

    /**
     * Reset feature configuration to defaults.
     */
    resetFeatureConfig() {
      log('resetFeatureConfig');
      update((state) => ({
        ...state,
        featureConfig: { ...DEFAULT_FEATURE_CONFIG },
      }));
    },

    /**
     * Update rolling refit configuration.
     */
    updateRollingRefitConfig(config: Partial<HMMState['rollingRefitConfig']>) {
      log('updateRollingRefitConfig', { config });
      update((state) => ({
        ...state,
        rollingRefitConfig: { ...state.rollingRefitConfig, ...config },
      }));
    },

    /**
     * Clear all HMM data.
     */
    clear() {
      log('clear called');
      set(initialState);
    },

    /**
     * Clear analysis data but keep settings.
     */
    clearAnalysis() {
      log('clearAnalysis called');
      update((state) => ({
        ...state,
        currentRegime: null,
        regimeSeries: [],
        indicators: null,
        indicatorSignals: null,
        currentSignal: null,
        backtestResult: null,
        isModelTrained: false,
        error: null,
        warning: null,
        refitTimestamps: [],
      }));
    },

    // ============== Optimization Methods ==============

    /**
     * Start HMM parameter optimization.
     */
    async startHMMOptimization(symbol: string) {
      log('startHMMOptimization called', { symbol });

      let settings: HMMState['settings'];
      let strategyParams: HMMState['strategyParams'];
      let backtestSettings: HMMState['backtestSettings'];
      const unsub = subscribe((s) => {
        settings = s.settings;
        strategyParams = s.strategyParams;
        backtestSettings = s.backtestSettings;
      });
      unsub();

      update((state) => ({
        ...state,
        hmmOptimization: {
          isRunning: true,
          optimizationId: null,
          progress: null,
          result: null,
        },
      }));

      try {
        const response = await startHMMOptimization({
          symbol,
          period: settings!.period,
          interval: settings!.interval,
          // Strategy params
          required_confirmations: strategyParams!.required_confirmations,
          rsi_oversold: strategyParams!.rsi_oversold,
          rsi_overbought: strategyParams!.rsi_overbought,
          rsi_bull_min: strategyParams!.rsi_bull_min,
          rsi_bear_max: strategyParams!.rsi_bear_max,
          macd_threshold: strategyParams!.macd_threshold,
          momentum_threshold: strategyParams!.momentum_threshold,
          adx_trend_threshold: strategyParams!.adx_trend_threshold,
          volume_ratio_threshold: strategyParams!.volume_ratio_threshold,
          regime_confidence_min: strategyParams!.regime_confidence_min,
          cooldown_periods: strategyParams!.cooldown_periods,
          bullish_regimes: strategyParams!.bullish_regimes,
          bearish_regimes: strategyParams!.bearish_regimes,
          stop_loss_pct: strategyParams!.stop_loss_pct,
          take_profit_pct: strategyParams!.take_profit_pct,
          trailing_stop_pct: strategyParams!.trailing_stop_pct,
          max_hold_periods: strategyParams!.max_hold_periods,
          ma_period: strategyParams!.ma_period,
          exit_on_regime_change: strategyParams!.exit_on_regime_change,
          exit_on_opposite_signal: strategyParams!.exit_on_opposite_signal,
          // Backtest settings
          leverage: backtestSettings!.leverage,
          slippage_pct: backtestSettings!.slippagePct,
          commission_pct: backtestSettings!.commissionPct,
          initial_capital: backtestSettings!.initialCapital,
        });

        update((state) => ({
          ...state,
          hmmOptimization: {
            ...state.hmmOptimization,
            optimizationId: response.optimization_id,
          },
        }));

        // Start polling for progress
        this._pollOptimizationProgress('hmm', response.optimization_id, symbol);

        return response;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'HMM optimization failed to start';
        log('ERROR in startHMMOptimization', { error: errorMessage });
        update((state) => ({
          ...state,
          hmmOptimization: {
            isRunning: false,
            optimizationId: null,
            progress: null,
            result: null,
          },
          error: errorMessage,
        }));
        return null;
      }
    },

    /**
     * Start strategy parameter optimization.
     */
    async startStrategyOptimization(symbol: string) {
      log('startStrategyOptimization called', { symbol });

      let settings: HMMState['settings'];
      let modelConfig: HMMState['modelConfig'];
      let featureConfig: HMMState['featureConfig'];
      let backtestSettings: HMMState['backtestSettings'];
      const unsub = subscribe((s) => {
        settings = s.settings;
        modelConfig = s.modelConfig;
        featureConfig = s.featureConfig;
        backtestSettings = s.backtestSettings;
      });
      unsub();

      // Convert feature config to list
      const selectedFeatures = FEATURE_INFO
        .filter(f => featureConfig![f.key])
        .map(f => f.key);

      update((state) => ({
        ...state,
        strategyOptimization: {
          isRunning: true,
          optimizationId: null,
          progress: null,
          result: null,
        },
      }));

      try {
        const response = await startStrategyOptimization({
          symbol,
          period: settings!.period,
          interval: settings!.interval,
          n_states: settings!.nStates,
          n_iter: settings!.nIter,
          model_type: modelConfig!.modelType,
          emission_distribution: modelConfig!.emissionDistribution,
          student_t_df: modelConfig!.studentTDf,
          selected_features: selectedFeatures.length > 0 ? selectedFeatures : ['log_return', 'range', 'volume_change'],
          n_trials: 200,
          timeout_seconds: 300,
          leverage: backtestSettings!.leverage,
          slippage_pct: backtestSettings!.slippagePct,
          commission_pct: backtestSettings!.commissionPct,
          initial_capital: backtestSettings!.initialCapital,
        });

        update((state) => ({
          ...state,
          strategyOptimization: {
            ...state.strategyOptimization,
            optimizationId: response.optimization_id,
          },
        }));

        // Start polling for progress
        this._pollOptimizationProgress('strategy', response.optimization_id, symbol);

        return response;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Strategy optimization failed to start';
        log('ERROR in startStrategyOptimization', { error: errorMessage });
        update((state) => ({
          ...state,
          strategyOptimization: {
            isRunning: false,
            optimizationId: null,
            progress: null,
            result: null,
          },
          error: errorMessage,
        }));
        return null;
      }
    },

    /**
     * Poll for optimization progress and handle completion.
     */
    async _pollOptimizationProgress(type: 'hmm' | 'strategy', optimizationId: string, symbol: string) {
      const pollInterval = 1000; // 1 second
      const maxPolls = 600; // 10 minutes max
      let polls = 0;

      const poll = async () => {
        polls++;
        if (polls > maxPolls) {
          log('Optimization polling timeout', { type, optimizationId });
          return;
        }

        try {
          const progress = await getOptimizationProgress(optimizationId);

          // Update progress in store
          update((state) => ({
            ...state,
            [type === 'hmm' ? 'hmmOptimization' : 'strategyOptimization']: {
              ...state[type === 'hmm' ? 'hmmOptimization' : 'strategyOptimization'],
              progress,
            },
          }));

          // Check if completed
          if (progress.status === 'completed' || progress.status === 'failed' || progress.status === 'cancelled') {
            // Get final result
            try {
              const result = await getOptimizationResult(optimizationId);
              log('Optimization completed', { type, result });

              update((state) => ({
                ...state,
                [type === 'hmm' ? 'hmmOptimization' : 'strategyOptimization']: {
                  isRunning: false,
                  optimizationId,
                  progress,
                  result,
                },
              }));

              // Apply best params if successful
              if (result.success && result.best_params) {
                if (type === 'hmm') {
                  this._applyHMMOptimizationResult(result, symbol);
                } else {
                  this._applyStrategyOptimizationResult(result, symbol);
                }
              }
            } catch (e) {
              log('Failed to get optimization result', { error: e });
              update((state) => ({
                ...state,
                [type === 'hmm' ? 'hmmOptimization' : 'strategyOptimization']: {
                  isRunning: false,
                  optimizationId,
                  progress,
                  result: null,
                },
              }));
            }
            return;
          }

          // Continue polling
          setTimeout(poll, pollInterval);
        } catch (error) {
          log('Error polling optimization progress', { error });
          // Continue polling on error (might be temporary)
          setTimeout(poll, pollInterval * 2);
        }
      };

      // Start polling
      poll();
    },

    /**
     * Apply HMM optimization results.
     */
    _applyHMMOptimizationResult(result: OptimizationResult, symbol: string) {
      const params = result.best_params;
      log('Applying HMM optimization result', { params });

      // Update HMM settings
      if (params.n_states) {
        this.updateSettings({ nStates: params.n_states as number });
      }
      if (params.n_iter) {
        this.updateSettings({ nIter: params.n_iter as number });
      }
      if (params.model_type) {
        this.updateModelConfig({ modelType: params.model_type as ModelType });
      }
      if (params.selected_features) {
        // Update feature config based on selected features
        const selectedFeatures = params.selected_features as string[];
        const newFeatureConfig: Partial<FeatureConfig> = {};
        FEATURE_INFO.forEach(f => {
          newFeatureConfig[f.key] = selectedFeatures.includes(f.key);
        });
        this.updateFeatureConfig(newFeatureConfig);
      }

      // Re-run analysis with new params
      this.analyze(symbol, true);
    },

    /**
     * Apply strategy optimization results.
     */
    _applyStrategyOptimizationResult(result: OptimizationResult, symbol: string) {
      const params = result.best_params;
      log('Applying strategy optimization result', { params });

      // Update strategy params
      const strategyUpdates: Partial<StrategyParams> = {};

      if (params.required_confirmations !== undefined) {
        strategyUpdates.required_confirmations = params.required_confirmations as number;
      }
      if (params.rsi_oversold !== undefined) {
        strategyUpdates.rsi_oversold = params.rsi_oversold as number;
      }
      if (params.rsi_overbought !== undefined) {
        strategyUpdates.rsi_overbought = params.rsi_overbought as number;
      }
      if (params.rsi_bull_min !== undefined) {
        strategyUpdates.rsi_bull_min = params.rsi_bull_min as number;
      }
      if (params.rsi_bear_max !== undefined) {
        strategyUpdates.rsi_bear_max = params.rsi_bear_max as number;
      }
      if (params.macd_threshold !== undefined) {
        strategyUpdates.macd_threshold = params.macd_threshold as number;
      }
      if (params.momentum_threshold !== undefined) {
        strategyUpdates.momentum_threshold = params.momentum_threshold as number;
      }
      if (params.adx_trend_threshold !== undefined) {
        strategyUpdates.adx_trend_threshold = params.adx_trend_threshold as number;
      }
      if (params.volume_ratio_threshold !== undefined) {
        strategyUpdates.volume_ratio_threshold = params.volume_ratio_threshold as number;
      }
      if (params.regime_confidence_min !== undefined) {
        strategyUpdates.regime_confidence_min = params.regime_confidence_min as number;
      }
      if (params.cooldown_periods !== undefined) {
        strategyUpdates.cooldown_periods = params.cooldown_periods as number;
      }
      if (params.bullish_regimes !== undefined) {
        strategyUpdates.bullish_regimes = params.bullish_regimes as string[];
      }
      if (params.bearish_regimes !== undefined) {
        strategyUpdates.bearish_regimes = params.bearish_regimes as string[];
      }
      if (params.stop_loss_pct !== undefined) {
        strategyUpdates.stop_loss_pct = params.stop_loss_pct as number;
      }
      if (params.take_profit_pct !== undefined) {
        strategyUpdates.take_profit_pct = params.take_profit_pct as number;
      }
      if (params.trailing_stop_pct !== undefined) {
        strategyUpdates.trailing_stop_pct = params.trailing_stop_pct as number;
      }
      if (params.max_hold_periods !== undefined) {
        strategyUpdates.max_hold_periods = params.max_hold_periods as number;
      }
      if (params.ma_period !== undefined) {
        strategyUpdates.ma_period = params.ma_period as number;
      }
      if (params.exit_on_regime_change !== undefined) {
        strategyUpdates.exit_on_regime_change = params.exit_on_regime_change as boolean;
      }
      if (params.exit_on_opposite_signal !== undefined) {
        strategyUpdates.exit_on_opposite_signal = params.exit_on_opposite_signal as boolean;
      }

      if (Object.keys(strategyUpdates).length > 0) {
        this.updateStrategyParams(strategyUpdates);
      }

      // Re-run backtest with new params
      this.runBacktest(symbol);
    },

    /**
     * Cancel running optimization.
     */
    async cancelOptimization(type: 'hmm' | 'strategy') {
      let optimizationId: string | null = null;
      const unsub = subscribe((s) => {
        optimizationId = type === 'hmm'
          ? s.hmmOptimization.optimizationId
          : s.strategyOptimization.optimizationId;
      });
      unsub();

      if (!optimizationId) {
        log('No optimization to cancel', { type });
        return;
      }

      log('Cancelling optimization', { type, optimizationId });

      try {
        await cancelOptimization(optimizationId);
        // The polling will handle the state update when it detects cancelled status
      } catch (error) {
        log('Error cancelling optimization', { error });
      }
    },

    // ============== Preset Methods ==============

    /**
     * Load all presets from the server.
     */
    async loadPresets() {
      log('loadPresets called');

      update((state) => ({
        ...state,
        presetsLoading: true,
      }));

      try {
        const response = await apiListPresets();
        log('Presets loaded', { count: response.count });

        update((state) => ({
          ...state,
          presets: response.presets,
          presetsLoading: false,
        }));

        return response.presets;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to load presets';
        log('ERROR loading presets', { error: errorMessage });
        update((state) => ({
          ...state,
          presetsLoading: false,
          error: errorMessage,
        }));
        return [];
      }
    },

    /**
     * Save current settings as a preset.
     */
    async savePreset(name?: string) {
      log('savePreset called', { name });

      let settings: HMMState['settings'];
      let modelConfig: HMMState['modelConfig'];
      let featureConfig: HMMState['featureConfig'];
      let strategyParams: HMMState['strategyParams'];
      let backtestSettings: HMMState['backtestSettings'];
      let backtestResult: HMMState['backtestResult'];
      const unsub = subscribe((s) => {
        settings = s.settings;
        modelConfig = s.modelConfig;
        featureConfig = s.featureConfig;
        strategyParams = s.strategyParams;
        backtestSettings = s.backtestSettings;
        backtestResult = s.backtestResult;
      });
      unsub();

      if (!settings!.symbol) {
        log('No symbol selected');
        return null;
      }

      // Convert feature config to list
      const selectedFeatures = FEATURE_INFO
        .filter(f => featureConfig![f.key])
        .map(f => f.key);

      try {
        const preset = await apiSavePreset({
          name,
          symbol: settings!.symbol,
          period: settings!.period,
          interval: settings!.interval,
          n_states: settings!.nStates,
          n_iter: settings!.nIter,
          model_type: modelConfig!.modelType,
          student_t_df: modelConfig!.studentTDf,
          selected_features: selectedFeatures.length > 0 ? selectedFeatures : ['log_return', 'range', 'volume_change'],
          required_confirmations: strategyParams!.required_confirmations,
          rsi_oversold: strategyParams!.rsi_oversold,
          rsi_overbought: strategyParams!.rsi_overbought,
          rsi_bull_min: strategyParams!.rsi_bull_min,
          rsi_bear_max: strategyParams!.rsi_bear_max,
          macd_threshold: strategyParams!.macd_threshold,
          momentum_threshold: strategyParams!.momentum_threshold,
          adx_trend_threshold: strategyParams!.adx_trend_threshold,
          volume_ratio_threshold: strategyParams!.volume_ratio_threshold,
          regime_confidence_min: strategyParams!.regime_confidence_min,
          cooldown_periods: strategyParams!.cooldown_periods,
          bullish_regimes: strategyParams!.bullish_regimes,
          bearish_regimes: strategyParams!.bearish_regimes,
          stop_loss_pct: strategyParams!.stop_loss_pct,
          take_profit_pct: strategyParams!.take_profit_pct,
          trailing_stop_pct: strategyParams!.trailing_stop_pct,
          max_hold_periods: strategyParams!.max_hold_periods,
          ma_period: strategyParams!.ma_period,
          exit_on_regime_change: strategyParams!.exit_on_regime_change,
          exit_on_opposite_signal: strategyParams!.exit_on_opposite_signal,
          leverage: backtestSettings!.leverage,
          slippage_pct: backtestSettings!.slippagePct,
          commission_pct: backtestSettings!.commissionPct,
          initial_capital: backtestSettings!.initialCapital,
          saved_alpha: backtestResult?.alpha,
          saved_sharpe: backtestResult?.sharpe_ratio,
          saved_total_return: backtestResult?.total_return,
        });

        log('Preset saved', { name: preset.name });

        // Reload presets
        await this.loadPresets();

        return preset;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to save preset';
        log('ERROR saving preset', { error: errorMessage });
        update((state) => ({
          ...state,
          error: errorMessage,
        }));
        return null;
      }
    },

    /**
     * Load a preset and apply its settings.
     */
    async loadPreset(preset: Preset) {
      log('loadPreset called', { name: preset.name });

      // Update HMM settings
      this.updateSettings({
        period: preset.period,
        interval: preset.interval,
        nStates: preset.n_states,
        nIter: preset.n_iter,
      });

      // Update model config
      this.updateModelConfig({
        modelType: preset.model_type as ModelType,
        studentTDf: preset.student_t_df,
      });

      // Update feature config
      const newFeatureConfig: Partial<FeatureConfig> = {};
      FEATURE_INFO.forEach(f => {
        newFeatureConfig[f.key] = preset.selected_features.includes(f.key);
      });
      this.updateFeatureConfig(newFeatureConfig);

      // Update strategy params
      this.updateStrategyParams({
        required_confirmations: preset.required_confirmations,
        rsi_oversold: preset.rsi_oversold,
        rsi_overbought: preset.rsi_overbought,
        rsi_bull_min: preset.rsi_bull_min,
        rsi_bear_max: preset.rsi_bear_max,
        macd_threshold: preset.macd_threshold,
        momentum_threshold: preset.momentum_threshold,
        adx_trend_threshold: preset.adx_trend_threshold,
        volume_ratio_threshold: preset.volume_ratio_threshold,
        regime_confidence_min: preset.regime_confidence_min,
        cooldown_periods: preset.cooldown_periods,
        bullish_regimes: preset.bullish_regimes,
        bearish_regimes: preset.bearish_regimes,
        stop_loss_pct: preset.stop_loss_pct,
        take_profit_pct: preset.take_profit_pct,
        trailing_stop_pct: preset.trailing_stop_pct,
        max_hold_periods: preset.max_hold_periods,
        ma_period: preset.ma_period,
        exit_on_regime_change: preset.exit_on_regime_change,
        exit_on_opposite_signal: preset.exit_on_opposite_signal,
      });

      // Update backtest settings
      this.updateBacktestSettings({
        leverage: preset.leverage,
        slippagePct: preset.slippage_pct,
        commissionPct: preset.commission_pct,
        initialCapital: preset.initial_capital,
      });

      log('Preset loaded', { name: preset.name });
    },

    /**
     * Delete a preset.
     */
    async deletePreset(name: string) {
      log('deletePreset called', { name });

      try {
        await apiDeletePreset(name);
        log('Preset deleted', { name });

        // Reload presets
        await this.loadPresets();

        return true;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to delete preset';
        log('ERROR deleting preset', { error: errorMessage });
        update((state) => ({
          ...state,
          error: errorMessage,
        }));
        return false;
      }
    },
  };
}

export const hmmStore = createHMMStore();

// Derived store for active overlay indicators (for main chart)
export const activeOverlays = derived(hmmStore, ($hmm) => {
  const overlays: string[] = [];
  if ($hmm.indicatorToggles.sma_20) overlays.push('sma_20');
  if ($hmm.indicatorToggles.sma_50) overlays.push('sma_50');
  if ($hmm.indicatorToggles.sma_200) overlays.push('sma_200');
  if ($hmm.indicatorToggles.ema_12) overlays.push('ema_12');
  if ($hmm.indicatorToggles.ema_26) overlays.push('ema_26');
  if ($hmm.indicatorToggles.bollinger) overlays.push('bollinger');
  return overlays;
});

// Derived store for active subplots
// Note: Volume is now rendered as an overlay in the main chart, not as a subplot
export const activeSubplots = derived(hmmStore, ($hmm) => {
  const subplots: string[] = [];
  // Volume is excluded - it's now an overlay in the main chart
  if ($hmm.indicatorToggles.rsi) subplots.push('rsi');
  if ($hmm.indicatorToggles.macd) subplots.push('macd');
  if ($hmm.indicatorToggles.adx) subplots.push('adx');
  if ($hmm.indicatorToggles.atr) subplots.push('atr');
  return subplots;
});

// Derived store for regime colors mapping
export const regimeColors = derived(hmmStore, () => ({
  'Crash': '#FF0000',
  'Bear': '#FF6B6B',
  'Neutral Down': '#FFB4B4',
  'Chop': '#808080',
  'Neutral Up': '#B4FFB4',
  'Bull': '#6BFF6B',
  'Bull Run': '#00FF00',
}));

// Derived store for signal color
export const signalColor = derived(hmmStore, ($hmm) => {
  const signal = $hmm.currentSignal?.signal;
  switch (signal) {
    case 'LONG':
      return '#00FF00';
    case 'SHORT':
      return '#FF0000';
    case 'CASH':
      return '#808080';
    case 'HOLD':
    default:
      return '#FFFF00';
  }
});

// Derived store for confirmation percentage
export const confirmationPercentage = derived(hmmStore, ($hmm) => {
  if (!$hmm.currentSignal) return 0;
  return Math.round(
    ($hmm.currentSignal.confirmations_met / $hmm.currentSignal.total_conditions) * 100
  );
});
