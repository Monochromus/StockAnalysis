import { writable, derived } from 'svelte/store';
import type { AnalysisResponse, AnalysisRequest, Wave, Pivot, RiskReward, HigherDegreeAnalysis, ProjectedZone, FibonacciLevel, ElliottWaveMode, ManualWaveRequest } from '$lib/types';
import { analyzeWaves, fetchPivots as fetchPivotsApi, analyzeManualWaves } from '$lib/api/analysis';
import { debugStore } from './debug';
import { getCountColor } from '$lib/components/chart/primitives/utils/colors';

interface AnalysisState {
  result: AnalysisResponse | null;
  loading: boolean;
  error: string | null;
  settings: {
    period: string;
    interval: string;
    zigzagThreshold: number;
  };
  selectedStartPivot: Pivot | null;
  currentSymbol: string | null;
  pivotsLoaded: boolean;
  pivotsOnly: Pivot[];
  /** null = primary count, 0/1/2 = alternative count index */
  selectedCountIndex: number | null;
  /** Elliott Wave mode: 'auto' for automatic detection, 'manual' for user-defined waves */
  mode: ElliottWaveMode;
  /** Pivot indices selected by user in manual mode */
  manualPivotIndices: number[];
}

const initialState: AnalysisState = {
  result: null,
  loading: false,
  error: null,
  settings: {
    period: '1y',
    interval: '1d',
    zigzagThreshold: 5.0,
  },
  selectedStartPivot: null,
  currentSymbol: null,
  pivotsLoaded: false,
  pivotsOnly: [],
  selectedCountIndex: null,
  mode: 'auto',
  manualPivotIndices: [],
};

function log(message: string, data?: any) {
  if (typeof import.meta !== 'undefined' && !import.meta.env?.DEV) return;
  const entry = { timestamp: new Date().toISOString(), source: 'AnalysisStore', message, data };
  console.log(`[AnalysisStore] ${message}`, data ?? '');
  debugStore.addLog(entry);
}

