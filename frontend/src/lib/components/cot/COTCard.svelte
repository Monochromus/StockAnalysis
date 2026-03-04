<script lang="ts">
  /**
   * COT Card Component
   * Displays COT data for a single commodity
   */

  import type { COTDashboardItem, COTAnalysis } from '$lib/types';
  import COTIndexGauge from './COTIndexGauge.svelte';
  import PositionBreakdown from './PositionBreakdown.svelte';
  import WeeklyChanges from './WeeklyChanges.svelte';
  import { cotStore } from '$lib/stores/cot';

  export let item: COTDashboardItem;
  export let expanded: boolean = false;
  export let onSelect: ((symbol: string) => void) | undefined = undefined;

  let loading = false;
  let fullAnalysis: COTAnalysis | null = null;

  function getSignalBadgeClass(signal: string, strength: string): string {
    const baseClass = 'signal-badge';
    if (signal === 'bullish') return `${baseClass} bullish ${strength}`;
    if (signal === 'bearish') return `${baseClass} bearish ${strength}`;
    return `${baseClass} neutral`;
  }

  function getSignalText(signal: string): string {
    if (signal === 'bullish') return 'Bullisch';
    if (signal === 'bearish') return 'Bearisch';
    return 'Neutral';
  }

  async function toggleExpand() {
    expanded = !expanded;

    if (expanded && !fullAnalysis) {
      loading = true;
      fullAnalysis = await cotStore.loadAnalysis(item.symbol);
      loading = false;
    }
  }

  function handleSelect() {
    if (onSelect) {
      onSelect(item.symbol);
    }
  }

  function formatNumber(n: number): string {
    if (Math.abs(n) >= 1000000) {
      return (n / 1000000).toFixed(1) + 'M';
    }
    if (Math.abs(n) >= 1000) {
      return (n / 1000).toFixed(1) + 'K';
    }
    return n.toLocaleString();
  }

  function formatDate(dateStr: string): string {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('de-DE', {
      day: '2-digit',
      month: '2-digit',
      year: '2-digit',
    });
  }
</script>

