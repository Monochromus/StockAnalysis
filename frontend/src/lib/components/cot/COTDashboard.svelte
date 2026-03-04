<script lang="ts">
  /**
   * COT Dashboard Component
   * Main view for COT analysis across multiple commodities
   */

  import { onMount } from 'svelte';
  import { cotStore, cotByGroup, cotBullishSignals, cotBearishSignals } from '$lib/stores/cot';
  import { watchlistSymbols } from '$lib/stores/watchlist';
  import COTCard from './COTCard.svelte';
  import COTLegend from './COTLegend.svelte';
  import COTChart from './COTChart.svelte';
  import type { COTDashboardItem, COTAnalysis } from '$lib/types';

  export let symbols: string[] = [];
  export let onSelectSymbol: ((symbol: string) => void) | undefined = undefined;

  let selectedSymbol: string | null = null;
  let selectedAnalysis: COTAnalysis | null = null;
  let legendExpanded = false;

  // Use watchlist if no symbols provided
  $: effectiveSymbols = symbols.length > 0 ? symbols : $watchlistSymbols;

  // Load dashboard when symbols change
  $: if (effectiveSymbols.length > 0) {
    loadDashboard();
  }

  onMount(async () => {
    await cotStore.checkStatus();
    if (effectiveSymbols.length > 0) {
      await loadDashboard();
    }
  });

  async function loadDashboard() {
    await cotStore.loadDashboard(effectiveSymbols);
  }

  async function handleRefresh() {
    await cotStore.loadDashboard(effectiveSymbols, true);
  }

  async function handleSelectSymbol(symbol: string) {
    selectedSymbol = symbol;
    selectedAnalysis = await cotStore.loadAnalysis(symbol, { weeks: 52 });

    if (onSelectSymbol) {
      onSelectSymbol(symbol);
    }
  }

  function closeDetail() {
    selectedSymbol = null;
    selectedAnalysis = null;
  }

  function formatDate(dateStr: string | null | undefined): string {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('de-DE', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  }

  function getSignalCount(items: COTDashboardItem[], signal: string): number {
    return items.filter(i => i.signal === signal).length;
  }
</script>

<div class="cot-dashboard">
  <div class="dashboard-header">
    <div class="header-title">
      <h2>COT Analyse</h2>
      <span class="subtitle">Commitments of Traders</span>
    </div>

    <div class="header-info">
      {#if $cotStore.status}
        <span class="last-update">
          CFTC-Daten: {formatDate($cotStore.status.last_cftc_update)}
        </span>
      {/if}

      <div class="signal-summary">
        <span class="signal-count bullish">
          <span class="count">{$cotBullishSignals.length}</span>
          <span class="label">Bullisch</span>
        </span>
        <span class="signal-count bearish">
          <span class="count">{$cotBearishSignals.length}</span>
          <span class="label">Bearisch</span>
        </span>
      </div>
    </div>

    <div class="header-actions">
      <button
        class="refresh-btn"
        on:click={handleRefresh}
        disabled={$cotStore.loading}
      >
        <svg
          class="refresh-icon"
          class:spinning={$cotStore.loading}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" />
        </svg>
        Aktualisieren
      </button>
    </div>
  </div>

  {#if $cotStore.error}
    <div class="error-message">
      {$cotStore.error}
    </div>
  {/if}

  {#if $cotStore.loading && $cotStore.dashboardItems.length === 0}
    <div class="loading-state">
      <span class="spinner"></span>
      <span>Lade COT-Daten...</span>
    </div>
  {:else if $cotStore.dashboardItems.length === 0}
    <div class="empty-state">
      <p>Keine COT-Daten verfügbar.</p>
      <p class="hint">
        Füge Rohstoff-Futures zu deiner Watchlist hinzu, um COT-Analysen zu sehen.
      </p>
      {#if $cotStore.status?.supported_symbols}
        <div class="supported-symbols">
          <span class="label">Unterstützte Symbole:</span>
          <div class="symbols-list">
            {#each $cotStore.status.supported_symbols.slice(0, 12) as symbol}
              <span class="symbol-badge">{symbol}</span>
            {/each}
            {#if $cotStore.status.supported_symbols.length > 12}
              <span class="more">+{$cotStore.status.supported_symbols.length - 12} weitere</span>
            {/if}
          </div>
        </div>
      {/if}
    </div>
  {:else}
    <!-- Selected symbol detail view -->
    {#if selectedSymbol && selectedAnalysis}
      <div class="detail-view">
        <div class="detail-header">
          <button class="back-btn" on:click={closeDetail}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M19 12H5M12 19l-7-7 7-7" />
            </svg>
            Zurück
          </button>
          <h3>{selectedAnalysis.commodity_name} ({selectedSymbol})</h3>
        </div>

        <div class="detail-content">
          {#if selectedAnalysis.history.length > 0}
            <div class="chart-section">
              <h4>Historische Net Positionen</h4>
              <COTChart history={selectedAnalysis.history} height={250} />
            </div>
          {/if}

          <div class="detail-interpretation">
            <h4>Analyse</h4>
            <p class="signal-text">
              <span class="signal-badge {selectedAnalysis.signal}">
                {selectedAnalysis.signal === 'bullish' ? 'Bullisch' : selectedAnalysis.signal === 'bearish' ? 'Bearisch' : 'Neutral'}
              </span>
              <span class="signal-strength">({selectedAnalysis.signal_strength})</span>
            </p>
            <p class="interpretation">{selectedAnalysis.interpretation}</p>
          </div>
        </div>
      </div>
    {:else}
      <!-- Dashboard grid view -->
      <div class="dashboard-content">
        {#each [...$cotByGroup] as [group, items]}
          <div class="group-section">
            <h3 class="group-title">{group}</h3>
            <div class="cards-grid">
              {#each items as item (item.symbol)}
                <COTCard
                  {item}
                  onSelect={handleSelectSymbol}
                />
              {/each}
            </div>
          </div>
        {/each}
      </div>
    {/if}
  {/if}

  <div class="dashboard-footer">
    <COTLegend bind:expanded={legendExpanded} />
  </div>
</div>

<style>
  .cot-dashboard {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    padding: 1rem;
    height: 100%;
    overflow-y: auto;
  }

  .dashboard-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 1rem;
  }

  .header-title {
    display: flex;
    flex-direction: column;
  }

  .header-title h2 {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 600;
    color: #E5E7EB;
  }

  .subtitle {
    font-size: 0.75rem;
    color: #6B7280;
  }

  .header-info {
    display: flex;
    align-items: center;
    gap: 1.5rem;
  }

  .last-update {
    font-size: 0.75rem;
    color: #6B7280;
  }

  .signal-summary {
    display: flex;
    gap: 0.75rem;
  }

  .signal-count {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.25rem 0.5rem;
    border-radius: 9999px;
    font-size: 0.75rem;
  }

  .signal-count.bullish {
    background: rgba(16, 185, 129, 0.2);
    color: #10B981;
  }

  .signal-count.bearish {
    background: rgba(239, 68, 68, 0.2);
    color: #EF4444;
  }

  .signal-count .count {
    font-weight: 600;
  }

  .header-actions {
    display: flex;
    gap: 0.5rem;
  }

  .refresh-btn {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.5rem 0.75rem;
    background: #374151;
    border: none;
    border-radius: 0.375rem;
    color: #E5E7EB;
    font-size: 0.875rem;
    cursor: pointer;
    transition: background 0.2s;
  }

  .refresh-btn:hover:not(:disabled) {
    background: #4B5563;
  }

  .refresh-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .refresh-icon {
    width: 16px;
    height: 16px;
  }

  .refresh-icon.spinning {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  .error-message {
    padding: 0.75rem 1rem;
    background: rgba(239, 68, 68, 0.2);
    border: 1px solid rgba(239, 68, 68, 0.3);
    border-radius: 0.5rem;
    color: #EF4444;
    font-size: 0.875rem;
  }

  .loading-state,
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 3rem;
    text-align: center;
    color: #9CA3AF;
  }

  .spinner {
    width: 24px;
    height: 24px;
    border: 2px solid #374151;
    border-top-color: #3B82F6;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 1rem;
  }

  .empty-state p {
    margin: 0;
  }

  .empty-state .hint {
    font-size: 0.875rem;
    margin-top: 0.5rem;
  }

  .supported-symbols {
    margin-top: 1rem;
    text-align: center;
  }

  .supported-symbols .label {
    font-size: 0.75rem;
    color: #6B7280;
    display: block;
    margin-bottom: 0.5rem;
  }

  .symbols-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem;
    justify-content: center;
  }

  .symbol-badge {
    padding: 0.125rem 0.375rem;
    background: #374151;
    border-radius: 0.25rem;
    font-size: 0.75rem;
    color: #E5E7EB;
  }

  .more {
    font-size: 0.75rem;
    color: #6B7280;
    padding: 0.125rem 0.375rem;
  }

  .dashboard-content {
    flex: 1;
    overflow-y: auto;
  }

  .group-section {
    margin-bottom: 1.5rem;
  }

  .group-title {
    font-size: 0.875rem;
    font-weight: 600;
    color: #9CA3AF;
    margin: 0 0 0.75rem 0;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #374151;
  }

  .cards-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 1rem;
  }

  /* Detail view styles */
  .detail-view {
    flex: 1;
    display: flex;
    flex-direction: column;
  }

  .detail-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1rem;
  }

  .back-btn {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.5rem 0.75rem;
    background: #374151;
    border: none;
    border-radius: 0.375rem;
    color: #E5E7EB;
    font-size: 0.875rem;
    cursor: pointer;
    transition: background 0.2s;
  }

  .back-btn:hover {
    background: #4B5563;
  }

  .back-btn svg {
    width: 16px;
    height: 16px;
  }

  .detail-header h3 {
    margin: 0;
    font-size: 1.125rem;
    color: #E5E7EB;
  }

  .detail-content {
    flex: 1;
    overflow-y: auto;
  }

  .chart-section {
    margin-bottom: 1.5rem;
  }

  .chart-section h4,
  .detail-interpretation h4 {
    font-size: 0.875rem;
    font-weight: 600;
    color: #E5E7EB;
    margin: 0 0 0.75rem 0;
  }

  .detail-interpretation {
    background: #1F2937;
    border: 1px solid #374151;
    border-radius: 0.5rem;
    padding: 1rem;
  }

  .signal-text {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: 0 0 0.75rem 0;
  }

  .signal-badge {
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.875rem;
    font-weight: 500;
  }

  .signal-badge.bullish {
    background: rgba(16, 185, 129, 0.2);
    color: #10B981;
  }

  .signal-badge.bearish {
    background: rgba(239, 68, 68, 0.2);
    color: #EF4444;
  }

  .signal-badge.neutral {
    background: rgba(107, 114, 128, 0.2);
    color: #9CA3AF;
  }

  .signal-strength {
    font-size: 0.75rem;
    color: #6B7280;
  }

  .interpretation {
    margin: 0;
    font-size: 0.875rem;
    color: #9CA3AF;
    line-height: 1.6;
  }

  .dashboard-footer {
    margin-top: auto;
    padding-top: 1rem;
  }

  @media (max-width: 768px) {
    .dashboard-header {
      flex-direction: column;
      align-items: stretch;
    }

    .header-info {
      justify-content: space-between;
    }

    .header-actions {
      justify-content: flex-end;
    }

    .cards-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
