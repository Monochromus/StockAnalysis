/**
 * COT Store - Manages Commitments of Traders data.
 */

import { writable, derived } from 'svelte/store';
import type {
  COTAnalysis,
  COTDashboardItem,
  COTStatusResponse,
  COTMappingsResponse,
} from '$lib/types';
import {
  getCOTDashboard,
  getCOTAnalysis,
  refreshCOTData,
  getCOTStatus,
  getCOTMappings,
} from '$lib/api/cot';

interface COTState {
  // Dashboard data
  dashboardItems: COTDashboardItem[];
  // Full analysis data by symbol
  analyses: Map<string, COTAnalysis>;
  // Loading states
  loading: boolean;
  loadingSymbols: Set<string>;
  // Error handling
  error: string | null;
  // Status
  status: COTStatusResponse | null;
  mappings: COTMappingsResponse | null;
  lastUpdated: string | null;
}

const initialState: COTState = {
  dashboardItems: [],
  analyses: new Map(),
  loading: false,
  loadingSymbols: new Set(),
  error: null,
  status: null,
  mappings: null,
  lastUpdated: null,
};

function createCOTStore() {
  const { subscribe, set, update } = writable<COTState>(initialState);

  return {
    subscribe,

    /**
     * Load COT dashboard for multiple symbols.
     */
    async loadDashboard(symbols: string[], forceRefresh: boolean = false) {
      if (symbols.length === 0) {
        update(state => ({
          ...state,
          dashboardItems: [],
          error: null,
        }));
        return;
      }

      update(state => ({
        ...state,
        loading: true,
        error: null,
      }));

      try {
        const response = await getCOTDashboard(symbols, forceRefresh);

        // Log any errors
        if (Object.keys(response.errors).length > 0) {
          console.warn('COT dashboard errors:', response.errors);
        }

        update(state => ({
          ...state,
          dashboardItems: response.items,
          loading: false,
          lastUpdated: response.timestamp,
          error: Object.keys(response.errors).length > 0
            ? `Fehler bei ${Object.keys(response.errors).length} Symbolen`
            : null,
        }));

      } catch (e) {
        const error = e instanceof Error ? e.message : 'Unbekannter Fehler';
        update(state => ({
          ...state,
          loading: false,
          error,
        }));
      }
    },

    /**
     * Load full COT analysis for a single symbol.
     */
    async loadAnalysis(
      symbol: string,
      options?: {
        weeks?: number;
        lookbackWeeks?: number;
        forceRefresh?: boolean;
      }
    ) {
      update(state => {
        const newLoadingSymbols = new Set(state.loadingSymbols);
        newLoadingSymbols.add(symbol);
        return {
          ...state,
          loadingSymbols: newLoadingSymbols,
          error: null,
        };
      });

      try {
        const analysis = await getCOTAnalysis(symbol, options);

        update(state => {
          const newAnalyses = new Map(state.analyses);
          newAnalyses.set(symbol, analysis);
          const newLoadingSymbols = new Set(state.loadingSymbols);
          newLoadingSymbols.delete(symbol);
          return {
            ...state,
            analyses: newAnalyses,
            loadingSymbols: newLoadingSymbols,
            lastUpdated: new Date().toISOString(),
          };
        });

        return analysis;

      } catch (e) {
        const error = e instanceof Error ? e.message : 'Unbekannter Fehler';
        update(state => {
          const newLoadingSymbols = new Set(state.loadingSymbols);
          newLoadingSymbols.delete(symbol);
          return {
            ...state,
            loadingSymbols: newLoadingSymbols,
            error: `Fehler bei ${symbol}: ${error}`,
          };
        });
        return null;
      }
    },

    /**
     * Force refresh COT data for a symbol.
     */
    async refresh(symbol: string) {
      update(state => {
        const newLoadingSymbols = new Set(state.loadingSymbols);
        newLoadingSymbols.add(symbol);
        return {
          ...state,
          loadingSymbols: newLoadingSymbols,
        };
      });

      try {
        const response = await refreshCOTData(symbol);

        if (response.success) {
          // Reload the full analysis
          const analysis = await getCOTAnalysis(symbol, { forceRefresh: false });

          update(state => {
            const newAnalyses = new Map(state.analyses);
            newAnalyses.set(symbol, analysis);
            const newLoadingSymbols = new Set(state.loadingSymbols);
            newLoadingSymbols.delete(symbol);
            return {
              ...state,
              analyses: newAnalyses,
              loadingSymbols: newLoadingSymbols,
              lastUpdated: new Date().toISOString(),
            };
          });
        }

        return response;

      } catch (e) {
        const error = e instanceof Error ? e.message : 'Unbekannter Fehler';
        update(state => {
          const newLoadingSymbols = new Set(state.loadingSymbols);
          newLoadingSymbols.delete(symbol);
          return {
            ...state,
            loadingSymbols: newLoadingSymbols,
            error: `Refresh fehlgeschlagen für ${symbol}: ${error}`,
          };
        });
        return null;
      }
    },

    /**
     * Check COT API status.
     */
    async checkStatus() {
      try {
        const status = await getCOTStatus();
        update(state => ({
          ...state,
          status,
        }));
        return status;
      } catch (e) {
        console.error('Failed to get COT status:', e);
        return null;
      }
    },

    /**
     * Load symbol mappings.
     */
    async loadMappings() {
      try {
        const mappings = await getCOTMappings();
        update(state => ({
          ...state,
          mappings,
        }));
        return mappings;
      } catch (e) {
        console.error('Failed to get COT mappings:', e);
        return null;
      }
    },

    /**
     * Clear all COT data.
     */
    clear() {
      set(initialState);
    },

    /**
     * Get analysis for a specific symbol.
     */
    getAnalysis(symbol: string): COTAnalysis | undefined {
      let result: COTAnalysis | undefined;
      const unsub = subscribe(state => {
        result = state.analyses.get(symbol);
      });
      unsub();
      return result;
    },

    /**
     * Check if a symbol is supported for COT analysis.
     */
    isSupported(symbol: string): boolean {
      let supported = false;
      const unsub = subscribe(state => {
        supported = state.status?.supported_symbols?.includes(symbol) ?? false;
      });
      unsub();
      return supported;
    },
  };
}

export const cotStore = createCOTStore();

// Derived store: dashboard items sorted by group then name
export const cotDashboardSorted = derived(cotStore, ($store) =>
  [...$store.dashboardItems].sort((a, b) => {
    if (a.group !== b.group) {
      return a.group.localeCompare(b.group);
    }
    return a.commodity_name.localeCompare(b.commodity_name);
  })
);

// Derived store: group dashboard items by commodity group
export const cotByGroup = derived(cotStore, ($store) => {
  const groups = new Map<string, COTDashboardItem[]>();
  for (const item of $store.dashboardItems) {
    const group = item.group || 'Other';
    if (!groups.has(group)) {
      groups.set(group, []);
    }
    groups.get(group)!.push(item);
  }
  return groups;
});

// Derived store: check if a symbol is loading
export function isSymbolLoading(symbol: string) {
  return derived(cotStore, ($store) => $store.loadingSymbols.has(symbol));
}

// Derived store: supported symbols
export const cotSupportedSymbols = derived(cotStore, ($store) =>
  $store.status?.supported_symbols ?? []
);

// Derived store: bullish signals
export const cotBullishSignals = derived(cotStore, ($store) =>
  $store.dashboardItems.filter(item => item.signal === 'bullish')
);

// Derived store: bearish signals
export const cotBearishSignals = derived(cotStore, ($store) =>
  $store.dashboardItems.filter(item => item.signal === 'bearish')
);