<div class="cot-card" class:expanded>
  <div class="card-header" on:click={toggleExpand} on:keypress={toggleExpand} role="button" tabindex="0">
    <div class="header-main">
      <div class="commodity-info">
        <span class="commodity-symbol">{item.symbol}</span>
        <span class="commodity-name">{item.commodity_name}</span>
      </div>
      <span class={getSignalBadgeClass(item.signal, item.signal_strength)}>
        {getSignalText(item.signal)}
      </span>
    </div>

    <div class="header-metrics">
      <div class="metric">
        <span class="metric-label">COT-Index</span>
        <span class="metric-value">{item.cot_index_commercial.toFixed(0)}</span>
      </div>
      <div class="metric">
        <span class="metric-label">Commercial</span>
        <span class="metric-value" class:positive={item.commercial_net > 0} class:negative={item.commercial_net < 0}>
          {formatNumber(item.commercial_net)}
        </span>
      </div>
      <div class="metric">
        <span class="metric-label">1W Änderung</span>
        <span class="metric-value" class:positive={item.weekly_change_commercial > 0} class:negative={item.weekly_change_commercial < 0}>
          {item.weekly_change_commercial > 0 ? '+' : ''}{formatNumber(item.weekly_change_commercial)}
        </span>
      </div>

      <svg
        class="expand-icon"
        class:expanded
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
      >
        <polyline points="6,9 12,15 18,9" />
      </svg>
    </div>
  </div>

  {#if expanded}
    <div class="card-content">
      {#if loading}
        <div class="loading">
          <span class="spinner"></span>
          <span>Lade Daten...</span>
        </div>
      {:else}
        <div class="content-grid">
          <div class="gauges-section">
            <COTIndexGauge
              value={item.cot_index_commercial}
              label="Commercial COT-Index"
              type="commercial"
            />
            <COTIndexGauge
              value={item.cot_index_noncommercial}
              label="Non-Commercial COT-Index"
              type="noncommercial"
            />
          </div>

          <div class="positions-section">
            {#if fullAnalysis?.current}
              <PositionBreakdown
                longPositions={fullAnalysis.current.commercial_long}
                shortPositions={fullAnalysis.current.commercial_short}
                label="Commercial Positionen"
                color="#3B82F6"
              />
              <PositionBreakdown
                longPositions={fullAnalysis.current.noncommercial_long}
                shortPositions={fullAnalysis.current.noncommercial_short}
                label="Non-Commercial Positionen"
                color="#F59E0B"
              />
            {:else}
              <div class="positions-summary">
                <div class="position-row">
                  <span class="position-label">Commercial Net:</span>
                  <span class="position-value" class:positive={item.commercial_net > 0} class:negative={item.commercial_net < 0}>
                    {formatNumber(item.commercial_net)}
                  </span>
                </div>
                <div class="position-row">
                  <span class="position-label">Non-Commercial Net:</span>
                  <span class="position-value" class:positive={item.noncommercial_net > 0} class:negative={item.noncommercial_net < 0}>
                    {formatNumber(item.noncommercial_net)}
                  </span>
                </div>
              </div>
            {/if}
          </div>

          <div class="changes-section">
            <WeeklyChanges
              weeklyChange={item.weekly_change_commercial}
              monthlyChange={fullAnalysis?.monthly_change_commercial ?? 0}
              label="Commercial Änderungen"
            />
            <WeeklyChanges
              weeklyChange={item.weekly_change_noncommercial}
              monthlyChange={fullAnalysis?.monthly_change_noncommercial ?? 0}
              label="Non-Commercial Änderungen"
            />
          </div>
        </div>

        {#if fullAnalysis?.interpretation}
          <div class="interpretation-section">
            <h4>Interpretation</h4>
            <p>{fullAnalysis.interpretation}</p>
          </div>
        {/if}

        <div class="card-footer">
          <span class="last-update">
            Letzte Daten: {formatDate(item.last_update)}
          </span>
          {#if onSelect}
            <button class="select-btn" on:click|stopPropagation={handleSelect}>
              Auswählen
            </button>
          {/if}
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .cot-card {
    border: 1px solid #374151;
    border-radius: 0.5rem;
    background: #1F2937;
    overflow: hidden;
    transition: border-color 0.2s;
  }

  .cot-card:hover {
    border-color: #4B5563;
  }

  .cot-card.expanded {
    border-color: #3B82F6;
  }

  .card-header {
    padding: 0.75rem 1rem;
    cursor: pointer;
    user-select: none;
  }

  .card-header:hover {
    background: #374151;
  }

  .header-main {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
  }

  .commodity-info {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
  }

  .commodity-symbol {
    font-weight: 600;
    color: #E5E7EB;
  }

  .commodity-name {
    font-size: 0.875rem;
    color: #9CA3AF;
  }

  .signal-badge {
    padding: 0.25rem 0.5rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 500;
  }

  .signal-badge.bullish {
    background: rgba(16, 185, 129, 0.2);
    color: #10B981;
  }

  .signal-badge.bullish.strong {
    background: rgba(16, 185, 129, 0.3);
  }

  .signal-badge.bearish {
    background: rgba(239, 68, 68, 0.2);
    color: #EF4444;
  }

  .signal-badge.bearish.strong {
    background: rgba(239, 68, 68, 0.3);
  }

  .signal-badge.neutral {
    background: rgba(107, 114, 128, 0.2);
    color: #9CA3AF;
  }

  .header-metrics {
    display: flex;
    align-items: center;
    gap: 1.5rem;
  }

  .metric {
    display: flex;
    flex-direction: column;
  }

  .metric-label {
    font-size: 0.625rem;
    color: #6B7280;
  }

  .metric-value {
    font-size: 0.875rem;
    font-weight: 500;
    color: #E5E7EB;
  }

  .metric-value.positive {
    color: #10B981;
  }

  .metric-value.negative {
    color: #EF4444;
  }

  .expand-icon {
    width: 16px;
    height: 16px;
    color: #6B7280;
    margin-left: auto;
    transition: transform 0.2s;
  }

  .expand-icon.expanded {
    transform: rotate(180deg);
  }

  .card-content {
    border-top: 1px solid #374151;
    padding: 1rem;
  }

  .loading {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 2rem;
    color: #9CA3AF;
  }

  .spinner {
    width: 16px;
    height: 16px;
    border: 2px solid #374151;
    border-top-color: #3B82F6;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  .content-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
  }

  .gauges-section {
    grid-column: 1;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .positions-section {
    grid-column: 2;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .changes-section {
    grid-column: 1 / -1;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
  }

  .positions-summary {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    padding: 0.5rem 0;
  }

  .position-row {
    display: flex;
    justify-content: space-between;
    font-size: 0.875rem;
  }

  .position-label {
    color: #9CA3AF;
  }

  .position-value {
    font-weight: 500;
    color: #E5E7EB;
  }

  .position-value.positive {
    color: #10B981;
  }

  .position-value.negative {
    color: #EF4444;
  }

  .interpretation-section {
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid #374151;
  }

  .interpretation-section h4 {
    font-size: 0.875rem;
    font-weight: 600;
    color: #E5E7EB;
    margin-bottom: 0.5rem;
  }

  .interpretation-section p {
    font-size: 0.875rem;
    color: #9CA3AF;
    line-height: 1.5;
    margin: 0;
  }

  .card-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid #374151;
  }

  .last-update {
    font-size: 0.75rem;
    color: #6B7280;
  }

  .select-btn {
    padding: 0.375rem 0.75rem;
    background: #3B82F6;
    border: none;
    border-radius: 0.375rem;
    color: white;
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.2s;
  }

  .select-btn:hover {
    background: #2563EB;
  }

  @media (max-width: 640px) {
    .content-grid {
      grid-template-columns: 1fr;
    }

    .gauges-section,
    .positions-section,
    .changes-section {
      grid-column: 1;
    }

    .changes-section {
      grid-template-columns: 1fr;
    }

    .header-metrics {
      gap: 1rem;
      flex-wrap: wrap;
    }
  }
</style>
