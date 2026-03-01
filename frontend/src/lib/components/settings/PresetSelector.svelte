<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  export let currentPreset: string | null;

  const dispatch = createEventDispatcher<{ select: string }>();

  const presets = [
    { value: 'default', label: 'Standard' },
    { value: 'sensitive', label: 'Sensitiv' },
    { value: 'conservative', label: 'Konservativ' },
    { value: 'trending', label: 'Trending' },
    { value: 'mean_reverting', label: 'Mean-Reverting' },
  ];

  function handleSelect(event: Event) {
    const target = event.target as HTMLSelectElement;
    dispatch('select', target.value);
  }
</script>

<div class="preset-selector">
  <label for="preset-select">Preset:</label>
  <select
    id="preset-select"
    value={currentPreset || ''}
    on:change={handleSelect}
  >
    <option value="" disabled>Benutzerdefiniert</option>
    {#each presets as preset}
      <option value={preset.value}>{preset.label}</option>
    {/each}
  </select>
</div>

<style>
  .preset-selector {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  label {
    font-size: 0.75rem;
    color: var(--color-text-muted);
  }

  select {
    padding: 0.25rem 0.5rem;
    font-size: 0.75rem;
    background: var(--color-bg-tertiary);
    border: 1px solid var(--color-bg-tertiary);
    border-radius: 4px;
    color: var(--color-text-primary);
    cursor: pointer;
  }

  select:hover {
    border-color: var(--color-wave-impulse);
  }

  select:focus {
    outline: none;
    border-color: var(--color-wave-impulse);
  }
</style>
