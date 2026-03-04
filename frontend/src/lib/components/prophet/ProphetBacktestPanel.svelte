<script lang="ts">
  import type { ProphetBacktestResponse, ProphetBacktestMetrics } from '$lib/types';

  let {
    enabled = false,
    loading = false,
    result = null,
    cutoffDate = null,
    error = null,
    symbol = null,
    onToggle,
    onRunBacktest,
    onSetCutoffDate,
    onClearBacktest,
  }: {
    enabled?: boolean;
    loading?: boolean;
    result?: ProphetBacktestResponse | null;
    cutoffDate?: string | null;
    error?: string | null;
    symbol?: string | null;
    onToggle: () => void;
    onRunBacktest: (cutoffDate: string) => void;
    onSetCutoffDate: (date: string | null) => void;
    onClearBacktest: () => void;
  } = $props();

  // Default cutoff date to 6 months ago
  let selectedDate = $state(cutoffDate || getDefaultCutoffDate());

  function getDefaultCutoffDate(): string {
    const date = new Date();
    date.setMonth(date.getMonth() - 6);
    return date.toISOString().split('T')[0];
  }

  function handleRunBacktest() {
    if (selectedDate && symbol) {
      onRunBacktest(selectedDate);
    }
  }

  function formatMetricValue(value: number, suffix: string = ''): string {
    if (value === undefined || value === null) return '-';
    return `${value.toFixed(2)}${suffix}`;
  }

  function getCorrelationColor(corr: number): string {
    if (corr >= 0.7) return 'text-emerald-400';
    if (corr >= 0.4) return 'text-yellow-400';
    return 'text-red-400';
  }

  function getMAPEColor(mape: number): string {
    if (mape <= 10) return 'text-emerald-400';
    if (mape <= 20) return 'text-yellow-400';
    return 'text-red-400';
  }

  function getDirectionColor(acc: number): string {
    if (acc >= 60) return 'text-emerald-400';
    if (acc >= 50) return 'text-yellow-400';
    return 'text-red-400';
  }
</script>