function createAnalysisStore() {
  const { subscribe, set, update } = writable<AnalysisState>(initialState);

  return {
    subscribe,

    async fetchPivots(symbol: string) {
      log('fetchPivots called', { symbol });
      update((state) => ({
        ...state,
        loading: true,
        error: null,
        currentSymbol: symbol,
        result: null,
        selectedStartPivot: null,
        pivotsLoaded: false,
        pivotsOnly: [],
      }));

      try {
        let settings: AnalysisState['settings'];
        const unsubscribe = subscribe((state) => {
          settings = state.settings;
        });
        unsubscribe();

        const request: AnalysisRequest = {
          symbol,
          period: settings!.period,
          interval: settings!.interval,
          zigzag_threshold: settings!.zigzagThreshold,
        };

        log('Sending pivot request', request);
        const response = await fetchPivotsApi(request);
        log('Pivot response received', {
          pivotCount: response.pivots?.length ?? 0,
          warning: response.warning,
        });

        update((state) => ({
          ...state,
          pivotsOnly: response.pivots ?? [],
          pivotsLoaded: true,
          loading: false,
          error: response.warning || null,
        }));

        return response;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to fetch pivots';
        log('ERROR in fetchPivots', { error: errorMessage });
        update((state) => ({
          ...state,
          loading: false,
          error: errorMessage,
        }));
        return null;
      }
    },

    async analyze(symbol: string, startPivotIndex?: number) {
      log('analyze called', { symbol, startPivotIndex });
      update((state) => ({ ...state, loading: true, error: null, currentSymbol: symbol, selectedCountIndex: null }));

      try {
        let settings: AnalysisState['settings'];
        const unsubscribe = subscribe((state) => {
          settings = state.settings;
        });
        unsubscribe();

        const request: AnalysisRequest = {
          symbol,
          period: settings!.period,
          interval: settings!.interval,
          zigzag_threshold: settings!.zigzagThreshold,
          start_pivot_index: startPivotIndex,
        };

        log('Sending analysis request', request);
        const response = await analyzeWaves(request);
        log('Analysis response received', {
          symbol: response.symbol,
          hasPrimaryCount: !!response.primary_count,
          waveCount: response.primary_count?.waves?.length ?? 0,
          alternativeCountsCount: response.alternative_counts?.length ?? 0,
          pivotCount: response.pivots?.length ?? 0,
          hasHigherDegree: !!response.higher_degree,
          warning: response.warning
        });

        update((state) => ({
          ...state,
          result: response,
          loading: false,
          error: response.warning || null,
        }));

        log('Store updated with analysis result');
        return response;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Analysis failed';
        log('ERROR in analysis', { error: errorMessage });
        update((state) => ({
          ...state,
          loading: false,
          error: errorMessage,
        }));
        return null;
      }
    },

    updateSettings(settings: Partial<AnalysisState['settings']>) {
      update((state) => ({
        ...state,
        settings: { ...state.settings, ...settings },
      }));
    },

    async selectStartPivot(pivot: Pivot) {
      log('Start pivot selected', { pivot });

      let currentSymbol: string | null = null;
      const unsubscribe = subscribe((state) => {
        currentSymbol = state.currentSymbol;
      });
      unsubscribe();

      if (!currentSymbol) {
        log('No symbol selected, cannot analyze from pivot');
        return null;
      }

      update((state) => ({
        ...state,
        selectedStartPivot: pivot,
      }));

      // Trigger new analysis from this pivot
      return this.analyze(currentSymbol, pivot.index);
    },

    /**
     * Select which count to display on chart.
     * null = primary count, 0/1/2 = alternative count index.
     */
    selectCount(index: number | null) {
      log('Count selected', { index });
      update((state) => ({
        ...state,
        selectedCountIndex: index,
      }));
    },

    clearAnalysis() {
      log('Analysis cleared');
      update((state) => ({
        ...state,
        result: null,
        selectedStartPivot: null,
        selectedCountIndex: null,
      }));
    },

    clear() {
      set(initialState);
    },

    /** Set the Elliott Wave analysis mode */
    setMode(mode: ElliottWaveMode) {
      log('Mode changed', { mode });
      update((state) => ({
        ...state,
        mode,
        // Clear manual pivots when switching modes
        manualPivotIndices: [],
        // Clear analysis result when switching to manual
        result: mode === 'manual' ? null : state.result,
        selectedStartPivot: null,
        selectedCountIndex: null,
      }));
    },

    /** Add a pivot to the manual wave selection */
    addManualPivot(pivot: Pivot) {
      log('Manual pivot added', { pivot });
      update((state) => ({
        ...state,
        manualPivotIndices: [...state.manualPivotIndices, pivot.index],
      }));
    },

    /** Remove the last manual pivot */
    removeLastManualPivot() {
      log('Last manual pivot removed');
      update((state) => ({
        ...state,
        manualPivotIndices: state.manualPivotIndices.slice(0, -1),
      }));
    },

    /** Clear all manual pivots */
    clearManualPivots() {
      log('Manual pivots cleared');
      update((state) => ({
        ...state,
        manualPivotIndices: [],
        result: null,
      }));
    },

    /** Analyze waves from manually selected pivots */
    async analyzeManual() {
      log('Manual analysis started');

      let currentSymbol: string | null = null;
      let settings: AnalysisState['settings'];
      let pivotIndices: number[];

      const unsubscribe = subscribe((state) => {
        currentSymbol = state.currentSymbol;
        settings = state.settings;
        pivotIndices = state.manualPivotIndices;
      });
      unsubscribe();

      if (!currentSymbol || pivotIndices!.length < 2) {
        log('Cannot analyze: insufficient data', { currentSymbol, pivotCount: pivotIndices!.length });
        return null;
      }

      update((state) => ({ ...state, loading: true, error: null, selectedCountIndex: null }));

      try {
        const request: ManualWaveRequest = {
          symbol: currentSymbol,
          period: settings!.period,
          interval: settings!.interval,
          pivot_indices: pivotIndices!,
          zigzag_threshold: settings!.zigzagThreshold,
        };

        log('Sending manual analysis request', request);
        const response = await analyzeManualWaves(request);
        log('Manual analysis response received', {
          symbol: response.symbol,
          hasPrimaryCount: !!response.primary_count,
          waveCount: response.primary_count?.waves?.length ?? 0,
          warning: response.warning,
        });

        update((state) => ({
          ...state,
          result: response,
          loading: false,
          error: response.warning || null,
        }));

        return response;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Manual analysis failed';
        log('ERROR in manual analysis', { error: errorMessage });
        update((state) => ({
          ...state,
          loading: false,
          error: errorMessage,
        }));
        return null;
      }
    },
  };
}

