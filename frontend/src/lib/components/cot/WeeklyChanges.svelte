<script lang="ts">
  /**
   * Weekly Changes Component
   * Shows weekly and monthly position changes with arrows
   */

  export let weeklyChange: number;
  export let monthlyChange: number;
  export let label: string = '';

  function formatChange(n: number): string {
    const prefix = n >= 0 ? '+' : '';
    if (Math.abs(n) >= 1000000) {
      return prefix + (n / 1000000).toFixed(1) + 'M';
    }
    if (Math.abs(n) >= 1000) {
      return prefix + (n / 1000).toFixed(1) + 'K';
    }
    return prefix + n.toLocaleString();
  }

  function getArrow(n: number): string {
    if (n > 0) return '▲';
    if (n < 0) return '▼';
    return '─';
  }

  function getColor(n: number): string {
    if (n > 0) return '#10B981'; // green
    if (n < 0) return '#EF4444'; // red
    return '#6B7280'; // gray
  }
</script>

<div class="weekly-changes">
  {#if label}
    <div class="changes-label">{label}</div>
  {/if}

  <div class="changes-grid">
    <div class="change-item">
      <span class="change-period">1W</span>
      <span class="change-value" style="color: {getColor(weeklyChange)}">
        <span class="arrow">{getArrow(weeklyChange)}</span>
        {formatChange(weeklyChange)}
      </span>
    </div>

    <div class="change-item">
      <span class="change-period">1M</span>
      <span class="change-value" style="color: {getColor(monthlyChange)}">
        <span class="arrow">{getArrow(monthlyChange)}</span>
        {formatChange(monthlyChange)}
      </span>
    </div>
  </div>
</div>

<style>
  .weekly-changes {
    padding: 0.25rem 0;
  }

  .changes-label {
    font-size: 0.75rem;
    color: #9CA3AF;
    margin-bottom: 0.25rem;
  }

  .changes-grid {
    display: flex;
    gap: 1rem;
  }

  .change-item {
    display: flex;
    flex-direction: column;
  }

  .change-period {
    font-size: 0.625rem;
    color: #6B7280;
  }

  .change-value {
    font-size: 0.875rem;
    font-weight: 500;
    display: flex;
    align-items: center;
    gap: 0.25rem;
  }

  .arrow {
    font-size: 0.625rem;
  }
</style>
