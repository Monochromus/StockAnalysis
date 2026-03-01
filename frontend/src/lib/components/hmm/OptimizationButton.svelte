<script lang="ts">
  let {
    label,
    description,
    disabled = false,
    loading = false,
    onclick,
  }: {
    label: string;
    description: string;
    disabled?: boolean;
    loading?: boolean;
    onclick: () => void;
  } = $props();
</script>

<button
  class="w-full p-3 rounded-lg border border-dashed transition-all duration-200
    {disabled
      ? 'border-stone-700 bg-stone-800/30 cursor-not-allowed opacity-50'
      : 'border-amber-500/50 bg-gradient-to-r from-amber-500/10 to-orange-500/10 hover:from-amber-500/20 hover:to-orange-500/20 hover:border-amber-500/70 cursor-pointer'
    }"
  {disabled}
  {onclick}
>
  <div class="flex items-center justify-between">
    <div class="flex items-center gap-2">
      {#if loading}
        <svg class="w-4 h-4 text-amber-400 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
      {:else}
        <svg class="w-4 h-4 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
      {/if}
      <span class="text-sm font-medium text-text-primary">{label}</span>
    </div>
    <svg class="w-4 h-4 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
    </svg>
  </div>
  <p class="text-xs text-text-muted mt-1 text-left">{description}</p>
</button>
