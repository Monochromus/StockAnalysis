<script lang="ts">
  type Variant = 'success' | 'error' | 'warning' | 'info' | 'neutral';

  export let variant: Variant = 'neutral';

  const variantClasses: Record<Variant, string> = {
    success: 'bg-emerald-400/15 text-emerald-400 border-emerald-400/25',
    error: 'bg-red-400/15 text-red-400 border-red-400/25',
    warning: 'bg-amber-400/15 text-amber-400 border-amber-400/25',
    info: 'bg-amber-600/15 text-amber-500 border-amber-500/25',
    neutral: 'bg-stone-700/40 text-stone-400 border-stone-600/40',
  };
</script>

<span
  class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium tracking-wide border liquid-glass-subtle {variantClasses[variant]}"
>
  <slot />
</span>
