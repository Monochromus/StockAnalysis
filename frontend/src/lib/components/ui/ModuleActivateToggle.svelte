<script lang="ts">
  import type { ModuleId } from '$lib/stores/modules';

  let {
    moduleId,
    isActive,
    onToggle,
    color = 'amber',
  }: {
    moduleId: ModuleId;
    isActive: boolean;
    onToggle: () => void;
    color?: 'amber' | 'emerald' | 'blue';
  } = $props();

  const colorClasses = {
    amber: {
      active: 'bg-amber-500/20 border-amber-500/50 text-amber-400',
      dot: 'bg-amber-400',
      hoverActive: 'hover:bg-amber-500/30',
    },
    emerald: {
      active: 'bg-emerald-500/20 border-emerald-500/50 text-emerald-400',
      dot: 'bg-emerald-400',
      hoverActive: 'hover:bg-emerald-500/30',
    },
    blue: {
      active: 'bg-blue-500/20 border-blue-500/50 text-blue-400',
      dot: 'bg-blue-400',
      hoverActive: 'hover:bg-blue-500/30',
    },
  };

  const colors = $derived(colorClasses[color]);
</script>

<button
  class="flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-lg border transition-all {isActive
    ? `${colors.active} ${colors.hoverActive}`
    : 'bg-stone-800/50 border-stone-700/50 text-stone-400 hover:bg-stone-700/50 hover:text-stone-300'}"
  onclick={onToggle}
>
  {#if isActive}
    <span class="relative flex h-2 w-2">
      <span class="animate-ping absolute inline-flex h-full w-full rounded-full {colors.dot} opacity-75"></span>
      <span class="relative inline-flex rounded-full h-2 w-2 {colors.dot}"></span>
    </span>
    <span>Aktiv</span>
  {:else}
    <span class="w-2 h-2 rounded-full bg-stone-600"></span>
    <span>Deaktiviert</span>
  {/if}
</button>
