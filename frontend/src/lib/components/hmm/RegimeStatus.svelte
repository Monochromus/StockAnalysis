<script lang="ts">
  import type { RegimeInfo, TradingSignal } from '$lib/types';

  let {
    regime,
    signal,
  }: {
    regime: RegimeInfo | null;
    signal: TradingSignal | null;
  } = $props();

  const regimeColors: Record<string, string> = {
    'Crash': '#FF0000',
    'Bear': '#FF6B6B',
    'Neutral Down': '#FFB4B4',
    'Chop': '#808080',
    'Neutral Up': '#B4FFB4',
    'Bull': '#6BFF6B',
    'Bull Run': '#00FF00',
  };

  const signalColors: Record<string, string> = {
    'LONG': '#00FF00',
    'SHORT': '#FF0000',
    'CASH': '#808080',
    'HOLD': '#FFFF00',
  };

  function getRegimeColor(regimeName: string): string {
    return regimeColors[regimeName] || '#808080';
  }

  function getSignalColor(signalType: string): string {
    return signalColors[signalType] || '#FFFF00';
  }

  function formatConfidence(value: number): string {
    return `${Math.round(value * 100)}%`;
  }
</script>

<div class="p-4 space-y-4">
  <!-- Current Regime -->
  <div class="space-y-2">
    <h3 class="text-xs font-medium text-text-muted uppercase tracking-wide">Current Regime</h3>
    {#if regime}
      <div
        class="p-3 rounded-xl border-2 text-center liquid-glass-subtle"
        style:border-color={getRegimeColor(regime.regime_name)}
        style:background-color={`${getRegimeColor(regime.regime_name)}12`}
      >
        <div
          class="text-lg font-bold"
          style:color={getRegimeColor(regime.regime_name)}
        >
          {regime.regime_name}
        </div>
        <div class="text-xs text-text-muted mt-1">
          Confidence: {formatConfidence(regime.confidence)}
        </div>
      </div>

      <!-- Confidence Gauge -->
      <div class="space-y-1">
        <div class="flex justify-between text-xs text-text-muted">
          <span>Confidence</span>
          <span>{formatConfidence(regime.confidence)}</span>
        </div>
        <div class="h-2 liquid-glass-subtle rounded-full overflow-hidden">
          <div
            class="h-full transition-all duration-300"
            style:width={`${regime.confidence * 100}%`}
            style:background-color={getRegimeColor(regime.regime_name)}
          ></div>
        </div>
      </div>

      <!-- Regime Stats -->
      <div class="grid grid-cols-2 gap-2 text-xs">
        <div class="p-2 liquid-glass-subtle rounded-lg">
          <div class="text-text-muted">Mean Return</div>
          <div class="font-medium" class:text-green-400={regime.mean_return > 0} class:text-red-400={regime.mean_return < 0}>
            {regime.mean_return > 0 ? '+' : ''}{regime.mean_return.toFixed(2)}%
          </div>
        </div>
        <div class="p-2 liquid-glass-subtle rounded-lg">
          <div class="text-text-muted">Volatility</div>
          <div class="font-medium">{regime.volatility.toFixed(2)}%</div>
        </div>
      </div>
    {:else}
      <div class="p-3 liquid-glass-subtle rounded-xl text-center text-text-muted">
        No regime data
      </div>
    {/if}
  </div>

  <!-- Trading Signal -->
  <div class="space-y-2">
    <h3 class="text-xs font-medium text-text-muted uppercase tracking-wide">Trading Signal</h3>
    {#if signal}
      <div
        class="p-3 rounded-xl border-2 text-center liquid-glass-subtle"
        style:border-color={getSignalColor(signal.signal)}
        style:background-color={`${getSignalColor(signal.signal)}12`}
      >
        <div
          class="text-2xl font-bold"
          style:color={getSignalColor(signal.signal)}
        >
          {signal.signal}
        </div>
        <div class="text-xs text-text-muted mt-1">
          {signal.confirmations_met} / {signal.total_conditions} confirmations
        </div>
      </div>

      <!-- Confirmation Progress -->
      <div class="space-y-1">
        <div class="flex justify-between text-xs text-text-muted">
          <span>Confirmations</span>
          <span>{signal.confirmations_met} / {signal.total_conditions}</span>
        </div>
        <div class="h-2 liquid-glass-subtle rounded-full overflow-hidden flex">
          {#each Array(signal.total_conditions) as _, i}
            <div
              class="flex-1 h-full border-r border-bg-primary last:border-r-0 transition-colors duration-300"
              class:bg-green-500={i < signal.confirmations_met}
              class:bg-bg-tertiary={i >= signal.confirmations_met}
            ></div>
          {/each}
        </div>
      </div>
    {:else}
      <div class="p-3 liquid-glass-subtle rounded-xl text-center text-text-muted">
        No signal data
      </div>
    {/if}
  </div>
</div>
