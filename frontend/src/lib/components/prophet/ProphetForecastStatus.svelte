<script lang="ts">
  import type { ProphetHorizonSummary, ProphetHorizonToggles } from '$lib/types';

  let {
    summaries = [],
    horizonToggles,
    onToggleHorizon,
  }: {
    summaries: ProphetHorizonSummary[];
    horizonToggles: ProphetHorizonToggles;
    onToggleHorizon: (horizon: keyof ProphetHorizonToggles) => void;
  } = $props();

  // Horizon display config
  const horizonConfig = {
    long_term: { label: 'Langfristig', color: '#1f77b4', bgClass: 'bg-blue-500/20', borderClass: 'border-blue-500/40' },
    mid_term: { label: 'Mittelfristig', color: '#2ca02c', bgClass: 'bg-green-500/20', borderClass: 'border-green-500/40' },
    short_term: { label: 'Kurzfristig', color: '#d62728', bgClass: 'bg-red-500/20', borderClass: 'border-red-500/40' },
  };

  function formatPrice(value: number | null): string {
    if (value === null) return '-';
    if (value >= 1000) return value.toLocaleString('de-DE', { maximumFractionDigits: 0 });
    if (value >= 100) return value.toFixed(1);
    if (value >= 1) return value.toFixed(2);
    return value.toFixed(4);
  }

  function formatChange(current: number, forecast: number | null): { value: string; isPositive: boolean } | null {
    if (forecast === null) return null;
    const change = ((forecast - current) / current) * 100;
    return {
      value: `${change >= 0 ? '+' : ''}${change.toFixed(1)}%`,
      isPositive: change >= 0,
    };
  }
</script>

<div class="p-4 border-t border-stone-700/30">
  <h3 class="text-xs font-medium text-text-muted uppercase tracking-wide mb-3">Prognose-Horizonte</h3>

  <div class="space-y-3">
    {#each summaries as summary}
      {@const config = horizonConfig[summary.horizon as keyof typeof horizonConfig]}
      {@const isActive = horizonToggles[summary.horizon as keyof ProphetHorizonToggles]}
      {@const change30d = formatChange(summary.last_actual_value, summary.forecast_30d)}
      {@const change90d = formatChange(summary.last_actual_value, summary.forecast_90d)}

      <div class="liquid-glass-subtle rounded-xl p-3 {config.bgClass} border {config.borderClass} transition-all {isActive ? 'opacity-100' : 'opacity-50'}">
        <!-- Header with toggle -->
        <div class="flex items-center justify-between mb-2">
          <div class="flex items-center gap-2">
            <div class="w-3 h-3 rounded-full" style="background-color: {config.color}"></div>
            <span class="text-sm font-medium text-text-primary">{config.label}</span>
          </div>
          <button
            class="w-8 h-5 rounded-full transition-all relative {isActive ? 'bg-blue-500' : 'bg-stone-600'}"
            onclick={() => onToggleHorizon(summary.horizon as keyof ProphetHorizonToggles)}
          >
            <div
              class="w-4 h-4 rounded-full bg-white shadow-md absolute top-0.5 transition-all {isActive ? 'left-3.5' : 'left-0.5'}"
            ></div>
          </button>
        </div>

        <!-- Metrics -->
        <div class="grid grid-cols-2 gap-2 text-xs">
          <div>
            <div class="text-text-muted">Aktuell</div>
            <div class="font-medium text-text-primary">{formatPrice(summary.last_actual_value)}</div>
          </div>
          <div>
            <div class="text-text-muted">30 Tage</div>
            <div class="font-medium {change30d?.isPositive ? 'text-green-400' : 'text-red-400'}">
              {change30d?.value ?? '-'}
            </div>
          </div>
          <div>
            <div class="text-text-muted">90 Tage</div>
            <div class="font-medium {change90d?.isPositive ? 'text-green-400' : 'text-red-400'}">
              {change90d?.value ?? '-'}
            </div>
          </div>
          <div>
            <div class="text-text-muted">MAPE</div>
            <div class="font-medium text-text-primary">
              {summary.metrics.mape !== null ? `${summary.metrics.mape.toFixed(1)}%` : '-'}
            </div>
          </div>
        </div>
      </div>
    {/each}
  </div>

  {#if summaries.length === 0}
    <div class="text-center py-4 text-text-muted text-sm">
      Keine Prognosen verfügbar
    </div>
  {/if}
</div>
