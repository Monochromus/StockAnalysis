/**
 * XGBoost Store for hybrid Prophet + XGBoost forecasting.
 *
 * Manages state for XGBoost residual correction model that improves
 * upon Prophet predictions.
 */

import { writable, derived } from 'svelte/store';
import type {
  HybridForecastSeries,
  XGBoostMetrics,
  FeatureImportance,
  XGBoostSettings,
  XGBoostFeatureToggles,
  XGBoostAnalysisResponse,
} from '$lib/types';
import {
  DEFAULT_XGBOOST_SETTINGS,
  DEFAULT_XGBOOST_FEATURE_TOGGLES,
} from '$lib/types';
import { analyzeXGBoost, getComparison } from '$lib/api/xgboost';
import { debugStore } from './debug';

interface XGBoostState {
  // Toggle for hybrid mode
  enabled: boolean;

  // Forecast results
  hybridForecasts: HybridForecastSeries[];

  // Metrics comparison (Prophet vs Hybrid)
  metrics: XGBoostMetrics | null;

  // Feature importance (top 10)
  featureImportance: FeatureImportance[];

  // Settings
  settings: XGBoostSettings;
  featureToggles: XGBoostFeatureToggles;

  // Loading states
  loading: boolean;

  // Error state
  error: string | null;
  warning: string | null;

  // Symbol tracking
  symbol: string | null;

  // Cache info
  fromCache: boolean;
  lastAnalyzedAt: string | null;
}

const initialState: XGBoostState = {
  enabled: true,  // XGBoost hybrid mode enabled by default

  hybridForecasts: [],
  metrics: null,
  featureImportance: [],

  settings: { ...DEFAULT_XGBOOST_SETTINGS },
  featureToggles: { ...DEFAULT_XGBOOST_FEATURE_TOGGLES },

  loading: false,
  error: null,
  warning: null,

  symbol: null,
  fromCache: false,
  lastAnalyzedAt: null,
};

function log(message: string, data?: unknown) {
  if (typeof import.meta !== 'undefined' && !import.meta.env?.DEV) return;
  const entry = { timestamp: new Date().toISOString(), source: 'XGBoostStore', message, data };
  console.log(`[XGBoostStore] ${message}`, data ?? '');
  debugStore.addLog(entry);
}

function createXGBoostStore() {
  const { subscribe, set, update } = writable<XGBoostState>(initialState);

  return {
    subscribe,

    /**
     * Enable or disable XGBoost hybrid mode.
     */
    setEnabled(enabled: boolean) {
      log('setEnabled', { enabled });
      update((state) => ({
        ...state,
        enabled,
      }));
    },

    /**
     * Toggle XGBoost hybrid mode.
     */
    toggle() {
      log('toggle');
      update((state) => ({
        ...state,
        enabled: !state.enabled,
      }));
    },

    /**
     * Perform XGBoost hybrid analysis for a symbol.
     */
    async analyze(symbol: string, forceRefresh = false, period = '5y', interval = '1d') {
      log('analyze called', { symbol, forceRefresh, period, interval });

      update((state) => ({
        ...state,
        loading: true,
        error: null,
        symbol,
      }));

      try {
        let settings: XGBoostSettings;
        let featureToggles: XGBoostFeatureToggles;
        const unsub = subscribe((s) => {
          settings = s.settings;
          featureToggles = s.featureToggles;
        });
        unsub();

        const response = await analyzeXGBoost({
          symbol,
          period,
          interval,
          forecast_periods: 365,
          settings: settings!,
          feature_toggles: featureToggles!,
          force_refresh: forceRefresh,
        });

        log('Analysis response received', {
          hybridForecasts: response.hybrid_forecasts.length,
          hasMetrics: !!response.metrics,
          featureImportanceCount: response.feature_importance.length,
          fromCache: response.from_cache,
          firstSeriesLength: response.hybrid_forecasts[0]?.series?.length || 0,
          firstSeriesHorizon: response.hybrid_forecasts[0]?.horizon || 'N/A',
        });

        // Debug: log raw response structure
        if (response.hybrid_forecasts.length > 0) {
          const first = response.hybrid_forecasts[0];
          log('First hybrid forecast details', {
            horizon: first.horizon,
            display_name: first.display_name,
            training_end_date: first.training_end_date,
            forecast_start_date: first.forecast_start_date,
            seriesLength: first.series?.length || 0,
            firstDataPoint: first.series?.[0],
            lastDataPoint: first.series?.[first.series?.length - 1],
          });
        }

        update((state) => ({
          ...state,
          hybridForecasts: response.hybrid_forecasts,
          metrics: response.metrics,
          featureImportance: response.feature_importance,
          loading: false,
          warning: response.warning,
          fromCache: response.from_cache,
          lastAnalyzedAt: response.timestamp,
        }));

        return response;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'XGBoost analysis failed';
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
     * Update XGBoost settings.
     */
    updateSettings(settings: Partial<XGBoostSettings>) {
      log('updateSettings', { settings });
      update((state) => ({
        ...state,
        settings: { ...state.settings, ...settings },
      }));
    },

    /**
     * Update feature toggles.
     */
    updateFeatureToggles(toggles: Partial<XGBoostFeatureToggles>) {
      log('updateFeatureToggles', { toggles });
      update((state) => ({
        ...state,
        featureToggles: { ...state.featureToggles, ...toggles },
      }));
    },

    /**
     * Reset settings to defaults.
     */
    resetSettings() {
      log('resetSettings');
      update((state) => ({
        ...state,
        settings: { ...DEFAULT_XGBOOST_SETTINGS },
        featureToggles: { ...DEFAULT_XGBOOST_FEATURE_TOGGLES },
      }));
    },

    /**
     * Clear all XGBoost data.
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
        hybridForecasts: [],
        metrics: null,
        featureImportance: [],
        error: null,
        warning: null,
        symbol: null,
        fromCache: false,
        lastAnalyzedAt: null,
      }));
    },
  };
}

export const xgboostStore = createXGBoostStore();

// Derived store: Check if hybrid forecasts are available
export const hasHybridForecasts = derived(xgboostStore, ($xgboost) => {
  return $xgboost.enabled && $xgboost.hybridForecasts.length > 0;
});

// Derived store: Get improvement summary
export const improvementSummary = derived(xgboostStore, ($xgboost) => {
  if (!$xgboost.metrics) return null;
  return {
    maeImprovement: $xgboost.metrics.mae_improvement_pct,
    rmseImprovement: $xgboost.metrics.rmse_improvement_pct,
    mapeImprovement: $xgboost.metrics.mape_improvement_pct,
    r2Improvement: $xgboost.metrics.r2_improvement_pct,
  };
});

// Derived store: Get visible hybrid forecasts (when enabled)
export const visibleHybridForecasts = derived(xgboostStore, ($xgboost) => {
  if (!$xgboost.enabled) return [];
  return $xgboost.hybridForecasts;
});
