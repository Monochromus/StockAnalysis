<script lang="ts">
  import { onMount } from 'svelte';
  import type { MonthlyReturn } from '$lib/types';
  import { watchlistStore, watchlistSymbols, DEFAULT_SYMBOLS } from '$lib/stores/watchlist';
  import { seasonalityStore, MONTH_NAMES } from '$lib/stores/seasonality';
  import { COMMODITY_WATCHLIST, CATEGORY_CONFIG, type Commodity, type CategoryKey } from '$lib/data/commodities';

  // Get commodity info from symbol
  function getCommodityInfo(symbol: string): { name: string; category: CategoryKey | null; icon: string } {
    const commodity = COMMODITY_WATCHLIST.find(c => c.symbol === symbol);
    if (commodity) {
      return {
        name: commodity.name,
        category: commodity.category,
        icon: getCategoryIcon(commodity.category),
      };
    }
    // Fallback for unknown symbols
    return { name: symbol, category: null, icon: '📈' };
  }

  function getCategoryIcon(category: CategoryKey): string {
    switch (category) {
      case 'energy': return '⛽';
      case 'agriculture': return '🌾';
      case 'metals': return '🪙';
      case 'crypto': return '₿';
      case 'other': return '📈';
      default: return '📈';
    }
  }

  function getCategoryColor(category: CategoryKey | null): string {
    if (!category) return '#a8a29e'; // stone-400
    return CATEGORY_CONFIG[category].color;
  }

  // State for loaded data
  let loadedData = $state<Map<string, MonthlyReturn[]>>(new Map());
  let loadingSymbols = $state<Set<string>>(new Set());

  // Load data for watchlist symbols
  async function loadSymbolData(symbol: string) {
    if (loadedData.has(symbol) || loadingSymbols.has(symbol)) return;

    loadingSymbols = new Set([...loadingSymbols, symbol]);

    try {
      const result = await seasonalityStore.analyzeWatchlistSymbol(symbol);
      if (result) {
        loadedData = new Map(loadedData).set(symbol, result.monthlyReturns);
      }
    } catch (e) {
      console.error(`Failed to load data for ${symbol}:`, e);
    }

    const newLoadingSymbols = new Set(loadingSymbols);
    newLoadingSymbols.delete(symbol);
    loadingSymbols = newLoadingSymbols;
  }

  // Load data for all watchlist symbols on mount and when watchlist changes
  $effect(() => {
    const symbols = $watchlistSymbols;
    for (const symbol of symbols) {
      loadSymbolData(symbol);
    }
  });

  // Get color based on return value
  function getBarColor(value: number): string {
    if (value >= 3) return 'bg-green-500';
    if (value >= 1) return 'bg-green-500/70';
    if (value > 0) return 'bg-green-500/40';
    if (value > -1) return 'bg-red-500/40';
    if (value > -3) return 'bg-red-500/70';
    return 'bg-red-500';
  }

  // Get bar width based on value (normalized)
  function getBarWidth(value: number, maxAbsValue: number): number {
    if (maxAbsValue === 0) return 0;
    return Math.min(Math.abs(value) / maxAbsValue * 100, 100);
  }

  // Calculate max absolute value across all loaded data
  const maxAbsValue = $derived(() => {
    let max = 0;
    for (const monthlyReturns of loadedData.values()) {
      for (const mr of monthlyReturns) {
        max = Math.max(max, Math.abs(mr.avg_return));
      }
    }
    return max || 5; // Default to 5% if no data
  });
</script>

