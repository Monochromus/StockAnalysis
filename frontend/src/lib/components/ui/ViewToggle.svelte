<script lang="ts">
  import type { ViewMode } from '$lib/types';

  interface Props {
    viewMode: ViewMode;
    onToggle: () => void;
    onSetMode?: (mode: ViewMode) => void;
  }

  let { viewMode, onToggle, onSetMode }: Props = $props();

  function setMode(mode: ViewMode) {
    if (onSetMode) {
      onSetMode(mode);
    } else if (viewMode !== mode) {
      // Fallback: cycle through until we hit the target
      onToggle();
    }
  }
</script>

<div class="flex items-center gap-1 bg-stone-800/50 rounded-lg p-1">
  <button
    type="button"
    class="px-3 py-1.5 rounded-md text-sm font-medium transition-all duration-200 flex items-center gap-2
      {viewMode === 'chart'
        ? 'bg-amber-500/20 text-amber-400'
        : 'text-stone-400 hover:text-stone-300 hover:bg-stone-700/50'}"
    onclick={() => setMode('chart')}
  >
    <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <line x1="18" y1="20" x2="18" y2="10" />
      <line x1="12" y1="20" x2="12" y2="4" />
      <line x1="6" y1="20" x2="6" y2="14" />
    </svg>
    Chart
  </button>

  <button
    type="button"
    class="px-3 py-1.5 rounded-md text-sm font-medium transition-all duration-200 flex items-center gap-2
      {viewMode === 'calendar'
        ? 'bg-amber-500/20 text-amber-400'
        : 'text-stone-400 hover:text-stone-300 hover:bg-stone-700/50'}"
    onclick={() => setMode('calendar')}
  >
    <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
    </svg>
    Kalender
  </button>

  <button
    type="button"
    class="px-3 py-1.5 rounded-md text-sm font-medium transition-all duration-200 flex items-center gap-2
      {viewMode === 'news'
        ? 'bg-amber-500/20 text-amber-400'
        : 'text-stone-400 hover:text-stone-300 hover:bg-stone-700/50'}"
    onclick={() => setMode('news')}
  >
    <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
    </svg>
    News
  </button>
</div>
