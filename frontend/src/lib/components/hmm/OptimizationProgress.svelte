<script lang="ts">
  import type { OptimizationProgress, OptimizationResult } from '$lib/types';

  let {
    progress,
    result,
    onCancel,
  }: {
    progress: OptimizationProgress | null;
    result: OptimizationResult | null;
    onCancel: () => void;
  } = $props();

  // Calculate progress percentage
  let progressPercent = $derived(
    progress && progress.total_trials > 0
      ? Math.round((progress.current_trial / progress.total_trials) * 100)
      : 0
  );

  // Format elapsed time
  let elapsedTime = $derived(() => {
    if (!progress) return '0s';
    const seconds = Math.floor(progress.elapsed_seconds);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  });

  // Determine if optimization is complete
  let isComplete = $derived(
    progress?.status === 'completed' ||
    progress?.status === 'failed' ||
    progress?.status === 'cancelled'
  );

  // Status color
  let statusColor = $derived(() => {
    if (!progress) return 'text-text-muted';
    switch (progress.status) {
      case 'completed':
        return 'text-green-400';
      case 'failed':
        return 'text-red-400';
      case 'cancelled':
        return 'text-amber-400';
      default:
        return 'text-blue-400';
    }
  });
</script>

<div class="p-3 rounded-lg bg-stone-800/50 border border-stone-700/50 space-y-3">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div class="flex items-center gap-2">
      {#if !isComplete}
        <svg class="w-4 h-4 text-amber-400 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <span class="text-xs font-medium text-amber-400 uppercase tracking-wide">Optimierung läuft</span>
      {:else}
        <svg class="w-4 h-4 {statusColor()}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          {#if progress?.status === 'completed'}
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          {:else if progress?.status === 'failed'}
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          {:else}
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          {/if}
        </svg>
        <span class="text-xs font-medium {statusColor()} uppercase tracking-wide">
          {#if progress?.status === 'completed'}
            Abgeschlossen
          {:else if progress?.status === 'failed'}
            Fehlgeschlagen
          {:else}
            Abgebrochen
          {/if}
        </span>
      {/if}
    </div>
    {#if !isComplete}
      <button
        class="text-xs text-text-muted hover:text-red-400 transition-colors"
        onclick={onCancel}
      >
        Abbrechen
      </button>
    {/if}
  </div>

  <!-- Progress bar -->
  {#if progress}
    <div class="space-y-1">
      <div class="flex justify-between text-xs text-text-muted">
        <span>Trial {progress.current_trial} / {progress.total_trials}</span>
        <span>{progressPercent}%</span>
      </div>
      <div class="h-2 bg-stone-700 rounded-full overflow-hidden">
        <div
          class="h-full transition-all duration-300 ease-out
            {isComplete && progress.status === 'completed'
              ? 'bg-green-500'
              : isComplete && progress.status === 'failed'
                ? 'bg-red-500'
                : 'bg-gradient-to-r from-amber-500 to-orange-500'
            }"
          style="width: {progressPercent}%"
        ></div>
      </div>
    </div>

    <!-- Status message -->
    <p class="text-xs text-text-muted">{progress.message}</p>

    <!-- Best result so far -->
    {#if progress.best_alpha !== 0 || (result && result.success)}
      <div class="pt-2 border-t border-stone-700/50">
        <div class="grid grid-cols-2 gap-2 text-xs">
          <div>
            <span class="text-text-muted">Best Alpha:</span>
            <span class="ml-1 font-mono {(result?.best_alpha ?? progress.best_alpha) >= 0 ? 'text-green-400' : 'text-red-400'}">
              {((result?.best_alpha ?? progress.best_alpha) >= 0 ? '+' : '')}{(result?.best_alpha ?? progress.best_alpha).toFixed(2)}%
            </span>
          </div>
          <div>
            <span class="text-text-muted">Zeit:</span>
            <span class="ml-1 font-mono text-text-primary">{elapsedTime()}</span>
          </div>
        </div>
      </div>
    {/if}

    <!-- Final result metrics -->
    {#if result && result.success}
      <div class="pt-2 border-t border-stone-700/50 space-y-2">
        <div class="text-xs font-medium text-green-400">Beste Parameter gefunden:</div>
        <div class="grid grid-cols-2 gap-2 text-xs">
          <div>
            <span class="text-text-muted">Sharpe:</span>
            <span class="ml-1 font-mono text-text-primary">{result.best_sharpe.toFixed(2)}</span>
          </div>
          <div>
            <span class="text-text-muted">Return:</span>
            <span class="ml-1 font-mono {result.best_total_return >= 0 ? 'text-green-400' : 'text-red-400'}">
              {result.best_total_return >= 0 ? '+' : ''}{result.best_total_return.toFixed(2)}%
            </span>
          </div>
          <div>
            <span class="text-text-muted">Max DD:</span>
            <span class="ml-1 font-mono text-red-400">{result.best_max_drawdown.toFixed(2)}%</span>
          </div>
          <div>
            <span class="text-text-muted">Trials:</span>
            <span class="ml-1 font-mono text-text-primary">{result.total_trials_evaluated}</span>
          </div>
        </div>
        <p class="text-xs text-green-400/80 bg-green-500/10 rounded p-2">
          Parameter wurden automatisch angewendet.
        </p>
      </div>
    {/if}

    <!-- Error message -->
    {#if result && !result.success && result.error_message}
      <div class="pt-2 border-t border-stone-700/50">
        <p class="text-xs text-red-400 bg-red-500/10 rounded p-2">
          {result.error_message}
        </p>
      </div>
    {/if}
  {/if}
</div>
