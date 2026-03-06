<script lang="ts">
  import { onMount } from 'svelte';
  import { newsStore, newsAnalysesList } from '$lib/stores/news';
  import { watchlistSymbols } from '$lib/stores/watchlist';
  import CommodityNewsCard from './CommodityNewsCard.svelte';
  import TradingOpportunitySummary from './TradingOpportunitySummary.svelte';

  // Load dashboard on mount and when watchlist changes
  let mounted = $state(false);

  onMount(() => {
    mounted = true;
    loadDashboard();
    newsStore.checkStatus();
  });

  // Reactive: reload when watchlist changes
  $effect(() => {
    if (mounted && $watchlistSymbols.length > 0) {
      loadDashboard();
    }
  });

  async function loadDashboard() {
    if ($watchlistSymbols.length > 0) {
      await newsStore.loadDashboard($watchlistSymbols);
    }
  }

  async function refreshAll() {
    if ($watchlistSymbols.length > 0) {
      await newsStore.loadDashboard($watchlistSymbols, true);
    }
  }

  function handleRefresh(symbol: string) {
    newsStore.refresh(symbol);
  }

  // Format last updated time
  function formatLastUpdated(iso: string | null): string {
    if (!iso) return '';
    try {
      const date = new Date(iso);
      return date.toLocaleTimeString('de-DE', {
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return '';
    }
  }
</script>

<div class="h-full flex flex-col overflow-hidden">
  <!-- Header -->
  <div class="flex-shrink-0 px-4 py-3 border-b border-stone-700/50 flex items-center justify-between">
    <div class="flex items-center gap-3">
      <h2 class="text-lg font-semibold text-stone-100">News Dashboard</h2>
      <span class="text-stone-500 text-sm">
        {$newsAnalysesList.length} Rohstoffe
      </span>
      {#if $newsStore.status}
        <span class="flex items-center gap-1.5 text-xs">
          <span class="w-2 h-2 rounded-full {$newsStore.status.available ? 'bg-emerald-500' : 'bg-red-500'}"></span>
          <span class="text-stone-500">Gemini {$newsStore.status.model_name}</span>
        </span>
      {/if}
    </div>
    <div class="flex items-center gap-3">
      {#if $newsStore.lastUpdated}
        <span class="text-stone-500 text-xs">
          Zuletzt: {formatLastUpdated($newsStore.lastUpdated)}
        </span>
      {/if}
      <button
        type="button"
        class="px-3 py-1.5 rounded-lg text-sm font-medium
          bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 border border-amber-500/40
          transition-colors disabled:opacity-50 disabled:cursor-not-allowed
          flex items-center gap-2"
        onclick={refreshAll}
        disabled={$newsStore.loading}
      >
        <svg
          class="w-4 h-4 {$newsStore.loading ? 'animate-spin' : ''}"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <path d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          <path d="M9 12l2 2 4-4" />
        </svg>
        Alle aktualisieren
      </button>
    </div>
  </div>

  <!-- Content -->
  <div class="flex-1 overflow-y-auto p-4">
    {#if $newsStore.error}
      <div class="mb-4 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
        {$newsStore.error}
      </div>
    {/if}

    {#if $watchlistSymbols.length === 0}
      <!-- Empty State -->
      <div class="h-full flex items-center justify-center">
        <div class="text-center max-w-md">
          <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-stone-800/50 flex items-center justify-center">
            <svg class="w-8 h-8 text-stone-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
            </svg>
          </div>
          <h3 class="text-lg font-medium text-stone-300 mb-2">
            Keine Rohstoffe in der Watchlist
          </h3>
          <p class="text-stone-500 text-sm">
            Fügen Sie Rohstoffe zu Ihrer Watchlist hinzu, um deren aktuelle
            Marktanalysen hier zu sehen.
          </p>
        </div>
      </div>
    {:else if $newsStore.loading && $newsAnalysesList.length === 0}
      <!-- Loading State -->
      <div class="h-full flex items-center justify-center">
        <div class="text-center">
          <svg class="w-12 h-12 mx-auto mb-4 text-amber-500 animate-spin" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <p class="text-stone-400">Analysiere Rohstoffe mit Gemini...</p>
          <p class="text-stone-500 text-sm mt-1">Dies kann einige Sekunden dauern.</p>
        </div>
      </div>
    {:else}
      <!-- Trading Opportunity Summary -->
      <TradingOpportunitySummary analyses={$newsAnalysesList} />

      <!-- Grid of Cards -->
      <div class="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
        {#each $newsAnalysesList as analysis (analysis.symbol)}
          <CommodityNewsCard
            {analysis}
            loading={$newsStore.loadingSymbols.has(analysis.symbol)}
            onRefresh={() => handleRefresh(analysis.symbol)}
          />
        {/each}
      </div>

      <!-- Missing symbols notice -->
      {#if $watchlistSymbols.length > $newsAnalysesList.length && !$newsStore.loading}
        <div class="mt-4 px-4 py-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400 text-sm">
          {$watchlistSymbols.length - $newsAnalysesList.length} Symbol(e) konnten nicht analysiert werden.
        </div>
      {/if}
    {/if}
  </div>

  <!-- Footer with disclaimer -->
  <div class="flex-shrink-0 px-4 py-2 border-t border-stone-700/50 bg-stone-900/50">
    <p class="text-stone-600 text-xs text-center">
      Analysen werden von Google Gemini mit Search Grounding erstellt.
      Keine Anlageberatung - immer eigene Recherche durchführen.
    </p>
  </div>
</div>
