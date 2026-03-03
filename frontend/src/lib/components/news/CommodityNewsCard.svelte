<script lang="ts">
  import type { CommodityNewsAnalysis } from '$lib/types';
  import MarketSentiment from './MarketSentiment.svelte';
  import UpcomingEvents from './UpcomingEvents.svelte';
  import NewsSourceList from './NewsSourceList.svelte';

  interface Props {
    analysis: CommodityNewsAnalysis;
    loading?: boolean;
    onRefresh?: () => void;
  }

  let { analysis, loading = false, onRefresh }: Props = $props();

  // Collapsible sections
  let showNews = $state(true);
  let showSupplyDemand = $state(false);
  let showMacro = $state(false);
  let showEvents = $state(true);
  let showSources = $state(false);

  // Format timestamp
  function formatTimestamp(iso: string): string {
    try {
      const date = new Date(iso);
      return date.toLocaleString('de-DE', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return iso;
    }
  }
</script>

<div class="liquid-glass rounded-xl overflow-hidden">
  <!-- Header -->
  <div class="px-4 py-3 border-b border-stone-700/50 flex items-center justify-between">
    <div class="flex items-center gap-3">
      <h3 class="text-lg font-semibold text-stone-100">
        {analysis.commodity_name}
      </h3>
      <span class="text-stone-500 text-sm font-mono">
        {analysis.symbol}
      </span>
    </div>
    <div class="flex items-center gap-3">
      <MarketSentiment
        sentiment={analysis.market_assessment.sentiment}
        confidence={analysis.market_assessment.confidence}
        size="sm"
      />
      {#if onRefresh}
        <button
          type="button"
          class="p-1.5 rounded-lg text-stone-400 hover:text-stone-200 hover:bg-stone-700/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          onclick={onRefresh}
          disabled={loading}
          title="Aktualisieren"
        >
          <svg
            class="w-4 h-4 {loading ? 'animate-spin' : ''}"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <path d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            <path d="M9 12l2 2 4-4" />
          </svg>
        </button>
      {/if}
    </div>
  </div>

  <!-- Content -->
  <div class="p-4 space-y-4">
    <!-- Market Assessment -->
    <div>
      <p class="text-stone-300 text-sm leading-relaxed">
        {analysis.market_assessment.summary}
      </p>
      {#if analysis.market_assessment.key_factors.length > 0}
        <div class="flex flex-wrap gap-1.5 mt-2">
          {#each analysis.market_assessment.key_factors as factor}
            <span class="text-xs bg-stone-700/50 text-stone-400 px-2 py-0.5 rounded">
              {factor}
            </span>
          {/each}
        </div>
      {/if}
    </div>

    <!-- News Section -->
    <div class="border-t border-stone-700/50 pt-3">
      <button
        type="button"
        class="w-full flex items-center justify-between text-left"
        onclick={() => showNews = !showNews}
      >
        <span class="text-sm font-medium text-stone-200">Aktuelle Nachrichten</span>
        <svg
          class="w-4 h-4 text-stone-500 transition-transform {showNews ? 'rotate-180' : ''}"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <path d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {#if showNews}
        <div class="mt-2 space-y-2">
          <p class="text-stone-400 text-sm">{analysis.news_summary}</p>
          {#if analysis.news_highlights.length > 0}
            <ul class="space-y-1">
              {#each analysis.news_highlights as highlight}
                <li class="text-stone-400 text-sm pl-3 border-l-2 border-amber-500/30">
                  {highlight}
                </li>
              {/each}
            </ul>
          {/if}
        </div>
      {/if}
    </div>

    <!-- Supply & Demand Section -->
    {#if analysis.supply_demand}
      <div class="border-t border-stone-700/50 pt-3">
        <button
          type="button"
          class="w-full flex items-center justify-between text-left"
          onclick={() => showSupplyDemand = !showSupplyDemand}
        >
          <span class="text-sm font-medium text-stone-200">Angebot & Nachfrage</span>
          <svg
            class="w-4 h-4 text-stone-500 transition-transform {showSupplyDemand ? 'rotate-180' : ''}"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <path d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        {#if showSupplyDemand}
          <div class="mt-2 space-y-2 text-sm">
            <div>
              <span class="text-emerald-400 font-medium">Angebot:</span>
              <span class="text-stone-400 ml-1">{analysis.supply_demand.supply_summary}</span>
            </div>
            <div>
              <span class="text-amber-400 font-medium">Nachfrage:</span>
              <span class="text-stone-400 ml-1">{analysis.supply_demand.demand_summary}</span>
            </div>
            <div>
              <span class="text-stone-300 font-medium">Ausblick:</span>
              <span class="text-stone-400 ml-1">{analysis.supply_demand.balance_outlook}</span>
            </div>
          </div>
        {/if}
      </div>
    {/if}

    <!-- Macro Factors Section -->
    {#if analysis.macro_factors}
      <div class="border-t border-stone-700/50 pt-3">
        <button
          type="button"
          class="w-full flex items-center justify-between text-left"
          onclick={() => showMacro = !showMacro}
        >
          <span class="text-sm font-medium text-stone-200">Makroökonomische Faktoren</span>
          <svg
            class="w-4 h-4 text-stone-500 transition-transform {showMacro ? 'rotate-180' : ''}"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <path d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        {#if showMacro}
          <div class="mt-2 space-y-2">
            {#if analysis.macro_factors.factors.length > 0}
              <div class="flex flex-wrap gap-1.5">
                {#each analysis.macro_factors.factors as factor}
                  <span class="text-xs bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded border border-blue-500/30">
                    {factor}
                  </span>
                {/each}
              </div>
            {/if}
            <p class="text-stone-400 text-sm">{analysis.macro_factors.summary}</p>
          </div>
        {/if}
      </div>
    {/if}

    <!-- Upcoming Events Section -->
    <div class="border-t border-stone-700/50 pt-3">
      <button
        type="button"
        class="w-full flex items-center justify-between text-left"
        onclick={() => showEvents = !showEvents}
      >
        <span class="text-sm font-medium text-stone-200">
          Anstehende Termine
          {#if analysis.upcoming_events.length > 0}
            <span class="text-stone-500 ml-1">({analysis.upcoming_events.length})</span>
          {/if}
        </span>
        <svg
          class="w-4 h-4 text-stone-500 transition-transform {showEvents ? 'rotate-180' : ''}"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <path d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {#if showEvents}
        <div class="mt-2">
          <UpcomingEvents events={analysis.upcoming_events} />
        </div>
      {/if}
    </div>

    <!-- Sources Section -->
    {#if analysis.sources.length > 0}
      <div class="border-t border-stone-700/50 pt-3">
        <button
          type="button"
          class="w-full flex items-center justify-between text-left"
          onclick={() => showSources = !showSources}
        >
          <span class="text-sm font-medium text-stone-200">
            Quellen
            <span class="text-stone-500 ml-1">({analysis.sources.length})</span>
          </span>
          <svg
            class="w-4 h-4 text-stone-500 transition-transform {showSources ? 'rotate-180' : ''}"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <path d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        {#if showSources}
          <div class="mt-2">
            <NewsSourceList sources={analysis.sources} />
          </div>
        {/if}
      </div>
    {/if}

    <!-- Google Search Suggestions (for compliance) -->
    {#if analysis.rendered_content}
      <div class="border-t border-stone-700/50 pt-3">
        <div class="text-xs text-stone-600">
          <!-- eslint-disable-next-line svelte/no-at-html-tags -->
          {@html analysis.rendered_content}
        </div>
      </div>
    {/if}
  </div>

  <!-- Footer -->
  <div class="px-4 py-2 bg-stone-800/30 border-t border-stone-700/50 flex items-center justify-between text-xs text-stone-500">
    <span>
      Aktualisiert: {formatTimestamp(analysis.timestamp)}
    </span>
    {#if analysis.from_cache}
      <span class="flex items-center gap-1">
        <span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
        Cache
      </span>
    {:else}
      <span class="flex items-center gap-1">
        <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
        Live
      </span>
    {/if}
  </div>
</div>
