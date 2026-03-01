import { writable, get } from 'svelte/store';

export interface DebugLogEntry {
  timestamp: string;
  source: string;
  message: string;
  data?: any;
}

interface DebugState {
  isOpen: boolean;
  logs: DebugLogEntry[];
  maxLogs: number;
}

const initialState: DebugState = {
  isOpen: false,
  logs: [],
  maxLogs: 200,
};

function createDebugStore() {
  const { subscribe, set, update } = writable<DebugState>(initialState);

  return {
    subscribe,

    toggle() {
      update((state) => ({ ...state, isOpen: !state.isOpen }));
    },

    open() {
      update((state) => ({ ...state, isOpen: true }));
    },

    close() {
      update((state) => ({ ...state, isOpen: false }));
    },

    addLog(entry: DebugLogEntry) {
      update((state) => {
        const newLogs = [...state.logs, entry];
        // Keep only the last maxLogs entries
        if (newLogs.length > state.maxLogs) {
          newLogs.shift();
        }
        return { ...state, logs: newLogs };
      });
    },

    clear() {
      update((state) => ({ ...state, logs: [] }));
    },

    // Helper to get current state synchronously
    getLogs(): DebugLogEntry[] {
      return get({ subscribe }).logs;
    },
  };
}

export const debugStore = createDebugStore();

// Global debug helper
if (typeof window !== 'undefined') {
  (window as any).debugStore = debugStore;
  (window as any).debugLog = (message: string, data?: any) => {
    debugStore.addLog({
      timestamp: new Date().toISOString(),
      source: 'Console',
      message,
      data,
    });
    if ((import.meta as any).env?.DEV) {
      console.log(`[Debug] ${message}`, data ?? '');
    }
  };
}
