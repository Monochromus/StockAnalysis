<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { Input, Button } from '$lib/components/ui';
  import { searchTickers } from '$lib/api/analysis';
  import type { TickerSearchResult } from '$lib/types';

  const dispatch = createEventDispatcher<{ select: string }>();

  let query = '';
  let results: TickerSearchResult[] = [];
  let loading = false;
  let showDropdown = false;
  let selectedIndex = -1;
  let debounceTimeout: ReturnType<typeof setTimeout>;

  async function handleInput() {
    clearTimeout(debounceTimeout);

    if (query.length < 1) {
      results = [];
      showDropdown = false;
      return;
    }

    debounceTimeout = setTimeout(async () => {
      loading = true;
      try {
        const response = await searchTickers(query);
        results = response.results;
        showDropdown = results.length > 0;
      } catch {
        results = [];
      } finally {
        loading = false;
      }
    }, 300);
  }

  function handleKeydown(event: KeyboardEvent) {
    if (!showDropdown) return;

    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault();
        selectedIndex = Math.min(selectedIndex + 1, results.length - 1);
        break;
      case 'ArrowUp':
        event.preventDefault();
        selectedIndex = Math.max(selectedIndex - 1, 0);
        break;
      case 'Enter':
        event.preventDefault();
        if (selectedIndex >= 0 && results[selectedIndex]) {
          selectTicker(results[selectedIndex].symbol);
        } else if (query.length > 0) {
          selectTicker(query.toUpperCase());
        }
        break;
      case 'Escape':
        showDropdown = false;
        selectedIndex = -1;
        break;
    }
  }

  function selectTicker(symbol: string) {
    query = symbol;
    showDropdown = false;
    selectedIndex = -1;
    dispatch('select', symbol);
  }

  function handleBlur() {
    // Delay to allow click on dropdown item
    setTimeout(() => {
      showDropdown = false;
    }, 200);
  }

  function handleSubmit() {
    if (query.length > 0) {
      selectTicker(query.toUpperCase());
    }
  }
</script>

<div class="relative">
  <form on:submit|preventDefault={handleSubmit} class="flex gap-2">
    <div class="relative flex-1">
      <Input
        type="search"
        placeholder="Search ticker (e.g., AAPL)"
        bind:value={query}
        on:input={handleInput}
        on:keydown={handleKeydown}
        on:focus={() => (showDropdown = results.length > 0)}
        on:blur={handleBlur}
      />

      {#if loading}
        <div class="absolute right-3 top-1/2 -translate-y-1/2">
          <svg class="animate-spin h-5 w-5 text-stone-500" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        </div>
      {/if}
    </div>

    <Button type="submit" variant="primary">Analyze</Button>
  </form>

  {#if showDropdown && results.length > 0}
    <ul class="absolute z-50 w-full mt-2 liquid-glass-intense rounded-xl shadow-2xl overflow-hidden animate-liquid-fade-in">
      {#each results as result, index}
        <li>
          <button
            type="button"
            class="w-full px-4 py-3 text-left transition-all flex items-center justify-between {index === selectedIndex ? 'bg-amber-500/15 text-amber-50' : 'hover:bg-stone-700/50'}"
            on:click={() => selectTicker(result.symbol)}
          >
            <div>
              <span class="font-semibold text-stone-50">{result.symbol}</span>
              <span class="text-stone-400 ml-2">{result.name}</span>
            </div>
            {#if result.exchange}
              <span class="text-xs text-stone-500">{result.exchange}</span>
            {/if}
          </button>
        </li>
      {/each}
    </ul>
  {/if}
</div>
