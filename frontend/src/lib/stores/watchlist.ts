/**
 * Watchlist Store with LocalStorage persistence.
 */

import { writable, derived } from 'svelte/store';
import type { WatchlistItem } from '$lib/types';

const STORAGE_KEY = 'commodity-cockpit-watchlist';

interface WatchlistState {
  items: WatchlistItem[];
}

function loadFromLocalStorage(): WatchlistItem[] {
  if (typeof window === 'undefined') return [];

  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch (e) {
    console.warn('Failed to load watchlist from localStorage:', e);
  }
  return [];
}

function saveToLocalStorage(items: WatchlistItem[]): void {
  if (typeof window === 'undefined') return;

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  } catch (e) {
    console.warn('Failed to save watchlist to localStorage:', e);
  }
}

const initialState: WatchlistState = {
  items: [],
};

function createWatchlistStore() {
  const { subscribe, set, update } = writable<WatchlistState>(initialState);

  // Load from localStorage on initialization (only in browser)
  if (typeof window !== 'undefined') {
    const items = loadFromLocalStorage();
    set({ items });
  }

  return {
    subscribe,

    /**
     * Initialize store (call on mount in browser).
     */
    init() {
      const items = loadFromLocalStorage();
      set({ items });
    },

    /**
     * Add a symbol to the watchlist.
     */
    add(symbol: string, name?: string) {
      update((state) => {
        // Check if already exists
        if (state.items.some((item) => item.symbol === symbol)) {
          return state;
        }

        const newItem: WatchlistItem = {
          symbol,
          name,
          addedAt: new Date().toISOString(),
        };

        const newItems = [...state.items, newItem];
        saveToLocalStorage(newItems);

        return { items: newItems };
      });
    },

    /**
     * Remove a symbol from the watchlist.
     */
    remove(symbol: string) {
      update((state) => {
        const newItems = state.items.filter((item) => item.symbol !== symbol);
        saveToLocalStorage(newItems);
        return { items: newItems };
      });
    },

    /**
     * Toggle a symbol in/out of the watchlist.
     */
    toggle(symbol: string, name?: string) {
      update((state) => {
        const exists = state.items.some((item) => item.symbol === symbol);

        let newItems: WatchlistItem[];
        if (exists) {
          newItems = state.items.filter((item) => item.symbol !== symbol);
        } else {
          const newItem: WatchlistItem = {
            symbol,
            name,
            addedAt: new Date().toISOString(),
          };
          newItems = [...state.items, newItem];
        }

        saveToLocalStorage(newItems);
        return { items: newItems };
      });
    },

    /**
     * Check if a symbol is in the watchlist.
     */
    has(symbol: string): boolean {
      let result = false;
      const unsub = subscribe((state) => {
        result = state.items.some((item) => item.symbol === symbol);
      });
      unsub();
      return result;
    },

    /**
     * Clear all items from the watchlist.
     */
    clear() {
      saveToLocalStorage([]);
      set({ items: [] });
    },
  };
}

export const watchlistStore = createWatchlistStore();

// Derived store for just the symbol list
export const watchlistSymbols = derived(watchlistStore, ($store) =>
  $store.items.map((item) => item.symbol)
);

// Derived store to check if a specific symbol is in watchlist
export function isInWatchlist(symbol: string) {
  return derived(watchlistStore, ($store) =>
    $store.items.some((item) => item.symbol === symbol)
  );
}
