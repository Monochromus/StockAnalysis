/**
 * News Store - Manages Gemini-powered market research data.
 */

import { writable, derived } from 'svelte/store';
import type {
  CommodityNewsAnalysis,
  NewsStatusResponse,
} from '$lib/types';
import {
  getNewsDashboard,
  getCommodityNews,
  refreshCommodityNews,
  getNewsStatus,
} from '$lib/api/news';
import { watchlistSymbols } from './watchlist';

interface NewsState {
  analyses: Map<string, CommodityNewsAnalysis>;
  loading: boolean;
  loadingSymbols: Set<string>;
  error: string | null;
  lastUpdated: string | null;
  status: NewsStatusResponse | null;
}

const initialState: NewsState = {
  analyses: new Map(),
  loading: false,
  loadingSymbols: new Set(),
  error: null,
  lastUpdated: null,
  status: null,
};

function createNewsStore() {
  const { subscribe, set, update } = writable<NewsState>(initialState);

  return {
    subscribe,

    /**
     * Load news dashboard for all watchlist symbols.
     */
    async loadDashboard(symbols: string[], forceRefresh: boolean = false) {
      if (symbols.length === 0) {
        update(state => ({
          ...state,
          analyses: new Map(),
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
        const response = await getNewsDashboard(symbols, forceRefresh);

        const analysesMap = new Map<string, CommodityNewsAnalysis>();
        for (const analysis of response.analyses) {
          analysesMap.set(analysis.symbol, analysis);
        }

        // Log any errors
        if (Object.keys(response.errors).length > 0) {
          console.warn('News dashboard errors:', response.errors);
        }

        update(state => ({
          ...state,
          analyses: analysesMap,
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
     * Load news for a single symbol.
     */
    async loadSymbol(symbol: string, forceRefresh: boolean = false) {
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
        const response = await getCommodityNews(symbol, forceRefresh);

        if (response.success && response.analysis) {
          update(state => {
            const newAnalyses = new Map(state.analyses);
            newAnalyses.set(symbol, response.analysis!);
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
      }
    },

    /**
     * Force refresh a single symbol.
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
        const response = await refreshCommodityNews(symbol);

        if (response.success && response.analysis) {
          update(state => {
            const newAnalyses = new Map(state.analyses);
            newAnalyses.set(symbol, response.analysis!);
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
      }
    },

    /**
     * Check Gemini API status.
     */
    async checkStatus() {
      try {
        const status = await getNewsStatus();
        update(state => ({
          ...state,
          status,
        }));
        return status;
      } catch (e) {
        console.error('Failed to get news status:', e);
        return null;
      }
    },

    /**
     * Clear all news data.
     */
    clear() {
      set(initialState);
    },

    /**
     * Get analysis for a specific symbol.
     */
    getAnalysis(symbol: string): CommodityNewsAnalysis | undefined {
      let result: CommodityNewsAnalysis | undefined;
      const unsub = subscribe(state => {
        result = state.analyses.get(symbol);
      });
      unsub();
      return result;
    },
  };
}

export const newsStore = createNewsStore();

// Derived store: analyses as array (sorted by symbol)
export const newsAnalysesList = derived(newsStore, ($store) =>
  Array.from($store.analyses.values()).sort((a, b) =>
    a.commodity_name.localeCompare(b.commodity_name)
  )
);

// Derived store: check if a symbol is loading
export function isSymbolLoading(symbol: string) {
  return derived(newsStore, ($store) => $store.loadingSymbols.has(symbol));
}
