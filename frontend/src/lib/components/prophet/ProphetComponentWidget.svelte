<script lang="ts">
  import type { ProphetComponentSeries } from '$lib/types';

  let {
    components,
    activeWidget,
    onClose,
  }: {
    components: ProphetComponentSeries | null;
    activeWidget: 'trend' | 'weekly' | 'monthly' | 'yearly' | null;
    onClose: () => void;
  } = $props();

  // Widget position state
  let isDragging = $state(false);
  let position = $state({ x: 20, y: 80 });
  let dragStart = $state({ x: 0, y: 0 });

  function handleMouseDown(e: MouseEvent) {
    isDragging = true;
    dragStart = {
      x: e.clientX - position.x,
      y: e.clientY - position.y,
    };
  }

  function handleMouseMove(e: MouseEvent) {
    if (!isDragging) return;
    position = {
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y,
    };
  }

  function handleMouseUp() {
    isDragging = false;
  }

  // Get data for active widget
  function getWidgetData() {
    if (!components || !activeWidget) return null;
    switch (activeWidget) {
      case 'trend': return components.trend;
      case 'weekly': return components.weekly;
      case 'monthly': return components.monthly;
      case 'yearly': return components.yearly;
      default: return null;
    }
  }

  const widgetConfig = {
    trend: { label: 'Trend', color: '#1f77b4' },
    weekly: { label: 'Wöchentlich', color: '#ff7f0e' },
    monthly: { label: 'Monatlich', color: '#2ca02c' },
    yearly: { label: 'Jährlich', color: '#d62728' },
  };
</script>

<svelte:window
  on:mousemove={handleMouseMove}
  on:mouseup={handleMouseUp}
/>

{#if activeWidget && components}
  {@const data = getWidgetData()}
  {@const config = widgetConfig[activeWidget]}

  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="fixed z-50 w-80 liquid-glass rounded-2xl shadow-2xl border border-stone-700/50 overflow-hidden"
    style="left: {position.x}px; top: {position.y}px;"
  >
    <!-- Header (draggable) -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
      class="p-3 flex items-center justify-between bg-stone-800/50 cursor-move select-none"
      onmousedown={handleMouseDown}
    >
      <div class="flex items-center gap-2">
        <div class="w-3 h-3 rounded-full" style="background-color: {config.color}"></div>
        <span class="text-sm font-medium text-text-primary">{config.label}</span>
      </div>
      <button
        class="w-6 h-6 flex items-center justify-center rounded-full hover:bg-stone-700/50 transition-all text-text-muted hover:text-text-primary"
        onclick={onClose}
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <!-- Content -->
    <div class="p-4 max-h-60 overflow-y-auto">
      {#if data && data.length > 0}
        {@const values = data.map(d => d.value)}
        {@const minVal = Math.min(...values)}
        {@const maxVal = Math.max(...values)}
        {@const range = maxVal - minVal || 1}

        <!-- Simple sparkline visualization -->
        <div class="h-24 flex items-end gap-px">
          {#each data.slice(-50) as point, i}
            {@const height = ((point.value - minVal) / range) * 100}
            <div
              class="flex-1 rounded-t transition-all hover:opacity-80"
              style="height: {height}%; background-color: {config.color}; min-width: 2px;"
              title="{point.ds}: {point.value.toFixed(2)}"
            ></div>
          {/each}
        </div>

        <!-- Stats -->
        <div class="mt-4 grid grid-cols-3 gap-2 text-xs">
          <div class="text-center">
            <div class="text-text-muted">Min</div>
            <div class="font-medium text-text-primary">{minVal.toFixed(2)}</div>
          </div>
          <div class="text-center">
            <div class="text-text-muted">Max</div>
            <div class="font-medium text-text-primary">{maxVal.toFixed(2)}</div>
          </div>
          <div class="text-center">
            <div class="text-text-muted">Aktuell</div>
            <div class="font-medium text-text-primary">{data[data.length - 1]?.value.toFixed(2) ?? '-'}</div>
          </div>
        </div>
      {:else}
        <div class="text-center py-4 text-text-muted text-sm">
          Keine Daten verfügbar
        </div>
      {/if}
    </div>
  </div>
{/if}
