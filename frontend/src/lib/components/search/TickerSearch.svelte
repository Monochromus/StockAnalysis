<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { Input, Button } from '$lib/components/ui';
  import { searchTickers } from '$lib/api/analysis';
  import { COMMODITY_WATCHLIST, CATEGORY_CONFIG, getGroupedCommodities, type Commodity, type CategoryKey } from '$lib/data/commodities';
  import type { TickerSearchResult } from '$lib/types';

  const dispatch = createEventDispatcher<{ select: string }>();

  let query = '';
  let results: TickerSearchResult[] = [];
  let loading = false;
  let showDropdown = false;
  let showWatchlist = false;
  let selectedIndex = -1;
  let debounceTimeout: ReturnType<typeof setTimeout>;

  const groupedCommodities = getGroupedCommodities();

  async function handleInput() {
    clearTimeout(debounceTimeout);
    showWatchlist = false;

    if (query.length < 1) {
      results = [];
      showDropdown = false;
      return;
    }

    debounceTimeout = setTimeout(async () => {
      loading = true;
      try {
        const response = await searchTickers(query);
        results = response.results;
        showDropdown = results.length > 0;
      } catch {
        results = [];
      } finally {
        loading = false;
      }
    }, 300);
  }

  function handleKeydown(event: KeyboardEvent) {
    if (!showDropdown) return;

    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault();
        selectedIndex = Math.min(selectedIndex + 1, results.length - 1);
        break;
      case 'ArrowUp':
        event.preventDefault();
        selectedIndex = Math.max(selectedIndex - 1, 0);
        break;
      case 'Enter':
        event.preventDefault();
        if (selectedIndex >= 0 && results[selectedIndex]) {
          selectTicker(results[selectedIndex].symbol);
        } else if (query.length > 0) {
          selectTicker(query.toUpperCase());
        }
        break;
      case 'Escape':
        showDropdown = false;
        showWatchlist = false;
        selectedIndex = -1;
        break;
    }
  }

  function selectTicker(symbol: string) {
    query = symbol;
    showDropdown = false;
    showWatchlist = false;
    selectedIndex = -1;
    dispatch('select', symbol);
  }

  function handleBlur() {
    // Delay to allow click on dropdown item
    setTimeout(() => {
      showDropdown = false;
      showWatchlist = false;
    }, 200);
  }

  function handleSubmit(event: Event) {
    event.preventDefault();
    if (query.length > 0) {
      selectTicker(query.toUpperCase());
    }
  }

  function toggleWatchlist() {
    showWatchlist = !showWatchlist;
    showDropdown = false;
  }

  function selectCommodity(commodity: Commodity) {
    selectTicker(commodity.symbol);
  }

  function getScoreBarWidth(score: number): string {
    return `${score}%`;
  }

  function getScoreColor(score: number): string {
    if (score >= 85) return 'bg-emerald-500';
    if (score >= 70) return 'bg-amber-500';
    return 'bg-stone-500';
  }
</script>

<div class="relative">
  <form onsubmit={handleSubmit} class="flex gap-2">
    <!-- Watchlist Button -->
    <button
      type="button"
      class="px-3 py-2 liquid-glass-subtle rounded-lg hover:bg-amber-500/20 transition-all flex items-center gap-1.5 {showWatchlist ? 'bg-amber-500/20 text-amber-400' : 'text-stone-400'}"
      onclick={toggleWatchlist}
      title="Rohstoff-Watchlist"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"/>
        <circle cx="12" cy="12" r="3"/>
        <line x1="12" y1="2" x2="12" y2="6"/>
        <line x1="12" y1="18" x2="12" y2="22"/>
        <line x1="2" y1="12" x2="6" y2="12"/>
        <line x1="18" y1="12" x2="22" y2="12"/>
      </svg>
    </button>

    <div class="relative flex-1">
      <Input
        type="search"
        placeholder="Search ticker (e.g., NG=F)"
        bind:value={query}
        oninput={handleInput}
        onkeydown={handleKeydown}
        onfocus={() => {
          if (results.length > 0) showDropdown = true;
        }}
        onblur={handleBlur}
      />

      {#if loading}
        <div class="absolute right-3 top-1/2 -translate-y-1/2">
          <svg class="animate-spin h-5 w-5 text-stone-500" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        </div>
      {/if}
    </div>

    <Button type="submit" variant="primary">Analyze</Button>
  </form>

  <!-- Watchlist Dropdown -->
  {#if showWatchlist}
    <div class="absolute z-50 w-full mt-2 liquid-glass-intense rounded-xl shadow-2xl overflow-hidden animate-liquid-fade-in max-h-96 overflow-y-auto">
      {#each groupedCommodities as group}
        <div class="border-b border-stone-700/30 last:border-b-0">
          <!-- Category Header -->
          <div class="px-4 py-2 bg-stone-800/50 flex items-center gap-2">
            <span
              class="w-2 h-2 rounded-full"
              style="background-color: {group.config.color}"
            ></span>
            <span class="text-xs font-semibold text-stone-400 uppercase tracking-wide">
              {group.config.label}
            </span>
          </div>

          <!-- Commodities -->
          {#each group.commodities as commodity}
            <button
              type="button"
              class="w-full px-4 py-2.5 text-left transition-all hover:bg-stone-700/50 flex items-center justify-between gap-3"
              onclick={() => selectCommodity(commodity)}
            >
              <div class="flex items-center gap-3 min-w-0">
                <span class="font-mono text-sm font-semibold text-stone-50 w-14 shrink-0">
                  {commodity.symbol.replace('=F', '')}
                </span>
                <span class="text-sm text-stone-400 truncate">
                  {commodity.name}
                </span>
              </div>
              <div class="flex items-center gap-2 shrink-0">
                <div class="w-16 h-1.5 bg-stone-700 rounded-full overflow-hidden">
                  <div
                    class="h-full rounded-full transition-all {getScoreColor(commodity.seasonalityScore)}"
                    style="width: {getScoreBarWidth(commodity.seasonalityScore)}"
                  ></div>
                </div>
                <span class="text-xs font-medium text-stone-400 w-6 text-right">
                  {commodity.seasonalityScore}
                </span>
              </div>
            </button>
          {/each}
        </div>
      {/each}
    </div>
  {/if}

  <!-- Search Results Dropdown -->
  {#if showDropdown && results.length > 0 && !showWatchlist}
    <ul class="absolute z-50 w-full mt-2 liquid-glass-intense rounded-xl shadow-2xl overflow-hidden animate-liquid-fade-in">
      {#each results as result, index}
        <li>
          <button
            type="button"
            class="w-full px-4 py-3 text-left transition-all flex items-center justify-between {index === selectedIndex ? 'bg-amber-500/15 text-amber-50' : 'hover:bg-stone-700/50'}"
            onclick={() => selectTicker(result.symbol)}
          >
            <div>
              <span class="font-semibold text-stone-50">{result.symbol}</span>
              <span class="text-stone-400 ml-2">{result.name}</span>
            </div>
            {#if result.exchange}
              <span class="text-xs text-stone-500">{result.exchange}</span>
            {/if}
          </button>
        </li>
      {/each}
    </ul>
  {/if}
</div>