export const analysisStore = createAnalysisStore();

// Derived store for the actively selected wave count
export const activeWaveCount = derived(analysisStore, ($analysis) => {
  if (!$analysis.result) return null;
  if ($analysis.selectedCountIndex === null) {
    return $analysis.result.primary_count;
  }
  return $analysis.result.alternative_counts[$analysis.selectedCountIndex] ?? $analysis.result.primary_count;
});

// Derived store for wave overlay data - shows selected count
export const waveOverlayData = derived(analysisStore, ($analysis) => {
  // Use pivotsOnly when no analysis result, otherwise use result pivots
  const pivots: Pivot[] = $analysis.result?.pivots ?? $analysis.pivotsOnly;
  const riskReward: RiskReward | null = $analysis.result?.risk_reward ?? null;

  if (!$analysis.result) {
    return { waves: [], pivots, riskReward: null, higherDegree: null, projectedZones: [], fibonacciLevels: [] };
  }

  // Determine which count to display
  let activeCount = $analysis.result.primary_count;
  if ($analysis.selectedCountIndex !== null) {
    activeCount = $analysis.result.alternative_counts[$analysis.selectedCountIndex] ?? activeCount;
  }

  // Use zones/levels from the active count, fall back to top-level
  const projectedZones: ProjectedZone[] = activeCount?.projected_zones ?? $analysis.result.projected_zones ?? [];
  const fibonacciLevels: FibonacciLevel[] = activeCount?.fibonacci_levels ?? $analysis.result.fibonacci_levels ?? [];

  // Build higherDegree (I) line from active count's waves
  let higherDegree: HigherDegreeAnalysis | null = null;
  if (activeCount?.is_complete && activeCount.waves.length >= 5) {
    const w1 = activeCount.waves.find(w => w.label === '1');
    const w5 = activeCount.waves.find(w => w.label === '5');
    if (w1 && w5) {
      higherDegree = {
        completed_wave: {
          label: '(I)' as const,
          start_timestamp: w1.start_timestamp,
          end_timestamp: w5.end_timestamp,
          start_price: w1.start_price,
          end_price: w5.end_price,
          start_index: w1.start_index,
          end_index: w5.end_index,
        },
        projected_zones: [],
        direction: w1.end_price > w1.start_price ? 'up' : 'down',
      };
    }
  }

  const waves: Array<Wave & { color: string }> = [];

  if (activeCount) {
    for (const wave of activeCount.waves) {
      waves.push({
        ...wave,
        color: getCountColor(0, wave.type),
      });
    }
  }

  return { waves, pivots, riskReward, higherDegree, projectedZones, fibonacciLevels };
});

// Derived store for validation summary (follows selected count)
export const validationSummary = derived([analysisStore, activeWaveCount], ([$analysis, $activeCount]) => {
  if (!$activeCount) {
    return { passed: 0, total: 0, results: [] };
  }

  const results = $activeCount.validation_results;
  const passed = results.filter((r) => r.passed).length;

  return {
    passed,
    total: results.length,
    results,
  };
});

// Derived store for Fibonacci summary (follows selected count)
export const fibonacciSummary = derived([analysisStore, activeWaveCount], ([$analysis, $activeCount]) => {
  if (!$activeCount) {
    return { averageScore: 0, scores: [] };
  }

  const scores = $activeCount.fibonacci_scores;
  const averageScore =
    scores.length > 0 ? scores.reduce((sum, s) => sum + s.score, 0) / scores.length : 0;

  return {
    averageScore: Math.round(averageScore),
    scores,
  };
});

// Derived store for manual mode state
export const manualModeState = derived(analysisStore, ($analysis) => {
  return {
    mode: $analysis.mode,
    pivotIndices: $analysis.manualPivotIndices,
    pivotCount: $analysis.manualPivotIndices.length,
    canAnalyze: $analysis.manualPivotIndices.length >= 2,
    // Get the next wave label based on selected pivots
    nextWaveLabel: getNextWaveLabel($analysis.manualPivotIndices.length),
  };
});

// Helper to determine the next wave label
function getNextWaveLabel(pivotCount: number): string {
  const labels = ['Start (W1)', 'W1 Ende', 'W2 Ende', 'W3 Ende', 'W4 Ende', 'W5 Ende'];
  if (pivotCount >= labels.length) return 'Komplett';
  return labels[pivotCount];
}
