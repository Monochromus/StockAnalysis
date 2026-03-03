/**
 * Seasonality Store for calendar analysis.
 */

import { writable, derived } from 'svelte/store';
import type {
  MonthlyReturn,
  DailySeasonality,
  SeasonalityAnalysisResponse,
} from '$lib/types';
import { analyzeSeasonality } from '$lib/api/seasonality';

interface SeasonalityState {
  // Current symbol analysis
  symbol: string | null;
  monthlyReturns: MonthlyReturn[];
  dailySeasonality: DailySeasonality[];
  lastAnalyzedAt: string | null;

  // Loading states
  loading: boolean;
  error: string | null;
  warning: string | null;

  // Cache for watchlist symbols
  watchlistCache: Map<string, {
    monthlyReturns: MonthlyReturn[];
    dailySeasonality: DailySeasonality[];
    timestamp: string;
  }>;
}

const initialState: SeasonalityState = {
  symbol: null,
  monthlyReturns: [],
  dailySeasonality: [],
  lastAnalyzedAt: null,
  loading: false,
  error: null,
  warning: null,
  watchlistCache: new Map(),
};

function createSeasonalityStore() {
  const { subscribe, set, update } = writable<SeasonalityState>(initialState);

  return {
    subscribe,

    /**
     * Analyze seasonality for a symbol.
     */
    async analyze(symbol: string, period: string = '5y') {
      update((state) => ({
        ...state,
        loading: true,
        error: null,
        symbol,
      }));

      try {
        const response = await analyzeSeasonality({
          symbol,
          period,
          interval: '1d',
        });

        update((state) => ({
          ...state,
          monthlyReturns: response.monthly_returns,
          dailySeasonality: response.daily_seasonality,
          lastAnalyzedAt: response.timestamp,
          loading: false,
          warning: response.warning,
        }));

        return response;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Seasonality analysis failed';
        update((state) => ({
          ...state,
          loading: false,
          error: errorMessage,
        }));
        return null;
      }
    },

    /**
     * Analyze a watchlist symbol and cache the result.
     */
    async analyzeWatchlistSymbol(symbol: string, period: string = '5y') {
      // Check cache first
      let cached = false;
      let cacheEntry: SeasonalityState['watchlistCache'] extends Map<string, infer V> ? V | undefined : never;
      const unsub = subscribe((state) => {
        cacheEntry = state.watchlistCache.get(symbol);
        if (cacheEntry) {
          // Cache is valid for 1 hour
          const cacheAge = Date.now() - new Date(cacheEntry.timestamp).getTime();
          cached = cacheAge < 60 * 60 * 1000;
        }
      });
      unsub();

      if (cached && cacheEntry) {
        return {
          monthlyReturns: cacheEntry.monthlyReturns,
          dailySeasonality: cacheEntry.dailySeasonality,
        };
      }

      try {
        const response = await analyzeSeasonality({
          symbol,
          period,
          interval: '1d',
        });

        // Update cache
        update((state) => {
          const newCache = new Map(state.watchlistCache);
          newCache.set(symbol, {
            monthlyReturns: response.monthly_returns,
            dailySeasonality: response.daily_seasonality,
            timestamp: new Date().toISOString(),
          });
          return { ...state, watchlistCache: newCache };
        });

        return {
          monthlyReturns: response.monthly_returns,
          dailySeasonality: response.daily_seasonality,
        };
      } catch (error) {
        console.error(`Failed to analyze ${symbol}:`, error);
        return null;
      }
    },

    /**
     * Get cached data for a watchlist symbol.
     */
    getCachedData(symbol: string) {
      let result: { monthlyReturns: MonthlyReturn[]; dailySeasonality: DailySeasonality[] } | null = null;
      const unsub = subscribe((state) => {
        const cached = state.watchlistCache.get(symbol);
        if (cached) {
          result = {
            monthlyReturns: cached.monthlyReturns,
            dailySeasonality: cached.dailySeasonality,
          };
        }
      });
      unsub();
      return result;
    },

    /**
     * Clear cache for a symbol.
     */
    clearCache(symbol: string) {
      update((state) => {
        const newCache = new Map(state.watchlistCache);
        newCache.delete(symbol);
        return { ...state, watchlistCache: newCache };
      });
    },

    /**
     * Clear all cached data.
     */
    clearAllCache() {
      update((state) => ({
        ...state,
        watchlistCache: new Map(),
      }));
    },

    /**
     * Clear current analysis.
     */
    clearAnalysis() {
      update((state) => ({
        ...state,
        symbol: null,
        monthlyReturns: [],
        dailySeasonality: [],
        lastAnalyzedAt: null,
        error: null,
        warning: null,
      }));
    },

    /**
     * Reset the store to initial state.
     */
    reset() {
      set(initialState);
    },
  };
}

export const seasonalityStore = createSeasonalityStore();

// Derived store for monthly returns sorted by month
export const sortedMonthlyReturns = derived(seasonalityStore, ($store) =>
  [...$store.monthlyReturns].sort((a, b) => a.month - b.month)
);

// Derived store for best/worst months
export const bestMonth = derived(seasonalityStore, ($store) => {
  if ($store.monthlyReturns.length === 0) return null;
  return $store.monthlyReturns.reduce((best, current) =>
    current.avg_return > best.avg_return ? current : best
  );
});

export const worstMonth = derived(seasonalityStore, ($store) => {
  if ($store.monthlyReturns.length === 0) return null;
  return $store.monthlyReturns.reduce((worst, current) =>
    current.avg_return < worst.avg_return ? current : worst
  );
});

// Month names for display
export const MONTH_NAMES = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
];

export const MONTH_NAMES_FULL = [
  'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
  'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'
];
