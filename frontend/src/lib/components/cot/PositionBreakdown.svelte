<script lang="ts">
  /**
   * Position Breakdown Component
   * Shows horizontal bar chart of long/short positions
   */

  export let longPositions: number;
  export let shortPositions: number;
  export let label: string = 'Positions';
  export let color: string = '#3B82F6'; // blue

  $: total = longPositions + shortPositions;
  $: longPct = total > 0 ? (longPositions / total) * 100 : 50;
  $: shortPct = total > 0 ? (shortPositions / total) * 100 : 50;

  function formatNumber(n: number): string {
    if (Math.abs(n) >= 1000000) {
      return (n / 1000000).toFixed(1) + 'M';
    }
    if (Math.abs(n) >= 1000) {
      return (n / 1000).toFixed(1) + 'K';
    }
    return n.toLocaleString();
  }
</script>

<div class="position-breakdown">
  <div class="breakdown-header">
    <span class="breakdown-label">{label}</span>
  </div>

  <div class="breakdown-bar">
    <div
      class="bar-long"
      style="width: {longPct}%; background-color: {color}"
      title="Long: {formatNumber(longPositions)}"
    ></div>
    <div
      class="bar-short"
      style="width: {shortPct}%"
      title="Short: {formatNumber(shortPositions)}"
    ></div>
  </div>

  <div class="breakdown-values">
    <div class="value-item">
      <span class="value-label">Long</span>
      <span class="value-number" style="color: {color}">{formatNumber(longPositions)}</span>
    </div>
    <div class="value-item">
      <span class="value-label">Short</span>
      <span class="value-number short">{formatNumber(shortPositions)}</span>
    </div>
  </div>
</div>

<style>
  .position-breakdown {
    padding: 0.5rem 0;
  }

  .breakdown-header {
    margin-bottom: 0.25rem;
  }

  .breakdown-label {
    font-size: 0.75rem;
    color: #9CA3AF;
  }

  .breakdown-bar {
    display: flex;
    height: 12px;
    border-radius: 6px;
    overflow: hidden;
    background: #374151;
  }

  .bar-long {
    transition: width 0.3s ease;
  }

  .bar-short {
    background: #6B7280;
    transition: width 0.3s ease;
  }

  .breakdown-values {
    display: flex;
    justify-content: space-between;
    margin-top: 0.25rem;
  }

  .value-item {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
  }

  .value-item:last-child {
    align-items: flex-end;
  }

  .value-label {
    font-size: 0.625rem;
    color: #6B7280;
  }

  .value-number {
    font-size: 0.875rem;
    font-weight: 500;
  }

  .value-number.short {
    color: #9CA3AF;
  }
</style>
