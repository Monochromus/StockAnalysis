<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { modulesStore, MODULE_CONFIGS, MODULE_ORDER, type ModuleId } from '$lib/stores/modules';
  import { uiStore } from '$lib/stores/ui';
  import type { ProviderMetadata } from '$lib/types';

  export let symbol: string = '';
  export let period: string = '1y';
  export let interval: string = '1d';
  export let candleCount: number = 0;
  export let loading: boolean = false;
  export let hasAnalysis: boolean = false;
  export let provider: ProviderMetadata | null = null;

  const dispatch = createEventDispatcher<{
    periodChange: string;
    intervalChange: string;
    resetAnalysis: void;
    openSettings: void;
    sidebarSelect: { moduleId: ModuleId };
  }>();

  const periods = [
    { value: '1mo', label: '1M' },
    { value: '3mo', label: '3M' },
    { value: '6mo', label: '6M' },
    { value: '1y', label: '1Y' },
    { value: '2y', label: '2Y' },
    { value: '5y', label: '5Y' },
  ];

  const intervals = [
    { value: '1h', label: '1H' },
    { value: '4h', label: '4H' },
    { value: '1d', label: '1D' },
    { value: '1wk', label: '1W' },
    { value: '1mo', label: '1Mo' },
  ];

  function handlePeriodChange(newPeriod: string) {
    if (newPeriod !== period && !loading) {
      dispatch('periodChange', newPeriod);
    }
  }

  function handleIntervalChange(newInterval: string) {
    if (newInterval !== interval && !loading) {
      dispatch('intervalChange', newInterval);
    }
  }

  function handleResetAnalysis() {
    dispatch('resetAnalysis');
  }

  function handleOpenSettings() {
    dispatch('openSettings');
  }

  function handleSidebarSelect(moduleId: ModuleId) {
    uiStore.toggleActiveSidebar(moduleId);
    dispatch('sidebarSelect', { moduleId });
  }

  // Button styling based on sidebar selection (not module active state)
  function getSidebarButtonClass(moduleId: ModuleId, isSidebarActive: boolean): string {
    if (!isSidebarActive) return 'text-stone-400 hover:text-stone-200 hover:bg-stone-700/50';

    const color = MODULE_CONFIGS[moduleId].color;
    switch (color) {
      case 'amber':
        return 'liquid-glass-subtle bg-amber-600/80 text-white border-amber-500/30';
      case 'emerald':
        return 'liquid-glass-subtle bg-emerald-600/80 text-white border-emerald-500/30';
      case 'blue':
        return 'liquid-glass-subtle bg-blue-600/80 text-white border-blue-500/30';
      case 'purple':
        return 'liquid-glass-subtle bg-purple-600/80 text-white border-purple-500/30';
      default:
        return 'liquid-glass-subtle bg-stone-600/80 text-white border-stone-500/30';
    }
  }

  // Small indicator dot color for module active state
  function getModuleActiveDotClass(moduleId: ModuleId): string {
    const color = MODULE_CONFIGS[moduleId].color;
    switch (color) {
      case 'amber':
        return 'bg-amber-400';
      case 'emerald':
        return 'bg-emerald-400';
      case 'blue':
        return 'bg-blue-400';
      case 'purple':
        return 'bg-purple-400';
      default:
        return 'bg-stone-400';
    }
  }
</script>

<div class="flex items-center justify-between px-4 py-2">
  <!-- Left: Symbol and Info -->
  <div class="flex items-center gap-4">
    {#if symbol}
      <span class="font-semibold text-stone-50">{symbol}</span>
      <span class="text-xs text-stone-500">
        {candleCount} candles
      </span>
      {#if provider}
        <span class="flex items-center gap-1.5 text-xs text-stone-500 border-l border-stone-700/40 pl-4">
          <span class="w-2 h-2 rounded-full {provider.from_cache ? 'bg-amber-500' : 'bg-emerald-500'}"></span>
          {provider.provider_display_name}
          {#if provider.from_cache}
            <span class="text-stone-600">(cache)</span>
          {/if}
        </span>
      {/if}
    {:else}
      <span class="text-stone-500">No ticker selected</span>
    {/if}
  </div>

  <!-- Center: Period Selector -->
  <div class="flex items-center gap-1">
    <span class="text-xs text-stone-500 mr-2">Period:</span>
    {#each periods as p}
      <button
        class="px-2.5 py-1 text-xs rounded-lg transition-all {period === p.value
          ? 'liquid-glass-subtle bg-amber-600/80 text-white border-amber-500/30'
          : 'text-stone-400 hover:text-stone-200 hover:bg-stone-700/50'}"
        disabled={loading}
        on:click={() => handlePeriodChange(p.value)}
      >
        {p.label}
      </button>
    {/each}
  </div>

  <!-- Right: Interval, Modules, and Actions -->
  <div class="flex items-center gap-4">
    <!-- Interval Selector -->
    <div class="flex items-center gap-1">
      <span class="text-xs text-stone-500 mr-2">Interval:</span>
      {#each intervals as i}
        <button
          class="px-2.5 py-1 text-xs rounded-lg transition-all {interval === i.value
            ? 'liquid-glass-subtle bg-amber-600/80 text-white border-amber-500/30'
            : 'text-stone-400 hover:text-stone-200 hover:bg-stone-700/50'}"
          disabled={loading}
          on:click={() => handleIntervalChange(i.value)}
        >
          {i.label}
        </button>
      {/each}
    </div>

    <!-- Analysis Modules -->
    <div class="flex items-center gap-1 border-l border-stone-700/40 pl-4">
      <span class="text-xs text-stone-500 mr-2">Modules:</span>
      {#each MODULE_ORDER as moduleId}
        {@const config = MODULE_CONFIGS[moduleId]}
        {@const isModuleActive = $modulesStore[moduleId]}
        {@const isSidebarActive = $uiStore.activeSidebar === moduleId}
        <button
          class="px-3 py-1 text-xs rounded-lg transition-all flex items-center gap-1.5 {getSidebarButtonClass(moduleId, isSidebarActive)}"
          disabled={loading}
          on:click={() => handleSidebarSelect(moduleId)}
          title={config.description}
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d={config.icon}/>
          </svg>
          {config.shortName}
          {#if isModuleActive}
            <span class="w-1.5 h-1.5 rounded-full {getModuleActiveDotClass(moduleId)}"></span>
          {/if}
        </button>
      {/each}
    </div>

    <!-- Reset Analysis Button (only for Elliott Waves) -->
    {#if hasAnalysis && $modulesStore.elliottWaves}
      <div class="flex items-center gap-1 border-l border-stone-700/40 pl-4">
        <button
          class="px-3 py-1 text-xs rounded-lg transition-all flex items-center gap-1.5 text-amber-400 hover:text-amber-300 hover:bg-stone-700/50"
          disabled={loading}
          on:click={handleResetAnalysis}
          title="Reset wave analysis"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
            <path d="M3 3v5h5"/>
          </svg>
          Reset
        </button>
      </div>
    {/if}

    <!-- Settings Button -->
    <div class="flex items-center border-l border-stone-700/40 pl-4">
      <button
        class="px-3 py-1 text-xs rounded-lg transition-all flex items-center gap-1.5 text-stone-400 hover:text-stone-200 hover:bg-stone-700/50"
        disabled={loading}
        on:click={handleOpenSettings}
        title="Settings"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>
          <circle cx="12" cy="12" r="3"/>
        </svg>
      </button>
    </div>
  </div>
</div>
