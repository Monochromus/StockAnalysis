<script lang="ts">
  import type { BacktestResult } from '$lib/types';

  let {
    result,
    loading = false,
    onRunBacktest,
  }: {
    result: BacktestResult | null;
    loading?: boolean;
    onRunBacktest: () => void;
  } = $props();

  function formatPercent(value: number): string {
    const sign = value > 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}%`;
  }

  function formatNumber(value: number): string {
    return value.toFixed(2);
  }
</script>

<div class="p-4 space-y-4">
  <div class="flex items-center justify-between">
    <h3 class="text-xs font-medium text-text-muted uppercase tracking-wide">Backtest Results</h3>
    <button
      class="px-3 py-1 text-xs liquid-glass-subtle bg-amber-600/80 text-white rounded-lg hover:bg-amber-500/80 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
      onclick={onRunBacktest}
      disabled={loading}
    >
      {loading ? 'Running...' : 'Run Backtest'}
    </button>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-8">
      <div class="animate-spin w-6 h-6 border-2 border-accent-primary border-t-transparent rounded-full"></div>
    </div>
  {:else if result}
    <!-- Key Metrics -->
    <div class="grid grid-cols-2 gap-2">
      <div class="p-3 liquid-glass-subtle rounded-xl">
        <div class="text-xs text-text-muted">Total Return</div>
        <div class="text-lg font-bold" class:text-green-400={result.total_return > 0} class:text-red-400={result.total_return < 0}>
          {formatPercent(result.total_return)}
        </div>
      </div>
      <div class="p-3 liquid-glass-subtle rounded-xl">
        <div class="text-xs text-text-muted">Buy & Hold</div>
        <div class="text-lg font-bold" class:text-green-400={result.buy_hold_return > 0} class:text-red-400={result.buy_hold_return < 0}>
          {formatPercent(result.buy_hold_return)}
        </div>
      </div>
    </div>

    <!-- Alpha -->
    <div class="p-3 liquid-glass-subtle rounded-xl">
      <div class="flex justify-between items-center">
        <span class="text-xs text-text-muted">Alpha (Strategy vs B&H)</span>
        <span class="text-lg font-bold" class:text-green-400={result.alpha > 0} class:text-red-400={result.alpha < 0}>
          {formatPercent(result.alpha)}
        </span>
      </div>
    </div>

    <!-- Risk Metrics -->
    <div class="grid grid-cols-2 gap-2">
      <div class="p-2 liquid-glass-subtle rounded-lg">
        <div class="text-xs text-text-muted">Sharpe Ratio</div>
        <div class="font-medium" class:text-green-400={result.sharpe_ratio > 1} class:text-yellow-400={result.sharpe_ratio > 0 && result.sharpe_ratio <= 1} class:text-red-400={result.sharpe_ratio <= 0}>
          {formatNumber(result.sharpe_ratio)}
        </div>
      </div>
      <div class="p-2 liquid-glass-subtle rounded-lg">
        <div class="text-xs text-text-muted">Max Drawdown</div>
        <div class="font-medium text-red-400">
          {formatPercent(result.max_drawdown)}
        </div>
      </div>
    </div>

    <!-- Trade Statistics -->
    <div class="space-y-2">
      <h4 class="text-xs text-text-muted">Trade Statistics</h4>
      <div class="grid grid-cols-3 gap-2 text-xs">
        <div class="p-2 liquid-glass-subtle rounded-lg text-center">
          <div class="text-text-muted">Total</div>
          <div class="font-medium">{result.total_trades}</div>
        </div>
        <div class="p-2 liquid-glass-subtle rounded-lg text-center">
          <div class="text-text-muted">Wins</div>
          <div class="font-medium text-green-400">{result.winning_trades}</div>
        </div>
        <div class="p-2 liquid-glass-subtle rounded-lg text-center">
          <div class="text-text-muted">Losses</div>
          <div class="font-medium text-red-400">{result.losing_trades}</div>
        </div>
      </div>
    </div>

    <!-- Performance Metrics -->
    <div class="grid grid-cols-2 gap-2 text-xs">
      <div class="p-2 liquid-glass-subtle rounded-lg">
        <div class="text-text-muted">Win Rate</div>
        <div class="font-medium">{formatPercent(result.win_rate)}</div>
      </div>
      <div class="p-2 liquid-glass-subtle rounded-lg">
        <div class="text-text-muted">Profit Factor</div>
        <div class="font-medium" class:text-green-400={result.profit_factor > 1}>
          {formatNumber(result.profit_factor)}
        </div>
      </div>
      <div class="p-2 liquid-glass-subtle rounded-lg">
        <div class="text-text-muted">Avg Win</div>
        <div class="font-medium text-green-400">${formatNumber(result.avg_win)}</div>
      </div>
      <div class="p-2 liquid-glass-subtle rounded-lg">
        <div class="text-text-muted">Avg Loss</div>
        <div class="font-medium text-red-400">${formatNumber(result.avg_loss)}</div>
      </div>
    </div>
  {:else}
    <div class="text-center text-text-muted text-xs py-8">
      Run a backtest to see strategy performance
    </div>
  {/if}
</div>
