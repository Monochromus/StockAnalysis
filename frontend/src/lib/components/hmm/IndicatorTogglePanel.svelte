<script lang="ts">
  import type { IndicatorToggleState } from '$lib/types';

  let {
    toggles,
    onToggle,
  }: {
    toggles: IndicatorToggleState;
    onToggle: (indicator: keyof IndicatorToggleState) => void;
  } = $props();

  const overlayIndicators: Array<{ key: keyof IndicatorToggleState; label: string; color: string }> = [
    { key: 'sma_20', label: 'SMA 20', color: '#FFFF00' },
    { key: 'sma_50', label: 'SMA 50', color: '#FF9800' },
    { key: 'sma_200', label: 'SMA 200', color: '#E91E63' },
    { key: 'ema_12', label: 'EMA 12', color: '#00BCD4' },
    { key: 'ema_26', label: 'EMA 26', color: '#9C27B0' },
    { key: 'bollinger', label: 'Bollinger', color: '#2196F3' },
  ];

  const subplotIndicators: Array<{ key: keyof IndicatorToggleState; label: string; color: string }> = [
    { key: 'volume', label: 'Volume', color: '#64B5F6' },
    { key: 'rsi', label: 'RSI', color: '#9C27B0' },
    { key: 'macd', label: 'MACD', color: '#2196F3' },
    { key: 'adx', label: 'ADX', color: '#FFEB3B' },
    { key: 'atr', label: 'ATR', color: '#FF7043' },
  ];
</script>

<div class="p-3 space-y-4">
  <!-- Overlays Section -->
  <div>
    <h4 class="text-xs font-medium text-text-muted mb-2 uppercase tracking-wide">Chart Overlays</h4>
    <div class="flex flex-wrap gap-2">
      {#each overlayIndicators as indicator}
        <button
          class="px-2.5 py-1.5 text-xs rounded-lg border transition-all duration-200 flex items-center gap-1.5"
          class:liquid-glass-subtle={!toggles[indicator.key]}
          class:border-bg-border={!toggles[indicator.key]}
          class:text-text-muted={!toggles[indicator.key]}
          class:bg-opacity-20={toggles[indicator.key]}
          class:border-opacity-60={toggles[indicator.key]}
          style:background-color={toggles[indicator.key] ? `${indicator.color}20` : undefined}
          style:border-color={toggles[indicator.key] ? indicator.color : undefined}
          style:color={toggles[indicator.key] ? indicator.color : undefined}
          onclick={() => onToggle(indicator.key)}
        >
          <span
            class="w-2 h-2 rounded-full"
            style:background-color={indicator.color}
          ></span>
          {indicator.label}
        </button>
      {/each}
    </div>
  </div>

  <!-- Subplots Section -->
  <div>
    <h4 class="text-xs font-medium text-text-muted mb-2 uppercase tracking-wide">Subplots</h4>
    <div class="flex flex-wrap gap-2">
      {#each subplotIndicators as indicator}
        <button
          class="px-2.5 py-1.5 text-xs rounded-lg border transition-all duration-200 flex items-center gap-1.5"
          class:liquid-glass-subtle={!toggles[indicator.key]}
          class:border-bg-border={!toggles[indicator.key]}
          class:text-text-muted={!toggles[indicator.key]}
          class:bg-opacity-20={toggles[indicator.key]}
          class:border-opacity-60={toggles[indicator.key]}
          style:background-color={toggles[indicator.key] ? `${indicator.color}20` : undefined}
          style:border-color={toggles[indicator.key] ? indicator.color : undefined}
          style:color={toggles[indicator.key] ? indicator.color : undefined}
          onclick={() => onToggle(indicator.key)}
        >
          <span
            class="w-2 h-2 rounded-full"
            style:background-color={indicator.color}
          ></span>
          {indicator.label}
        </button>
      {/each}
    </div>
  </div>
</div>
