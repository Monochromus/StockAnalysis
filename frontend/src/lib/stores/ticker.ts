import { writable, derived } from 'svelte/store';
import type { TickerInfo, Candle, ProviderMetadata } from '$lib/types';
import { getMarketData } from '$lib/api/analysis';
import { debugStore } from './debug';

interface TickerState {
  symbol: string | null;
  info: TickerInfo | null;
  candles: Candle[];
  provider: ProviderMetadata | null;
  loading: boolean;
  error: string | null;
}

const initialState: TickerState = {
  symbol: null,
  info: null,
  candles: [],
  provider: null,
  loading: false,
  error: null,
};

function log(message: string, data?: any) {
  if (typeof import.meta !== 'undefined' && !import.meta.env?.DEV) return;
  const entry = { timestamp: new Date().toISOString(), source: 'TickerStore', message, data };
  console.log(`[TickerStore] ${message}`, data ?? '');
  debugStore.addLog(entry);
}

function createTickerStore() {
  const { subscribe, set, update } = writable<TickerState>(initialState);

  return {
    subscribe,

    async setSymbol(symbol: string, period: string = '5y', interval: string = '1d') {
      log('setSymbol called', { symbol, period, interval });
      update((state) => ({ ...state, loading: true, error: null }));

      try {
        log('Fetching market data...');
        const response = await getMarketData(symbol, period, interval);
        log('Market data received', {
          symbol: response.symbol,
          candleCount: response.data.candles.length,
          provider: response.provider?.provider_display_name,
          fromCache: response.provider?.from_cache,
          warning: response.warning,
          firstCandle: response.data.candles[0],
          lastCandle: response.data.candles[response.data.candles.length - 1]
        });

        update((state) => ({
          ...state,
          symbol: response.symbol,
          candles: response.data.candles,
          provider: response.provider,
          loading: false,
          error: response.warning || null,
        }));

        log('Store updated successfully', { candleCount: response.data.candles.length });
        return true;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to load data';
        log('ERROR fetching market data', { error: errorMessage });
        update((state) => ({
          ...state,
          loading: false,
          error: errorMessage,
        }));
        return false;
      }
    },

    setInfo(info: TickerInfo) {
      update((state) => ({ ...state, info }));
    },

    clear() {
      set(initialState);
    },
  };
}

export const tickerStore = createTickerStore();

// Derived store for chart-ready data
export const chartData = derived(tickerStore, ($ticker) => ({
  symbol: $ticker.symbol,
  candles: $ticker.candles.map((c) => ({
    time: new Date(c.timestamp).getTime() / 1000, // Convert to Unix timestamp
    open: c.open,
    high: c.high,
    low: c.low,
    close: c.close,
  })),
}));
