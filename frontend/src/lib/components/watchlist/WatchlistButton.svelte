<script lang="ts">
  import { watchlistStore, DEFAULT_SYMBOLS } from '$lib/stores/watchlist';

  interface Props {
    symbol: string;
    name?: string;
    size?: 'sm' | 'md' | 'lg';
  }

  let { symbol, name, size = 'md' }: Props = $props();

  // Use $derived for reactive values based on props
  let isDefault = $derived(DEFAULT_SYMBOLS.includes(symbol));
  let isCustom = $derived(watchlistStore.isCustom(symbol));

  function handleClick() {
    // Default symbols cannot be toggled
    if (isDefault) return;
    watchlistStore.toggle(symbol, name);
  }

  const sizeClasses = {
    sm: 'w-5 h-5',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
  };

  // Determine button state and styling
  let buttonClasses = $derived.by(() => {
    if (isDefault) {
      // Default symbols show a locked/fixed state
      return 'text-amber-500/60 cursor-default';
    }
    if (isCustom) {
      // Custom symbols in watchlist
      return 'text-rose-500 hover:text-rose-400';
    }
    // Not in watchlist
    return 'text-stone-500 hover:text-stone-300';
  });

  let title = $derived.by(() => {
    if (isDefault) {
      return 'Standard-Rohstoff (immer in Watchlist)';
    }
    if (isCustom) {
      return 'Aus Watchlist entfernen';
    }
    return 'Zur Watchlist hinzufügen';
  });
</script>

<button
  type="button"
  class="p-1.5 rounded-lg transition-all duration-200 {buttonClasses}"
  onclick={handleClick}
  title={title}
  disabled={isDefault}
>
  {#if isDefault}
    <!-- Star icon for default symbols -->
    <svg
      class="{sizeClasses[size]}"
      viewBox="0 0 24 24"
      fill="currentColor"
      stroke="currentColor"
      stroke-width="1"
    >
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
    </svg>
  {:else}
    <!-- Heart icon for custom symbols -->
    <svg
      class="{sizeClasses[size]} transition-transform {isCustom ? 'scale-110' : 'scale-100'}"
      viewBox="0 0 24 24"
      fill={isCustom ? 'currentColor' : 'none'}
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
    </svg>
  {/if}
</button>
