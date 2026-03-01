<script lang="ts">
  import { debugStore } from '$lib/stores/debug';
  import { tickerStore } from '$lib/stores/ticker';
  import { analysisStore } from '$lib/stores/analysis';
  import { onMount } from 'svelte';

  let logsContainer: HTMLDivElement;
  let activeTab: 'logs' | 'state' = 'logs';
  let autoScroll = true;
  let lastLogCount = 0;

  // Only auto-scroll if user hasn't scrolled up manually
  function handleScroll() {
    if (!logsContainer) return;
    const isAtBottom = logsContainer.scrollHeight - logsContainer.scrollTop - logsContainer.clientHeight < 50;
    autoScroll = isAtBottom;
  }

  // Auto-scroll to bottom when new logs arrive (only if autoScroll is enabled)
  $: if (logsContainer && $debugStore.logs.length > lastLogCount && autoScroll) {
    lastLogCount = $debugStore.logs.length;
    setTimeout(() => {
      if (autoScroll && logsContainer) {
        logsContainer.scrollTop = logsContainer.scrollHeight;
      }
    }, 10);
  }

  function formatData(data: any): string {
    if (data === undefined) return '';
    try {
      return JSON.stringify(data, null, 2);
    } catch {
      return String(data);
    }
  }

  function getLogColor(message: string): string {
    if (message.includes('ERROR')) return 'text-red-400';
    if (message.includes('WARNING')) return 'text-amber-400';
    if (message.includes('SUCCESS') || message.includes('successfully')) return 'text-emerald-400';
    return 'text-slate-300';
  }
</script>