<div class="space-y-4">
  <h3 class="text-sm font-medium text-stone-300 flex items-center gap-2">
    <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
    </svg>
    Watchlist Vergleich
  </h3>

  {#if $watchlistSymbols.length === 0}
    <div class="text-sm text-stone-500 italic py-4 text-center">
      Keine Symbole in der Watchlist. Klicke auf das Herz-Symbol um Assets hinzuzufuegen.
    </div>
  {:else}
    <!-- Month headers -->
    <div class="flex items-center">
      <div class="w-44 flex-shrink-0"></div>
      <div class="flex-1 flex">
        {#each MONTH_NAMES as month}
          <div class="flex-1 text-xs text-stone-500 text-center">{month}</div>
        {/each}
      </div>
    </div>

    <!-- Symbol rows -->
    {#each $watchlistSymbols as symbol}
      {@const monthlyReturns = loadedData.get(symbol)}
      {@const isLoading = loadingSymbols.has(symbol)}
      {@const commodityInfo = getCommodityInfo(symbol)}

      <div class="flex items-center gap-2">
        <!-- Commodity name with icon -->
        <div class="w-44 flex-shrink-0 flex items-center gap-2 min-w-0">
          <span class="text-base" title={commodityInfo.category || 'Sonstiges'}>{commodityInfo.icon}</span>
          <div class="flex flex-col min-w-0">
            <span class="text-sm text-stone-200 font-medium truncate" title={commodityInfo.name}>
              {commodityInfo.name.split(' (')[0]}
            </span>
            <span class="text-[10px] text-stone-500 font-mono">{symbol}</span>
          </div>
        </div>

        <!-- Monthly bars -->
        <div class="flex-1 flex gap-1">
          {#if isLoading}
            {#each Array.from({ length: 12 }) as _}
              <div class="flex-1 h-6 bg-stone-800/50 rounded animate-pulse"></div>
            {/each}
          {:else if monthlyReturns}
            {#each monthlyReturns.sort((a, b) => a.month - b.month) as mr}
              {@const barWidth = getBarWidth(mr.avg_return, maxAbsValue())}

              <div
                class="flex-1 h-6 bg-stone-800/30 rounded relative overflow-hidden group cursor-pointer"
                title="{MONTH_NAMES[mr.month - 1]}: {mr.avg_return >= 0 ? '+' : ''}{mr.avg_return.toFixed(2)}%"
              >
                <!-- Bar -->
                <div
                  class="absolute inset-y-0 transition-all duration-300 {getBarColor(mr.avg_return)}"
                  style="width: {barWidth}%; {mr.avg_return >= 0 ? 'left: 0' : 'right: 0'}"
                ></div>

                <!-- Value on hover -->
                <div class="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                  <span class="text-[10px] font-medium text-white drop-shadow-lg">
                    {mr.avg_return >= 0 ? '+' : ''}{mr.avg_return.toFixed(1)}%
                  </span>
                </div>
              </div>
            {/each}
          {:else}
            {#each Array.from({ length: 12 }) as _}
              <div class="flex-1 h-6 bg-stone-800/30 rounded"></div>
            {/each}
          {/if}
        </div>

        <!-- Remove button (only for custom symbols, not defaults) -->
        {#if !DEFAULT_SYMBOLS.includes(symbol)}
          <button
            type="button"
            class="p-1 text-stone-500 hover:text-rose-400 transition-colors"
            onclick={() => watchlistStore.remove(symbol)}
            title="Aus Watchlist entfernen"
          >
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        {:else}
          <!-- Placeholder for default symbols to maintain alignment -->
          <div class="w-6"></div>
        {/if}
      </div>
    {/each}

    <!-- Legend -->
    <div class="flex items-center justify-center gap-4 mt-4 text-xs text-stone-500">
      <div class="flex items-center gap-1">
        <div class="w-3 h-3 rounded bg-red-500"></div>
        <span>-3%+</span>
      </div>
      <div class="flex items-center gap-1">
        <div class="w-3 h-3 rounded bg-red-500/40"></div>
        <span>-1%</span>
      </div>
      <div class="flex items-center gap-1">
        <div class="w-3 h-3 rounded bg-green-500/40"></div>
        <span>+1%</span>
      </div>
      <div class="flex items-center gap-1">
        <div class="w-3 h-3 rounded bg-green-500"></div>
        <span>+3%+</span>
      </div>
    </div>
  {/if}
</div>