<div class="px-3 pb-3">
  <div class="space-y-3">
    <!-- Date Picker -->
    <div>
      <label class="block text-xs text-text-muted mb-1">Cutoff-Datum</label>
      <div class="flex gap-2">
        <input
          type="date"
          bind:value={selectedDate}
          max={new Date().toISOString().split('T')[0]}
          class="flex-1 px-2 py-1.5 text-sm liquid-glass-subtle border border-stone-700/30 rounded-lg bg-stone-900/50 text-text-primary focus:outline-none focus:border-purple-500/50"
          disabled={loading}
        />
        <button
          class="px-3 py-1.5 text-xs liquid-glass-subtle bg-purple-600/80 text-white rounded-lg hover:bg-purple-500/80 transition-all disabled:opacity-50"
          onclick={handleRunBacktest}
          disabled={loading || !symbol || !selectedDate}
        >
          {loading ? 'Teste...' : 'Backtest'}
        </button>
      </div>
      <p class="mt-1 text-[10px] text-text-muted">
        Prophet trainiert nur auf Daten VOR diesem Datum
      </p>
    </div>

    <!-- Error -->
    {#if error}
      <div class="p-2 liquid-glass-subtle border border-red-500/30 rounded-lg bg-red-900/20">
        <p class="text-xs text-red-400">{error}</p>
      </div>
    {/if}

    <!-- Results -->
    {#if result}
      <div class="space-y-2">
        <!-- Header -->
        <div class="flex items-center justify-between">
          <span class="text-xs font-medium text-text-primary">Backtest-Ergebnis</span>
          <button
            class="text-[10px] text-text-muted hover:text-red-400 transition-colors"
            onclick={onClearBacktest}
          >
            Löschen
          </button>
        </div>

        <!-- Metrics Grid -->
        <div class="grid grid-cols-2 gap-2">
          <!-- Correlation -->
          <div class="p-2 liquid-glass-subtle rounded-lg">
            <div class="text-[10px] text-text-muted uppercase tracking-wide">Korrelation</div>
            <div class="text-lg font-semibold {getCorrelationColor(result.metrics.correlation)}">
              {formatMetricValue(result.metrics.correlation)}
            </div>
            <div class="text-[10px] text-text-muted">(-1 bis 1)</div>
          </div>

          <!-- R-Squared -->
          <div class="p-2 liquid-glass-subtle rounded-lg">
            <div class="text-[10px] text-text-muted uppercase tracking-wide">R²</div>
            <div class="text-lg font-semibold {getCorrelationColor(result.metrics.r_squared)}">
              {formatMetricValue(result.metrics.r_squared)}
            </div>
            <div class="text-[10px] text-text-muted">Bestimmtheitsmaß</div>
          </div>

          <!-- MAPE -->
          <div class="p-2 liquid-glass-subtle rounded-lg">
            <div class="text-[10px] text-text-muted uppercase tracking-wide">MAPE</div>
            <div class="text-lg font-semibold {getMAPEColor(result.metrics.mape)}">
              {formatMetricValue(result.metrics.mape, '%')}
            </div>
            <div class="text-[10px] text-text-muted">Mittl. Fehler %</div>
          </div>

          <!-- Direction Accuracy -->
          <div class="p-2 liquid-glass-subtle rounded-lg">
            <div class="text-[10px] text-text-muted uppercase tracking-wide">Richtung</div>
            <div class="text-lg font-semibold {getDirectionColor(result.metrics.direction_accuracy)}">
              {formatMetricValue(result.metrics.direction_accuracy, '%')}
            </div>
            <div class="text-[10px] text-text-muted">korrekte Richtung</div>
          </div>
        </div>

        <!-- Additional Metrics -->
        <div class="grid grid-cols-3 gap-2 text-center">
          <div class="p-1.5 liquid-glass-subtle rounded-lg">
            <div class="text-[10px] text-text-muted">RMSE</div>
            <div class="text-xs font-medium text-text-primary">
              ${formatMetricValue(result.metrics.rmse)}
            </div>
          </div>
          <div class="p-1.5 liquid-glass-subtle rounded-lg">
            <div class="text-[10px] text-text-muted">MAE</div>
            <div class="text-xs font-medium text-text-primary">
              ${formatMetricValue(result.metrics.mae)}
            </div>
          </div>
          <div class="p-1.5 liquid-glass-subtle rounded-lg">
            <div class="text-[10px] text-text-muted">Tage verglichen</div>
            <div class="text-xs font-medium text-text-primary">
              {result.metrics.days_with_actual}
            </div>
          </div>
        </div>

        <!-- Date Info -->
        <div class="text-[10px] text-text-muted space-y-0.5">
          <div class="flex justify-between">
            <span>Training endet:</span>
            <span class="text-purple-400">{result.cutoff_date}</span>
          </div>
          <div class="flex justify-between">
            <span>Prognose bis:</span>
            <span>{result.forecast_end_date}</span>
          </div>
          <div class="flex justify-between">
            <span>Vergleich mit Ist bis:</span>
            <span class="text-green-400">{result.today_date}</span>
          </div>
        </div>
      </div>
    {:else if !loading}
      <div class="text-center py-2">
        <p class="text-xs text-text-muted">
          Wählen Sie ein Datum und starten Sie den Backtest, um die Prognosequalität zu validieren.
        </p>
      </div>
    {/if}

    <!-- Loading State -->
    {#if loading}
      <div class="flex items-center justify-center py-4">
        <div class="text-center">
          <div class="animate-spin w-6 h-6 border-2 border-purple-500 border-t-transparent rounded-full mx-auto mb-2"></div>
          <p class="text-xs text-text-muted">Prophet Backtest...</p>
        </div>
      </div>
    {/if}
  </div>
</div>
