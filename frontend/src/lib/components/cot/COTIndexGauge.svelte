<script lang="ts">
  /**
   * COT Index Gauge Component
   * Displays a visual gauge for COT Index (0-100)
   */

  export let value: number;
  export let label: string = 'COT Index';
  export let type: 'commercial' | 'noncommercial' = 'commercial';

  // Calculate color based on value and type
  $: color = getColor(value, type);
  $: percentage = Math.max(0, Math.min(100, value));

  function getColor(val: number, traderType: string): string {
    if (traderType === 'commercial') {
      // Commercials: high = bullish (green), low = bearish (red)
      if (val >= 80) return '#10B981'; // green
      if (val >= 60) return '#34D399'; // light green
      if (val <= 20) return '#EF4444'; // red
      if (val <= 40) return '#F87171'; // light red
      return '#6B7280'; // gray (neutral)
    } else {
      // Non-commercials: high = bearish (red), low = bullish (green)
      // (Crowded long = bearish, extreme short = bullish)
      if (val >= 80) return '#F87171'; // light red
      if (val >= 60) return '#FBBF24'; // yellow/warning
      if (val <= 20) return '#34D399'; // light green
      if (val <= 40) return '#6B7280'; // gray
      return '#6B7280'; // gray (neutral)
    }
  }

  function getSignalText(val: number, traderType: string): string {
    if (traderType === 'commercial') {
      if (val >= 80) return 'Extrem Long';
      if (val >= 60) return 'Long';
      if (val <= 20) return 'Extrem Short';
      if (val <= 40) return 'Short';
      return 'Neutral';
    } else {
      if (val >= 80) return 'Überkauft';
      if (val >= 60) return 'Long';
      if (val <= 20) return 'Überverkauft';
      if (val <= 40) return 'Short';
      return 'Neutral';
    }
  }
</script>

<div class="cot-gauge">
  <div class="gauge-header">
    <span class="gauge-label">{label}</span>
    <span class="gauge-value" style="color: {color}">{value.toFixed(1)}</span>
  </div>

  <div class="gauge-bar-container">
    <div class="gauge-bar">
      <div
        class="gauge-fill"
        style="width: {percentage}%; background-color: {color}"
      ></div>
      <!-- Markers -->
      <div class="gauge-marker" style="left: 20%"></div>
      <div class="gauge-marker" style="left: 80%"></div>
    </div>
    <div class="gauge-labels">
      <span>0</span>
      <span>50</span>
      <span>100</span>
    </div>
  </div>

  <div class="gauge-signal" style="color: {color}">
    {getSignalText(value, type)}
  </div>
</div>

<style>
  .cot-gauge {
    padding: 0.5rem;
  }

  .gauge-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
  }

  .gauge-label {
    font-size: 0.75rem;
    color: #9CA3AF;
  }

  .gauge-value {
    font-size: 1.25rem;
    font-weight: 600;
  }

  .gauge-bar-container {
    margin-bottom: 0.25rem;
  }

  .gauge-bar {
    position: relative;
    height: 8px;
    background: #374151;
    border-radius: 4px;
    overflow: hidden;
  }

  .gauge-fill {
    height: 100%;
    transition: width 0.3s ease, background-color 0.3s ease;
    border-radius: 4px;
  }

  .gauge-marker {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 2px;
    background: rgba(255, 255, 255, 0.3);
  }

  .gauge-labels {
    display: flex;
    justify-content: space-between;
    font-size: 0.625rem;
    color: #6B7280;
    margin-top: 2px;
  }

  .gauge-signal {
    text-align: center;
    font-size: 0.75rem;
    font-weight: 500;
    margin-top: 0.25rem;
  }
</style>
