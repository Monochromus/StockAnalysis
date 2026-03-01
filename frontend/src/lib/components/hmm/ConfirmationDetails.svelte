<script lang="ts">
  import type { TradingSignal } from '$lib/types';

  let {
    signal,
  }: {
    signal: TradingSignal | null;
  } = $props();

  // Map of condition keys to human-readable labels
  const conditionLabels: Record<string, string> = {
    // Long conditions
    regime_bullish: 'Regime is Bullish',
    regime_confidence: 'High Confidence',
    rsi_favorable: 'RSI Favorable',
    macd_bullish: 'MACD Bullish',
    adx_bullish: 'ADX Shows Uptrend',
    momentum_positive: 'Positive Momentum',
    volume_strong: 'Strong Volume',
    price_above_ma: 'Price Above MA',
    // Short conditions
    regime_bearish: 'Regime is Bearish',
    macd_bearish: 'MACD Bearish',
    adx_bearish: 'ADX Shows Downtrend',
    momentum_negative: 'Negative Momentum',
    price_below_ma: 'Price Below MA',
    // Special conditions
    cooldown_active: 'Cooldown Active',
    chop_regime: 'Chop Regime',
  };

  function getConditionIcon(met: boolean | undefined): string {
    if (met === true) return '✓';
    if (met === false) return '✗';
    return '-';
  }

  function getConditionClass(met: boolean | undefined): string {
    if (met === true) return 'text-green-400';
    if (met === false) return 'text-red-400';
    return 'text-text-muted';
  }

  // Get the relevant conditions based on signal type
  function getConditions(): Array<{ key: string; label: string; met: boolean | undefined }> {
    if (!signal || !signal.details) return [];

    const conditions: Array<{ key: string; label: string; met: boolean | undefined }> = [];
    const details = signal.details;

    // Determine which conditions to show based on signal direction
    const isLongBiased = signal.signal === 'LONG' ||
                         (details.regime_bullish !== undefined);

    if (isLongBiased) {
      // Long conditions
      if (details.regime_bullish !== undefined) {
        conditions.push({ key: 'regime_bullish', label: conditionLabels.regime_bullish, met: details.regime_bullish });
      }
      if (details.regime_confidence !== undefined) {
        conditions.push({ key: 'regime_confidence', label: conditionLabels.regime_confidence, met: details.regime_confidence });
      }
      if (details.rsi_favorable !== undefined) {
        conditions.push({ key: 'rsi_favorable', label: conditionLabels.rsi_favorable, met: details.rsi_favorable });
      }
      if (details.macd_bullish !== undefined) {
        conditions.push({ key: 'macd_bullish', label: conditionLabels.macd_bullish, met: details.macd_bullish });
      }
      if (details.adx_bullish !== undefined) {
        conditions.push({ key: 'adx_bullish', label: conditionLabels.adx_bullish, met: details.adx_bullish });
      }
      if (details.momentum_positive !== undefined) {
        conditions.push({ key: 'momentum_positive', label: conditionLabels.momentum_positive, met: details.momentum_positive });
      }
      if (details.volume_strong !== undefined) {
        conditions.push({ key: 'volume_strong', label: conditionLabels.volume_strong, met: details.volume_strong });
      }
      if (details.price_above_ma !== undefined) {
        conditions.push({ key: 'price_above_ma', label: conditionLabels.price_above_ma, met: details.price_above_ma });
      }
    } else {
      // Short conditions
      if (details.regime_bearish !== undefined) {
        conditions.push({ key: 'regime_bearish', label: conditionLabels.regime_bearish, met: details.regime_bearish });
      }
      if (details.regime_confidence !== undefined) {
        conditions.push({ key: 'regime_confidence', label: conditionLabels.regime_confidence, met: details.regime_confidence });
      }
      if (details.rsi_favorable !== undefined) {
        conditions.push({ key: 'rsi_favorable', label: conditionLabels.rsi_favorable, met: details.rsi_favorable });
      }
      if (details.macd_bearish !== undefined) {
        conditions.push({ key: 'macd_bearish', label: conditionLabels.macd_bearish, met: details.macd_bearish });
      }
      if (details.adx_bearish !== undefined) {
        conditions.push({ key: 'adx_bearish', label: conditionLabels.adx_bearish, met: details.adx_bearish });
      }
      if (details.momentum_negative !== undefined) {
        conditions.push({ key: 'momentum_negative', label: conditionLabels.momentum_negative, met: details.momentum_negative });
      }
      if (details.volume_strong !== undefined) {
        conditions.push({ key: 'volume_strong', label: conditionLabels.volume_strong, met: details.volume_strong });
      }
      if (details.price_below_ma !== undefined) {
        conditions.push({ key: 'price_below_ma', label: conditionLabels.price_below_ma, met: details.price_below_ma });
      }
    }

    // Special conditions
    if (details.cooldown_active) {
      conditions.push({ key: 'cooldown_active', label: conditionLabels.cooldown_active, met: true });
    }
    if (details.chop_regime) {
      conditions.push({ key: 'chop_regime', label: conditionLabels.chop_regime, met: true });
    }

    return conditions;
  }
</script>

<div class="p-4">
  <h3 class="text-xs font-medium text-text-muted uppercase tracking-wide mb-3">Confirmation Details</h3>

  {#if signal && signal.details}
    <div class="space-y-1">
      {#each getConditions() as condition}
        <div class="flex items-center justify-between py-1.5 px-2 liquid-glass-subtle rounded-lg">
          <span class="text-xs text-text-primary">{condition.label}</span>
          <span class="text-sm font-bold {getConditionClass(condition.met)}">
            {getConditionIcon(condition.met)}
          </span>
        </div>
      {/each}
    </div>

    {#if getConditions().length === 0}
      <div class="text-center text-text-muted text-xs py-4">
        No detailed conditions available
      </div>
    {/if}
  {:else}
    <div class="text-center text-text-muted text-xs py-4">
      Analyze a symbol to see confirmation details
    </div>
  {/if}
</div>
