<script lang="ts">
  import { onMount } from 'svelte';
  import { seasonalityStore, sortedMonthlyReturns, bestMonth, worstMonth, MONTH_NAMES_FULL } from '$lib/stores/seasonality';
  import HeatmapGrid from './HeatmapGrid.svelte';
  import YearCalendar from './YearCalendar.svelte';
  import WatchlistComparison from './WatchlistComparison.svelte';

  interface Props {
    symbol: string;
  }

  let { symbol }: Props = $props();

  type CalendarViewMode = 'heatmap' | 'calendar';
  let calendarViewMode = $state<CalendarViewMode>('heatmap');

  // Load seasonality data when symbol changes
  $effect(() => {
    if (symbol) {
      seasonalityStore.analyze(symbol);
    }
  });
</script>

<div class="h-full overflow-y-auto p-6 space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <h2 class="text-xl font-semibold text-stone-100">
        Saisonalitaets-Kalender
        {#if symbol}
          <span class="text-amber-500">({symbol})</span>
        {/if}
      </h2>
      <p class="text-sm text-stone-400 mt-1">
        Historische Saisonalitaetsmuster basierend auf 5 Jahren Daten
      </p>
    </div>

    <!-- View mode toggle -->
    <div class="flex items-center gap-1 bg-stone-800/50 rounded-lg p-1">
      <button
        type="button"
        class="px-3 py-1.5 rounded-md text-sm font-medium transition-all duration-200
          {calendarViewMode === 'heatmap'
            ? 'bg-amber-500/20 text-amber-400'
            : 'text-stone-400 hover:text-stone-300 hover:bg-stone-700/50'}"
        onclick={() => (calendarViewMode = 'heatmap')}
      >
        Heatmap
      </button>
      <button
        type="button"
        class="px-3 py-1.5 rounded-md text-sm font-medium transition-all duration-200
          {calendarViewMode === 'calendar'
            ? 'bg-amber-500/20 text-amber-400'
            : 'text-stone-400 hover:text-stone-300 hover:bg-stone-700/50'}"
        onclick={() => (calendarViewMode = 'calendar')}
      >
        Kalender
      </button>
    </div>
  </div>

  {#if $seasonalityStore.loading}
    <!-- Loading state -->
    <div class="flex items-center justify-center py-20">
      <div class="flex items-center gap-3">
        <svg class="animate-spin h-8 w-8 text-amber-500" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
        <span class="text-stone-400">Analysiere Saisonalitaet...</span>
      </div>
    </div>
  {:else if $seasonalityStore.error}
    <!-- Error state -->
    <div class="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
      <p class="text-red-400">{$seasonalityStore.error}</p>
    </div>
  {:else if !symbol}
    <!-- No symbol selected -->
    <div class="flex items-center justify-center py-20">
      <p class="text-stone-500 text-lg">Waehle ein Symbol um die Saisonalitaet zu analysieren</p>
    </div>
  {:else}
    <!-- Monthly Returns Summary -->
    <div class="bg-stone-800/30 rounded-xl p-4">
      <h3 class="text-sm font-medium text-stone-300 mb-3">Monatliche Performance (5 Jahre)</h3>

      <div class="grid grid-cols-12 gap-2">
        {#each $sortedMonthlyReturns as mr}
          {@const isPositive = mr.avg_return > 0}

          <div
            class="flex flex-col items-center p-2 rounded-lg {isPositive ? 'bg-green-500/10' : 'bg-red-500/10'}"
            title="{MONTH_NAMES_FULL[mr.month - 1]}: Avg {mr.avg_return >= 0 ? '+' : ''}{mr.avg_return.toFixed(2)}%, Win Rate {mr.positive_pct.toFixed(0)}%"
          >
            <span class="text-xs text-stone-400">{MONTH_NAMES_FULL[mr.month - 1].slice(0, 3)}</span>
            <span class="text-sm font-semibold {isPositive ? 'text-green-400' : 'text-red-400'}">
              {isPositive ? '+' : ''}{mr.avg_return.toFixed(1)}%
            </span>
            <span class="text-[10px] text-stone-500">{mr.positive_pct.toFixed(0)}% Win</span>
          </div>
        {/each}
      </div>

      <!-- Best/Worst months -->
      {#if $bestMonth && $worstMonth}
        <div class="flex items-center justify-center gap-8 mt-4 text-sm">
          <div class="flex items-center gap-2">
            <span class="text-stone-400">Bester Monat:</span>
            <span class="text-green-400 font-medium">
              {MONTH_NAMES_FULL[$bestMonth.month - 1]} (+{$bestMonth.avg_return.toFixed(2)}%)
            </span>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-stone-400">Schlechtester Monat:</span>
            <span class="text-red-400 font-medium">
              {MONTH_NAMES_FULL[$worstMonth.month - 1]} ({$worstMonth.avg_return.toFixed(2)}%)
            </span>
          </div>
        </div>
      {/if}
    </div>

    <!-- Daily Seasonality Visualization -->
    <div class="bg-stone-800/30 rounded-xl p-4">
      <h3 class="text-sm font-medium text-stone-300 mb-3">
        Taegliche Saisonalitaet (Durchschnittliche Tagesrendite)
      </h3>

      {#if calendarViewMode === 'heatmap'}
        <HeatmapGrid dailySeasonality={$seasonalityStore.dailySeasonality} />
      {:else}
        <YearCalendar dailySeasonality={$seasonalityStore.dailySeasonality} />
      {/if}
    </div>

    <!-- Watchlist Comparison -->
    <div class="bg-stone-800/30 rounded-xl p-4">
      <WatchlistComparison />
    </div>
  {/if}
</div>