{#if $debugStore.isOpen}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" on:click={() => debugStore.close()}>
    <div
      class="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-[90vw] max-w-4xl h-[80vh] flex flex-col"
      on:click|stopPropagation
    >
      <!-- Header -->
      <div class="flex items-center justify-between px-4 py-3 border-b border-slate-700">
        <h2 class="text-lg font-semibold text-slate-100">Debug Panel</h2>
        <div class="flex items-center gap-4">
          <!-- Tabs -->
          <div class="flex gap-1 bg-slate-800 rounded-lg p-1">
            <button
              class="px-3 py-1 rounded-md text-sm transition-colors {activeTab === 'logs'
                ? 'bg-emerald-600 text-white'
                : 'text-slate-400 hover:text-slate-200'}"
              on:click={() => (activeTab = 'logs')}
            >
              Logs ({$debugStore.logs.length})
            </button>
            <button
              class="px-3 py-1 rounded-md text-sm transition-colors {activeTab === 'state'
                ? 'bg-emerald-600 text-white'
                : 'text-slate-400 hover:text-slate-200'}"
              on:click={() => (activeTab = 'state')}
            >
              State
            </button>
          </div>
          <button
            class="px-3 py-1 text-sm text-slate-400 hover:text-slate-200 border border-slate-600 rounded-md"
            on:click={() => debugStore.clear()}
          >
            Clear Logs
          </button>
          <button
            class="text-slate-400 hover:text-slate-200 text-xl leading-none"
            on:click={() => debugStore.close()}
          >
            &times;
          </button>
        </div>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-hidden">
        {#if activeTab === 'logs'}
          <!-- Logs Tab -->
          <div bind:this={logsContainer} on:scroll={handleScroll} class="h-full overflow-auto p-4 font-mono text-xs">
            {#if $debugStore.logs.length === 0}
              <p class="text-slate-500 text-center py-8">No logs yet. Interact with the app to see debug output.</p>
            {:else}
              {#each $debugStore.logs as log, i}
                <div class="mb-2 pb-2 border-b border-slate-800">
                  <div class="flex items-start gap-2">
                    <span class="text-slate-500 shrink-0">{log.timestamp.split('T')[1].split('.')[0]}</span>
                    <span class="text-cyan-400 shrink-0">[{log.source}]</span>
                    <span class={getLogColor(log.message)}>{log.message}</span>
                  </div>
                  {#if log.data !== undefined}
                    <pre class="mt-1 ml-20 text-slate-400 bg-slate-800/50 p-2 rounded overflow-x-auto">{formatData(log.data)}</pre>
                  {/if}
                </div>
              {/each}
            {/if}
          </div>
        {:else}
          <!-- State Tab -->
          <div class="h-full overflow-auto p-4 font-mono text-xs">
            <div class="space-y-4">
              <!-- Ticker Store State -->
              <div>
                <h3 class="text-emerald-400 font-semibold mb-2">Ticker Store</h3>
                <pre class="bg-slate-800/50 p-3 rounded overflow-x-auto text-slate-300">{JSON.stringify({
                  symbol: $tickerStore.symbol,
                  loading: $tickerStore.loading,
                  error: $tickerStore.error,
                  candleCount: $tickerStore.candles.length,
                  firstCandle: $tickerStore.candles[0],
                  lastCandle: $tickerStore.candles[$tickerStore.candles.length - 1]
                }, null, 2)}</pre>
              </div>

              <!-- Analysis Store State -->
              <div>
                <h3 class="text-emerald-400 font-semibold mb-2">Analysis Store</h3>
                <pre class="bg-slate-800/50 p-3 rounded overflow-x-auto text-slate-300">{JSON.stringify({
                  loading: $analysisStore.loading,
                  error: $analysisStore.error,
                  hasResult: !!$analysisStore.result,
                  hasPrimaryCount: !!$analysisStore.result?.primary_count,
                  waveCount: $analysisStore.result?.primary_count?.waves?.length ?? 0,
                  alternativeCountsCount: $analysisStore.result?.alternative_counts?.length ?? 0
                }, null, 2)}</pre>
              </div>

              <!-- Raw Candles Sample -->
              {#if $tickerStore.candles.length > 0}
                <div>
                  <h3 class="text-emerald-400 font-semibold mb-2">First 5 Candles (Raw)</h3>
                  <pre class="bg-slate-800/50 p-3 rounded overflow-x-auto text-slate-300">{JSON.stringify($tickerStore.candles.slice(0, 5), null, 2)}</pre>
                </div>
              {/if}

              <!-- Primary Wave Count -->
              {#if $analysisStore.result?.primary_count}
                <div>
                  <h3 class="text-emerald-400 font-semibold mb-2">Primary Wave Count</h3>
                  <pre class="bg-slate-800/50 p-3 rounded overflow-x-auto text-slate-300">{JSON.stringify($analysisStore.result.primary_count, null, 2)}</pre>
                </div>
              {/if}
            </div>
          </div>
        {/if}
      </div>

      <!-- Footer -->
      <div class="px-4 py-2 border-t border-slate-700 text-xs text-slate-500 flex items-center justify-between">
        <span>Press <kbd class="px-1.5 py-0.5 bg-slate-800 rounded">Ctrl+Shift+D</kbd> or click the bug icon to toggle this panel</span>
        <button
          class="px-2 py-1 rounded text-xs transition-colors {autoScroll ? 'bg-emerald-600 text-white' : 'bg-slate-700 text-slate-400 hover:bg-slate-600'}"
          on:click={() => {
            autoScroll = !autoScroll;
            if (autoScroll && logsContainer) {
              logsContainer.scrollTop = logsContainer.scrollHeight;
            }
          }}
        >
          Auto-scroll: {autoScroll ? 'ON' : 'OFF'}
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- Floating Debug Button -->
<button
  class="fixed bottom-4 right-4 z-40 w-12 h-12 rounded-full bg-slate-800 border border-slate-700 text-slate-400 hover:text-emerald-400 hover:border-emerald-500 shadow-lg flex items-center justify-center transition-colors"
  on:click={() => debugStore.toggle()}
  title="Toggle Debug Panel (Ctrl+Shift+D)"
>
  <svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
  </svg>
</button>

<svelte:window
  on:keydown={(e) => {
    if (e.ctrlKey && e.shiftKey && e.key === 'D') {
      e.preventDefault();
      debugStore.toggle();
    }
  }}
/>
