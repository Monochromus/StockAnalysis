import { writable } from 'svelte/store';

interface SubplotHeights {
  rsi: number;
  macd: number;
  adx: number;
  volume: number;
  atr: number;
}

const defaultHeights: SubplotHeights = {
  rsi: 80,
  macd: 80,
  adx: 80,
  volume: 60,
  atr: 60,
};

const MIN_HEIGHT = 40;
const MAX_HEIGHT = 200;

function createSubplotHeightsStore() {
  const { subscribe, update, set } = writable<SubplotHeights>(defaultHeights);

  return {
    subscribe,

    setHeight: (type: keyof SubplotHeights, height: number) => {
      const clampedHeight = Math.max(MIN_HEIGHT, Math.min(MAX_HEIGHT, height));
      update((heights) => ({ ...heights, [type]: clampedHeight }));
    },

    resetToDefaults: () => set(defaultHeights),

    getMinHeight: () => MIN_HEIGHT,
    getMaxHeight: () => MAX_HEIGHT,
  };
}

export const subplotHeightsStore = createSubplotHeightsStore();
