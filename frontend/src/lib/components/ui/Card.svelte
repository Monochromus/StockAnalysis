<script lang="ts">
  export let padding: 'none' | 'sm' | 'md' | 'lg' = 'md';
  export let variant: 'glass' | 'solid' | 'subtle' = 'glass';

  const paddingClasses = {
    none: '',
    sm: 'p-3',
    md: 'p-4',
    lg: 'p-6',
  };
</script>

{#if variant === 'glass'}
  <div class="rounded-2xl liquid-glass liquid-shine {paddingClasses[padding]} transition-all duration-200 hover:border-stone-600/30">
    <slot />
  </div>
{:else if variant === 'subtle'}
  <div class="rounded-xl liquid-glass-subtle {paddingClasses[padding]} transition-all duration-200">
    <slot />
  </div>
{:else}
  <div class="bg-stone-900 rounded-2xl border border-stone-800 {paddingClasses[padding]}">
    <slot />
  </div>
{/if}
