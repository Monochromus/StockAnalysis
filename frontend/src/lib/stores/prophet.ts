/**
 * Prophet Store for time series forecasting.
 *
 * Manages state for Prophet-based price, volatility, and RSI forecasts
 * with three horizons: long-term, mid-term, and short-term.
 */

import { writable, derived } from 'svelte/store';
import type {
  ProphetForecastSeries,
  ProphetHorizonSummary,
  ProphetComponentSeries,
  ProphetHorizonToggles,
  ProphetSettings,
  ProphetAnalysisResponse,
  ProphetBacktestResponse,
  ProphetBacktestMetrics,
  BacktestDataPoint,
} from '$lib/types';
import { DEFAULT_PROPHET_HORIZON_TOGGLES, DEFAULT_PROPHET_SETTINGS } from '$lib/types';
import {
  analyzeProphet,
  forecastPrice,
  forecastIndicators,
  getComponents,
  backtestProphet,
} from '$lib/api/prophet';
import { debugStore } from './debug';

interface ProphetState {
  // Forecast results
  priceForecasts: ProphetForecastSeries[];
  volatilityForecasts: ProphetForecastSeries[];
  rsiForecasts: ProphetForecastSeries[];
  priceSummaries: ProphetHorizonSummary[];

  // Components (seasonality decomposition)
  components: ProphetComponentSeries | null;
  componentsHorizon: string;

  // UI state
  horizonToggles: ProphetHorizonToggles;
  showComponents: boolean;
  activeComponentWidget: 'trend' | 'weekly' | 'monthly' | 'yearly' | null;

  // Loading states
  loading: boolean;
  componentsLoading: boolean;

  // Error state
  error: string | null;
  warning: string | null;

  // Settings
  settings: ProphetSettings;

  // Symbol tracking
  symbol: string | null;

  // Cache info
  fromCache: boolean;
  lastAnalyzedAt: string | null;

  // Backtest state
  backtestEnabled: boolean;
  backtestCutoffDate: string | null;
  backtestLoading: boolean;
  backtestResult: ProphetBacktestResponse | null;
  backtestError: string | null;
}

const initialState: ProphetState = {
  priceForecasts: [],
  volatilityForecasts: [],
  rsiForecasts: [],
  priceSummaries: [],

  components: null,
  componentsHorizon: 'long_term',

  horizonToggles: { ...DEFAULT_PROPHET_HORIZON_TOGGLES },
  showComponents: false,
  activeComponentWidget: null,

  loading: false,
  componentsLoading: false,

  error: null,
  warning: null,

  settings: { ...DEFAULT_PROPHET_SETTINGS },

  symbol: null,
  fromCache: false,
  lastAnalyzedAt: null,

  // Backtest state
  backtestEnabled: false,
  backtestCutoffDate: null,
  backtestLoading: false,
  backtestResult: null,
  backtestError: null,
};

function log(message: string, data?: unknown) {
  if (typeof import.meta !== 'undefined' && !import.meta.env?.DEV) return;
  const entry = { timestamp: new Date().toISOString(), source: 'ProphetStore', message, data };
  console.log(`[ProphetStore] ${message}`, data ?? '');
  debugStore.addLog(entry);
}

