<script lang="ts">
  import ParameterSlider from './ParameterSlider.svelte';
  import { engineConfigStore } from '$lib/stores/engineConfig';
  import { DFA_PARAMETERS } from '$lib/types/waveEngine';

  $: config = $engineConfigStore.config.dfa;

  function handleWindowChange(event: CustomEvent<number>) {
    engineConfigStore.updateDFA({ window_size: event.detail });
  }

  function handlePolynomialChange(value: number) {
    engineConfigStore.updateDFA({ polynomial_order: value });
  }

  function handleMinSegmentChange(event: CustomEvent<number>) {
    engineConfigStore.updateDFA({ min_segment_size: event.detail });
  }

  function handleMaxSegmentRatioChange(event: CustomEvent<number>) {
    engineConfigStore.updateDFA({ max_segment_ratio: event.detail });
  }
</script>

<div class="dfa-settings">
  <ParameterSlider
    label="Fenstergröße"
    description="Anzahl der Datenpunkte für die DFA-Berechnung. Größere Fenster = stabilere Schätzungen, aber weniger reaktiv."
    value={config.window_size}
    min={50}
    max={500}
    step={10}
    unit="Kerzen"
    on:change={handleWindowChange}
  />

  <div class="polynomial-order">
    <label class="label">Polynomordnung</label>
    <div class="toggle-group">
      {#each [1, 2, 3] as order}
        <button
          type="button"
          class="toggle-btn"
          class:active={config.polynomial_order === order}
          on:click={() => handlePolynomialChange(order)}
        >
          DFA-{order}
        </button>
      {/each}
    </div>
    <p class="description">
      {#if config.polynomial_order === 1}
        Linear - Entfernt lineare Trends
      {:else if config.polynomial_order === 2}
        Quadratisch - Empfohlen für Finanzdaten
      {:else}
        Kubisch - Entfernt komplexe Trends
      {/if}
    </p>
  </div>

  <ParameterSlider
    label="Min. Segmentgröße"
    description="Minimale Größe der DFA-Segmente. Kleinere Werte = feinere Analyse."
    value={config.min_segment_size}
    min={2}
    max={10}
    step={1}
    on:change={handleMinSegmentChange}
  />

  <ParameterSlider
    label="Max. Segment-Verhältnis"
    description="Maximale Segmentgröße als Anteil der Datenlänge."
    value={config.max_segment_ratio}
    min={0.1}
    max={0.5}
    step={0.05}
    on:change={handleMaxSegmentRatioChange}
  />
</div>

<style>
  .dfa-settings {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .polynomial-order {
    padding: 0.5rem 0;
  }

  .label {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--color-text-primary);
    display: block;
    margin-bottom: 0.5rem;
  }

  .toggle-group {
    display: flex;
    gap: 0.25rem;
  }

  .toggle-btn {
    flex: 1;
    padding: 0.5rem;
    font-size: 0.75rem;
    font-weight: 500;
    background: var(--color-bg-tertiary);
    border: 1px solid var(--color-bg-tertiary);
    border-radius: 4px;
    color: var(--color-text-secondary);
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .toggle-btn:hover {
    border-color: var(--color-wave-impulse);
    color: var(--color-text-primary);
  }

  .toggle-btn.active {
    background: var(--color-wave-impulse);
    border-color: var(--color-wave-impulse);
    color: white;
  }

  .description {
    font-size: 0.75rem;
    color: var(--color-text-muted);
    margin: 0.5rem 0 0;
    line-height: 1.4;
  }
</style>
