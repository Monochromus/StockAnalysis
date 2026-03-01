/**
 * Svelte store for Wave Engine configuration.
 *
 * Manages:
 * - Current engine configuration
 * - Preset management
 * - Configuration validation
 * - Modification tracking
 */

import { writable, derived } from 'svelte/store';
import type {
  EngineConfig,
  DFAConfig,
  ThresholdConfig,
  RegimeConfig,
  ConfidenceWeights,
  TimeframeLevel,
} from '$lib/types/waveEngine';
import {
  DEFAULT_ENGINE_CONFIG,
  DEFAULT_DFA_CONFIG,
  DEFAULT_THRESHOLD_CONFIG,
  DEFAULT_REGIME_CONFIG,
  DEFAULT_CONFIDENCE_WEIGHTS,
  PRESET_CONFIGS,
} from '$lib/types/waveEngine';
import { debugStore } from './debug';

// ============= Types =============

interface EngineConfigState {
  config: EngineConfig;
  isModified: boolean;
  presetName: string | null;
  lastApplied: EngineConfig | null;
}

// ============= Helper Functions =============

function log(message: string, data?: unknown) {
  if (typeof import.meta !== 'undefined' && !import.meta.env?.DEV) return;
  const entry = {
    timestamp: new Date().toISOString(),
    source: 'EngineConfigStore',
    message,
    data,
  };
  console.log(`[EngineConfigStore] ${message}`, data ?? '');
  debugStore.addLog(entry);
}

function deepClone<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj));
}

function configsEqual(a: EngineConfig, b: EngineConfig): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

function applyPartialConfig(base: EngineConfig, partial: Partial<EngineConfig>): EngineConfig {
  return {
    dfa: { ...base.dfa, ...partial.dfa },
    threshold: { ...base.threshold, ...partial.threshold },
    regime: { ...base.regime, ...partial.regime },
    confidence_weights: { ...base.confidence_weights, ...partial.confidence_weights },
    fibonacci_tolerance: partial.fibonacci_tolerance ?? base.fibonacci_tolerance,
    enabled_timeframes: partial.enabled_timeframes ?? base.enabled_timeframes,
  };
}

// ============= Initial State =============

const initialState: EngineConfigState = {
  config: deepClone(DEFAULT_ENGINE_CONFIG),
  isModified: false,
  presetName: 'default',
  lastApplied: null,
};

// ============= Store Creation =============