function createProphetStore() {
  const { subscribe, set, update } = writable<ProphetState>(initialState);

  return {
    subscribe,

    /**
     * Perform full Prophet analysis for a symbol.
     */
    async analyze(symbol: string, forceRefresh = false) {
      log('analyze called', { symbol, forceRefresh });

      update((state) => ({
        ...state,
        loading: true,
        error: null,
        symbol,
      }));

      try {
        let settings: ProphetSettings;
        const unsub = subscribe((s) => {
          settings = s.settings;
        });
        unsub();

        const response = await analyzeProphet({
          symbol,
          period: settings!.period,
          interval: settings!.interval,
          forecast_periods: settings!.forecast_periods,
          yearly_seasonality: settings!.yearly_seasonality,
          weekly_seasonality: settings!.weekly_seasonality,
          changepoint_prior_scale: settings!.changepoint_prior_scale,
          interval_width: settings!.interval_width,
          force_refresh: forceRefresh,
        });

        log('Analysis response received', {
          priceForecasts: response.price_forecasts.length,
          volatilityForecasts: response.volatility_forecasts.length,
          rsiForecasts: response.rsi_forecasts.length,
          fromCache: response.from_cache,
        });

        update((state) => ({
          ...state,
          priceForecasts: response.price_forecasts,
          volatilityForecasts: response.volatility_forecasts,
          rsiForecasts: response.rsi_forecasts,
          priceSummaries: response.price_summaries,
          loading: false,
          warning: response.warning,
          fromCache: response.from_cache,
          lastAnalyzedAt: response.timestamp,
        }));

        return response;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Prophet analysis failed';
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
     * Fetch seasonal components for visualization.
     */
    async fetchComponents(symbol: string, horizon: string = 'long_term') {
      log('fetchComponents called', { symbol, horizon });

      update((state) => ({
        ...state,
        componentsLoading: true,
        componentsHorizon: horizon,
      }));

      try {
        let settings: ProphetSettings;
        const unsub = subscribe((s) => {
          settings = s.settings;
        });
        unsub();

        const response = await getComponents(
          symbol,
          horizon,
          settings!.period,
          settings!.interval
        );

        log('Components received', {
          hasTrend: response.components.trend.length > 0,
          hasWeekly: !!response.components.weekly,
          hasMonthly: !!response.components.monthly,
          hasYearly: !!response.components.yearly,
        });

        update((state) => ({
          ...state,
          components: response.components,
          componentsLoading: false,
          warning: response.warning,
        }));

        return response;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to fetch components';
        log('ERROR in fetchComponents', { error: errorMessage });
        update((state) => ({
          ...state,
          componentsLoading: false,
          error: errorMessage,
        }));
        return null;
      }
    },

    /**
     * Toggle a horizon on/off.
     */
    toggleHorizon(horizon: keyof ProphetHorizonToggles) {
      log('toggleHorizon', { horizon });
      update((state) => ({
        ...state,
        horizonToggles: {
          ...state.horizonToggles,
          [horizon]: !state.horizonToggles[horizon],
        },
      }));
    },

    /**
     * Set multiple horizon toggles at once.
     */
    setHorizonToggles(toggles: Partial<ProphetHorizonToggles>) {
      log('setHorizonToggles', { toggles });
      update((state) => ({
        ...state,
        horizonToggles: {
          ...state.horizonToggles,
          ...toggles,
        },
      }));
    },

    /**
     * Toggle components view.
     */
    toggleComponents() {
      log('toggleComponents');
      update((state) => ({
        ...state,
        showComponents: !state.showComponents,
      }));
    },

    /**
     * Set active component widget.
     */
    setActiveComponentWidget(widget: ProphetState['activeComponentWidget']) {
      log('setActiveComponentWidget', { widget });
      update((state) => ({
        ...state,
        activeComponentWidget: widget,
      }));
    },

    /**
     * Update settings.
     */
    updateSettings(settings: Partial<ProphetSettings>) {
      log('updateSettings', { settings });
      update((state) => ({
        ...state,
        settings: { ...state.settings, ...settings },
      }));
    },

    /**
     * Reset settings to defaults.
     */
    resetSettings() {
      log('resetSettings');
      update((state) => ({
        ...state,
        settings: { ...DEFAULT_PROPHET_SETTINGS },
      }));
    },

    /**
     * Clear all Prophet data.
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
        priceForecasts: [],
        volatilityForecasts: [],
        rsiForecasts: [],
        priceSummaries: [],
        components: null,
        error: null,
        warning: null,
        symbol: null,
        fromCache: false,
        lastAnalyzedAt: null,
        backtestResult: null,
        backtestError: null,
      }));
    },

    /**
     * Toggle backtest mode on/off.
     */
    toggleBacktest() {
      log('toggleBacktest');
      update((state) => ({
        ...state,
        backtestEnabled: !state.backtestEnabled,
        // Clear backtest result when disabling
        ...(!state.backtestEnabled ? {} : { backtestResult: null, backtestError: null }),
      }));
    },

    /**
     * Set backtest cutoff date.
     */
    setBacktestCutoffDate(date: string | null) {
      log('setBacktestCutoffDate', { date });
      update((state) => ({
        ...state,
        backtestCutoffDate: date,
      }));
    },

    /**
     * Run backtest with the current settings.
     */
    async runBacktest(symbol: string, cutoffDate: string) {
      log('runBacktest called', { symbol, cutoffDate });

      update((state) => ({
        ...state,
        backtestLoading: true,
        backtestError: null,
      }));

      try {
        let settings: ProphetSettings;
        const unsub = subscribe((s) => {
          settings = s.settings;
        });
        unsub();

        const response = await backtestProphet({
          symbol,
          cutoff_date: cutoffDate,
          period: settings!.period,
          interval: settings!.interval,
          forecast_periods: settings!.forecast_periods,
          yearly_seasonality: settings!.yearly_seasonality,
          weekly_seasonality: settings!.weekly_seasonality,
          changepoint_prior_scale: settings!.changepoint_prior_scale,
          interval_width: settings!.interval_width,
        });

        log('Backtest response received', {
          cutoffDate: response.cutoff_date,
          todayDate: response.today_date,
          metricsCorrelation: response.metrics.correlation,
          metricsMAPE: response.metrics.mape,
        });

        update((state) => ({
          ...state,
          backtestResult: response,
          backtestLoading: false,
          backtestCutoffDate: cutoffDate,
          backtestEnabled: true,  // Auto-enable when backtest completes
        }));

        return response;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Backtest failed';
        log('ERROR in runBacktest', { error: errorMessage });
        update((state) => ({
          ...state,
          backtestLoading: false,
          backtestError: errorMessage,
        }));
        return null;
      }
    },

    /**
     * Clear backtest results.
     */
    clearBacktest() {
      log('clearBacktest called');
      update((state) => ({
        ...state,
        backtestResult: null,
        backtestError: null,
        backtestCutoffDate: null,
      }));
    },
  };
}

export const prophetStore = createProphetStore();

// Derived store: Get visible price forecasts based on horizon toggles
export const visiblePriceForecasts = derived(prophetStore, ($prophet) => {
  return $prophet.priceForecasts.filter((forecast) => {
    const horizon = forecast.horizon as keyof ProphetHorizonToggles;
    return $prophet.horizonToggles[horizon];
  });
});

// Derived store: Get visible volatility forecasts based on horizon toggles
export const visibleVolatilityForecasts = derived(prophetStore, ($prophet) => {
  return $prophet.volatilityForecasts.filter((forecast) => {
    const horizon = forecast.horizon as keyof ProphetHorizonToggles;
    return $prophet.horizonToggles[horizon];
  });
});

// Derived store: Get visible RSI forecasts based on horizon toggles
export const visibleRsiForecasts = derived(prophetStore, ($prophet) => {
  return $prophet.rsiForecasts.filter((forecast) => {
    const horizon = forecast.horizon as keyof ProphetHorizonToggles;
    return $prophet.horizonToggles[horizon];
  });
});

// Derived store: Check if any forecasts are available
export const hasForecasts = derived(prophetStore, ($prophet) => {
  return $prophet.priceForecasts.length > 0;
});

// Derived store: Get training end date (from long-term forecast)
export const trainingEndDate = derived(prophetStore, ($prophet) => {
  const longTerm = $prophet.priceForecasts.find((f) => f.horizon === 'long_term');
  return longTerm?.training_end_date ?? null;
});

// Derived store: Horizon colors mapping
export const horizonColors = derived(prophetStore, () => ({
  long_term: '#1f77b4',   // Blue
  mid_term: '#2ca02c',    // Green
  short_term: '#d62728',  // Red
}));

// Derived store: Check if backtest is active
export const isBacktestActive = derived(prophetStore, ($prophet) => {
  return $prophet.backtestEnabled && $prophet.backtestResult !== null;
});

// Derived store: Get backtest forecast for chart display
export const backtestForecast = derived(prophetStore, ($prophet) => {
  return $prophet.backtestResult?.backtest_forecast ?? null;
});

// Derived store: Get backtest metrics
export const backtestMetrics = derived(prophetStore, ($prophet) => {
  return $prophet.backtestResult?.metrics ?? null;
});
