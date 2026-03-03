<script lang="ts">
  import { watchlistStore, isInWatchlist } from '$lib/stores/watchlist';

  interface Props {
    symbol: string;
    name?: string;
    size?: 'sm' | 'md' | 'lg';
  }

  let { symbol, name, size = 'md' }: Props = $props();

  const inWatchlist = isInWatchlist(symbol);

  function handleClick() {
    watchlistStore.toggle(symbol, name);
  }

  const sizeClasses = {
    sm: 'w-5 h-5',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
  };
</script>

<button
  type="button"
  class="p-1.5 rounded-lg transition-all duration-200 {$inWatchlist ? 'text-rose-500 hover:text-rose-400' : 'text-stone-500 hover:text-stone-300'}"
  onclick={handleClick}
  title={$inWatchlist ? 'Aus Watchlist entfernen' : 'Zur Watchlist hinzufuegen'}
>
  <svg
    class="{sizeClasses[size]} transition-transform {$inWatchlist ? 'scale-110' : 'scale-100'}"
    viewBox="0 0 24 24"
    fill={$inWatchlist ? 'currentColor' : 'none'}
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
  >
    <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
  </svg>
</button>
