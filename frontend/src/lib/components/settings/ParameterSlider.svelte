<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  export let label: string;
  export let description: string = '';
  export let value: number;
  export let min: number;
  export let max: number;
  export let step: number;
  export let unit: string = '';
  export let disabled: boolean = false;

  const dispatch = createEventDispatcher<{ change: number }>();

  function handleInput(event: Event) {
    const target = event.target as HTMLInputElement;
    const newValue = parseFloat(target.value);
    dispatch('change', newValue);
  }

  function formatValue(val: number): string {
    if (step >= 1) {
      return val.toString();
    }
    const decimals = step.toString().split('.')[1]?.length || 2;
    return val.toFixed(decimals);
  }
</script>

<div class="parameter-slider" class:disabled>
  <div class="header">
    <label class="label">{label}</label>
    <span class="value">
      {formatValue(value)}{unit ? ` ${unit}` : ''}
    </span>
  </div>

  <input
    type="range"
    {min}
    {max}
    {step}
    {value}
    {disabled}
    on:input={handleInput}
    class="slider"
  />

  {#if description}
    <p class="description">{description}</p>
  {/if}
</div>

<style>
  .parameter-slider {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    padding: 0.5rem 0;
  }

  .parameter-slider.disabled {
    opacity: 0.5;
    pointer-events: none;
  }

  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .label {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--color-text-primary);
  }

  .value {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--color-accent);
    font-variant-numeric: tabular-nums;
  }

  .slider {
    width: 100%;
    height: 6px;
    border-radius: 3px;
    background: var(--color-bg-tertiary);
    outline: none;
    -webkit-appearance: none;
    appearance: none;
    cursor: pointer;
  }

  .slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: var(--color-accent);
    cursor: pointer;
    transition: transform 0.15s ease;
  }

  .slider::-webkit-slider-thumb:hover {
    transform: scale(1.15);
  }

  .slider::-moz-range-thumb {
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: var(--color-accent);
    cursor: pointer;
    border: none;
    transition: transform 0.15s ease;
  }

  .slider::-moz-range-thumb:hover {
    transform: scale(1.15);
  }

  .description {
    font-size: 0.75rem;
    color: var(--color-text-muted);
    margin: 0;
    line-height: 1.4;
  }
</style>