function createEngineConfigStore() {
  const { subscribe, set, update } = writable<EngineConfigState>(initialState);

  return {
    subscribe,

    // ============= DFA Config Updates =============

    updateDFA(changes: Partial<DFAConfig>) {
      log('updateDFA', changes);
      update((state) => ({
        ...state,
        config: {
          ...state.config,
          dfa: { ...state.config.dfa, ...changes },
        },
        isModified: true,
        presetName: null,
      }));
    },

    // ============= Threshold Config Updates =============

    updateThreshold(changes: Partial<ThresholdConfig>) {
      log('updateThreshold', changes);
      update((state) => ({
        ...state,
        config: {
          ...state.config,
          threshold: { ...state.config.threshold, ...changes },
        },
        isModified: true,
        presetName: null,
      }));
    },

    // ============= Regime Config Updates =============

    updateRegime(changes: Partial<RegimeConfig>) {
      log('updateRegime', changes);
      update((state) => ({
        ...state,
        config: {
          ...state.config,
          regime: { ...state.config.regime, ...changes },
        },
        isModified: true,
        presetName: null,
      }));
    },

    // ============= Confidence Weights Updates =============

    updateConfidenceWeights(changes: Partial<ConfidenceWeights>) {
      log('updateConfidenceWeights', changes);
      update((state) => ({
        ...state,
        config: {
          ...state.config,
          confidence_weights: { ...state.config.confidence_weights, ...changes },
        },
        isModified: true,
        presetName: null,
      }));
    },

    // ============= Other Updates =============

    updateFibonacciTolerance(value: number) {
      log('updateFibonacciTolerance', value);
      update((state) => ({
        ...state,
        config: {
          ...state.config,
          fibonacci_tolerance: value,
        },
        isModified: true,
        presetName: null,
      }));
    },

    updateEnabledTimeframes(timeframes: TimeframeLevel[]) {
      log('updateEnabledTimeframes', timeframes);
      update((state) => ({
        ...state,
        config: {
          ...state.config,
          enabled_timeframes: timeframes,
        },
        isModified: true,
        presetName: null,
      }));
    },

    // ============= Preset Management =============

    applyPreset(presetName: string) {
      log('applyPreset', presetName);
      const preset = PRESET_CONFIGS[presetName];
      if (!preset) {
        console.warn(`Unknown preset: ${presetName}`);
        return;
      }

      update((state) => ({
        ...state,
        config: applyPartialConfig(deepClone(DEFAULT_ENGINE_CONFIG), preset),
        isModified: false,
        presetName,
      }));
    },

    // ============= Reset & Apply =============

    resetToDefaults() {
      log('resetToDefaults');
      update((state) => ({
        ...state,
        config: deepClone(DEFAULT_ENGINE_CONFIG),
        isModified: false,
        presetName: 'default',
      }));
    },

    revertChanges() {
      log('revertChanges');
      update((state) => ({
        ...state,
        config: state.lastApplied ? deepClone(state.lastApplied) : deepClone(DEFAULT_ENGINE_CONFIG),
        isModified: false,
      }));
    },

    markAsApplied() {
      log('markAsApplied');
      update((state) => ({
        ...state,
        lastApplied: deepClone(state.config),
        isModified: false,
      }));
    },

    // ============= Import/Export =============

    exportConfig(): EngineConfig {
      let currentConfig: EngineConfig = deepClone(DEFAULT_ENGINE_CONFIG);
      const unsubscribe = subscribe((state) => {
        currentConfig = deepClone(state.config);
      });
      unsubscribe();
      return currentConfig;
    },

    importConfig(config: EngineConfig) {
      log('importConfig', config);
      update((state) => ({
        ...state,
        config: deepClone(config),
        isModified: true,
        presetName: null,
      }));
    },

    // ============= Full State Update =============

    setConfig(config: EngineConfig) {
      log('setConfig', config);
      update((state) => ({
        ...state,
        config: deepClone(config),
        isModified: !configsEqual(config, state.lastApplied || DEFAULT_ENGINE_CONFIG),
        presetName: null,
      }));
    },
  };
}

export const engineConfigStore = createEngineConfigStore();

// ============= Derived Stores =============

/**
 * Check if confidence weights sum to approximately 1.0
 */
export const weightsValid = derived(engineConfigStore, ($store) => {
  const weights = $store.config.confidence_weights;
  const sum =
    weights.w1_threshold_distance +
    weights.w2_timeframe_consistency +
    weights.w3_dfa_stability +
    weights.w4_structural_validity;
  return Math.abs(sum - 1.0) < 0.05;
});

/**
 * Get validation warnings for current config
 */
export const configWarnings = derived(engineConfigStore, ($store) => {
  const warnings: string[] = [];
  const config = $store.config;

  // Check weight sum
  const weightSum =
    config.confidence_weights.w1_threshold_distance +
    config.confidence_weights.w2_timeframe_consistency +
    config.confidence_weights.w3_dfa_stability +
    config.confidence_weights.w4_structural_validity;

  if (Math.abs(weightSum - 1.0) >= 0.05) {
    warnings.push(`Konfidenz-Gewichte summieren sich zu ${weightSum.toFixed(2)} (sollte 1.0 sein)`);
  }

  // Check beta range
  if (config.threshold.beta_min >= config.threshold.beta_max) {
    warnings.push('β min muss kleiner als β max sein');
  }

  // Check regime thresholds
  if (config.regime.mean_reverting_threshold >= config.regime.trending_threshold) {
    warnings.push('Mean-Reverting-Schwelle muss kleiner als Trending-Schwelle sein');
  }

  // Performance warnings
  if (config.dfa.window_size > 300) {
    warnings.push('Große DFA-Fenstergröße (>300) kann die Performance beeinträchtigen');
  }

  return warnings;
});

/**
 * Current preset name or null if custom
 */
export const currentPresetName = derived(engineConfigStore, ($store) => $store.presetName);

/**
 * Whether config has unsaved changes
 */
export const hasUnsavedChanges = derived(engineConfigStore, ($store) => $store.isModified);
