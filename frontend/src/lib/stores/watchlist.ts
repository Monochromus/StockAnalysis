/**
 * Watchlist Store with LocalStorage persistence.
 *
 * The watchlist consists of:
 * 1. Default symbols from COMMODITY_WATCHLIST (always included)
 * 2. Custom symbols added by the user via the heart button
 */

import { writable, derived } from 'svelte/store';
import type { WatchlistItem } from '$lib/types';
import { COMMODITY_WATCHLIST } from '$lib/data/commodities';

const STORAGE_KEY = 'commodity-cockpit-watchlist-custom';

// Default symbols from COMMODITY_WATCHLIST
const DEFAULT_SYMBOLS = COMMODITY_WATCHLIST.map(c => c.symbol);

interface WatchlistState {
  /** Custom items added by the user (not including defaults) */
  customItems: WatchlistItem[];
}

function loadCustomFromLocalStorage(): WatchlistItem[] {
  if (typeof window === 'undefined') return [];

  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch (e) {
    console.warn('Failed to load custom watchlist from localStorage:', e);
  }
  return [];
}

function saveCustomToLocalStorage(items: WatchlistItem[]): void {
  if (typeof window === 'undefined') return;

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  } catch (e) {
    console.warn('Failed to save custom watchlist to localStorage:', e);
  }
}

const initialState: WatchlistState = {
  customItems: [],
};

function createWatchlistStore() {
  const { subscribe, set, update } = writable<WatchlistState>(initialState);

  // Load from localStorage on initialization (only in browser)
  if (typeof window !== 'undefined') {
    const customItems = loadCustomFromLocalStorage();
    set({ customItems });
  }

  return {
    subscribe,

    /**
     * Initialize store (call on mount in browser).
     */
    init() {
      const customItems = loadCustomFromLocalStorage();
      set({ customItems });
    },

    /**
     * Add a custom symbol to the watchlist.
     * Default symbols cannot be added (they're always included).
     */
    add(symbol: string, name?: string) {
      // Skip if it's a default symbol
      if (DEFAULT_SYMBOLS.includes(symbol)) {
        return;
      }

      update((state) => {
        // Check if already exists in custom items
        if (state.customItems.some((item) => item.symbol === symbol)) {
          return state;
        }

        const newItem: WatchlistItem = {
          symbol,
          name,
          addedAt: new Date().toISOString(),
        };

        const newItems = [...state.customItems, newItem];
        saveCustomToLocalStorage(newItems);

        return { customItems: newItems };
      });
    },

    /**
     * Remove a custom symbol from the watchlist.
     * Default symbols cannot be removed.
     */
    remove(symbol: string) {
      // Cannot remove default symbols
      if (DEFAULT_SYMBOLS.includes(symbol)) {
        return;
      }

      update((state) => {
        const newItems = state.customItems.filter((item) => item.symbol !== symbol);
        saveCustomToLocalStorage(newItems);
        return { customItems: newItems };
      });
    },

    /**
     * Toggle a custom symbol in/out of the watchlist.
     * Default symbols are always in the watchlist and cannot be toggled off.
     */
    toggle(symbol: string, name?: string) {
      // Default symbols are always included, cannot toggle
      if (DEFAULT_SYMBOLS.includes(symbol)) {
        return;
      }

      update((state) => {
        const exists = state.customItems.some((item) => item.symbol === symbol);

        let newItems: WatchlistItem[];
        if (exists) {
          newItems = state.customItems.filter((item) => item.symbol !== symbol);
        } else {
          const newItem: WatchlistItem = {
            symbol,
            name,
            addedAt: new Date().toISOString(),
          };
          newItems = [...state.customItems, newItem];
        }

        saveCustomToLocalStorage(newItems);
        return { customItems: newItems };
      });
    },

    /**
     * Check if a symbol is in the watchlist (default OR custom).
     */
    has(symbol: string): boolean {
      // Default symbols are always included
      if (DEFAULT_SYMBOLS.includes(symbol)) {
        return true;
      }

      let result = false;
      const unsub = subscribe((state) => {
        result = state.customItems.some((item) => item.symbol === symbol);
      });
      unsub();
      return result;
    },

    /**
     * Check if a symbol is a default symbol.
     */
    isDefault(symbol: string): boolean {
      return DEFAULT_SYMBOLS.includes(symbol);
    },

    /**
     * Check if a symbol is a custom (user-added) symbol.
     */
    isCustom(symbol: string): boolean {
      let result = false;
      const unsub = subscribe((state) => {
        result = state.customItems.some((item) => item.symbol === symbol);
      });
      unsub();
      return result;
    },

    /**
     * Clear all custom items from the watchlist.
     * Default symbols remain.
     */
    clear() {
      saveCustomToLocalStorage([]);
      set({ customItems: [] });
    },
  };
}

export const watchlistStore = createWatchlistStore();

// Derived store for just the custom symbol list
export const customWatchlistSymbols = derived(watchlistStore, ($store) =>
  $store.customItems.map((item) => item.symbol)
);

// Derived store for ALL watchlist symbols (default + custom)
export const watchlistSymbols = derived(watchlistStore, ($store) => {
  const customSymbols = $store.customItems.map((item) => item.symbol);
  // Combine defaults + custom, avoiding duplicates
  const allSymbols = [...DEFAULT_SYMBOLS];
  for (const symbol of customSymbols) {
    if (!allSymbols.includes(symbol)) {
      allSymbols.push(symbol);
    }
  }
  return allSymbols;
});

// Derived store to check if a specific symbol is in watchlist (default OR custom)
export function isInWatchlist(symbol: string) {
  return derived(watchlistStore, ($store) => {
    if (DEFAULT_SYMBOLS.includes(symbol)) {
      return true;
    }
    return $store.customItems.some((item) => item.symbol === symbol);
  });
}

// Derived store to check if a symbol is a custom addition
export function isCustomSymbol(symbol: string) {
  return derived(watchlistStore, ($store) =>
    $store.customItems.some((item) => item.symbol === symbol)
  );
}

// Export default symbols for use in components
export { DEFAULT_SYMBOLS };
