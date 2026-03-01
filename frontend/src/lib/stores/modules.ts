/**
 * Analysis Modules Store
 *
 * Manages the state of different analysis modules.
 * Each module can be independently enabled/disabled and combined with others.
 *
 * Current modules:
 * - elliottWaves: Elliott Wave Analysis with pivot detection
 * - hmm: HMM Regime Detection with indicators
 *
 * Future modules can be easily added by extending the ModuleState interface.
 */

import { writable, derived } from 'svelte/store';

export type ModuleId = 'elliottWaves' | 'hmm' | 'prophet';

export interface ModuleConfig {
  id: ModuleId;
  name: string;
  shortName: string;
  description: string;
  icon: string; // SVG path
  color: string; // Active color class
}

export interface ModuleState {
  elliottWaves: boolean;
  hmm: boolean;
  prophet: boolean;
}

// Module configurations - easily extensible for new modules
export const MODULE_CONFIGS: Record<ModuleId, ModuleConfig> = {
  elliottWaves: {
    id: 'elliottWaves',
    name: 'Elliott Waves',
    shortName: 'EW',
    description: 'Elliott Wave Analysis with automatic pivot detection and wave counting',
    icon: 'M3 3v18h18M7 16l4-8 4 6 4-10', // Wave-like pattern
    color: 'amber',
  },
  hmm: {
    id: 'hmm',
    name: 'HMM Regime',
    shortName: 'HMM',
    description: 'Hidden Markov Model for market regime detection and trading signals',
    icon: 'M3 3v18h18M18 17V9M13 17V5M8 17v-3', // Bar chart pattern
    color: 'emerald',
  },
  prophet: {
    id: 'prophet',
    name: 'Prophet Forecast',
    shortName: 'PRO',
    description: 'Facebook Prophet for price, volatility, and RSI forecasting',
    icon: 'M3 3v18h18M7 14l5-4 4 2 4-6', // Forecast line pattern
    color: 'blue',
  },
};

// Module order for UI display
export const MODULE_ORDER: ModuleId[] = ['elliottWaves', 'hmm', 'prophet'];

const initialState: ModuleState = {
  elliottWaves: false,
  hmm: false,
  prophet: false,
};

function createModulesStore() {
  const { subscribe, set, update } = writable<ModuleState>(initialState);

  return {
    subscribe,

    /**
     * Toggle a specific module on/off
     */
    toggle(moduleId: ModuleId) {
      update((state) => ({
        ...state,
        [moduleId]: !state[moduleId],
      }));
    },

    /**
     * Enable a specific module
     */
    enable(moduleId: ModuleId) {
      update((state) => ({
        ...state,
        [moduleId]: true,
      }));
    },

    /**
     * Disable a specific module
     */
    disable(moduleId: ModuleId) {
      update((state) => ({
        ...state,
        [moduleId]: false,
      }));
    },

    /**
     * Check if a module is enabled
     */
    isEnabled(moduleId: ModuleId): boolean {
      let enabled = false;
      const unsub = subscribe((state) => {
        enabled = state[moduleId];
      });
      unsub();
      return enabled;
    },

    /**
     * Reset all modules to disabled
     */
    reset() {
      set(initialState);
    },

    /**
     * Set multiple modules at once
     */
    setModules(modules: Partial<ModuleState>) {
      update((state) => ({
        ...state,
        ...modules,
      }));
    },
  };
}

export const modulesStore = createModulesStore();

// Derived store: List of active module IDs
export const activeModules = derived(modulesStore, ($modules) => {
  return MODULE_ORDER.filter((id) => $modules[id]);
});

// Derived store: Check if any module is active
export const hasActiveModules = derived(modulesStore, ($modules) => {
  return Object.values($modules).some((enabled) => enabled);
});

// Derived store: Get active module configs
export const activeModuleConfigs = derived(modulesStore, ($modules) => {
  return MODULE_ORDER.filter((id) => $modules[id]).map((id) => MODULE_CONFIGS[id]);
});
