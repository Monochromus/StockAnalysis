<script lang="ts">
  import ParameterSlider from './ParameterSlider.svelte';
  import { engineConfigStore, weightsValid } from '$lib/stores/engineConfig';

  $: config = $engineConfigStore.config.confidence_weights;
  $: total = config.w1_threshold_distance + config.w2_timeframe_consistency + config.w3_dfa_stability + config.w4_structural_validity;
  $: isValid = $weightsValid;

  function handleChange(key: string, value: number) {
    engineConfigStore.updateConfidenceWeights({ [key]: value });
  }
</script>

<div class="confidence-settings">
  <div class="total-indicator" class:invalid={!isValid}>
    <span class="total-label">Summe der Gewichte:</span>
    <span class="total-value">{total.toFixed(2)}</span>
    {#if !isValid}
      <span class="warning">Sollte 1.0 sein</span>
    {/if}
  </div>

  <div class="weights-grid">
    <div class="weight-item">
      <div class="weight-bar" style="--weight: {config.w1_threshold_distance}; --color: #10b981;"></div>
      <ParameterSlider
        label="Threshold-Abstand (k1)"
        description="Wie weit die Amplitude den Threshold überschreitet."
        value={config.w1_threshold_distance}
        min={0}
        max={1}
        step={0.05}
        on:change={(e) => handleChange('w1_threshold_distance', e.detail)}
      />
    </div>

    <div class="weight-item">
      <div class="weight-bar" style="--weight: {config.w2_timeframe_consistency}; --color: #3b82f6;"></div>
      <ParameterSlider
        label="Timeframe-Konsistenz (k2)"
        description="Auf wie vielen Zeitebenen der Pivot existiert."
        value={config.w2_timeframe_consistency}
        min={0}
        max={1}
        step={0.05}
        on:change={(e) => handleChange('w2_timeframe_consistency', e.detail)}
      />
    </div>

    <div class="weight-item">
      <div class="weight-bar" style="--weight: {config.w3_dfa_stability}; --color: #f59e0b;"></div>
      <ParameterSlider
        label="DFA-Stabilität (k3)"
        description="Wie stabil α während der Pivot-Bildung war."
        value={config.w3_dfa_stability}
        min={0}
        max={1}
        step={0.05}
        on:change={(e) => handleChange('w3_dfa_stability', e.detail)}
      />
    </div>

    <div class="weight-item">
      <div class="weight-bar" style="--weight: {config.w4_structural_validity}; --color: #8b5cf6;"></div>
      <ParameterSlider
        label="Strukturelle Validität (k4)"
        description="Ob der Pivot in die lokale Struktur passt."
        value={config.w4_structural_validity}
        min={0}
        max={1}
        step={0.05}
        on:change={(e) => handleChange('w4_structural_validity', e.detail)}
      />
    </div>
  </div>

  <div class="formula-preview">
    <span class="formula">confidence = {config.w1_threshold_distance}·k1 + {config.w2_timeframe_consistency}·k2 + {config.w3_dfa_stability}·k3 + {config.w4_structural_validity}·k4</span>
  </div>
</div>

<style>
  .confidence-settings {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .total-indicator {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
    background: var(--color-bg-tertiary);
    border-radius: 6px;
    border-left: 3px solid var(--color-wave-impulse);
  }

  .total-indicator.invalid {
    border-left-color: #ef4444;
  }

  .total-label {
    font-size: 0.75rem;
    color: var(--color-text-muted);
  }

  .total-value {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--color-text-primary);
    font-variant-numeric: tabular-nums;
  }

  .warning {
    font-size: 0.75rem;
    color: #ef4444;
    margin-left: auto;
  }

  .weights-grid {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .weight-item {
    position: relative;
    padding-left: 4px;
  }

  .weight-bar {
    position: absolute;
    left: 0;
    top: 0.5rem;
    bottom: 0.5rem;
    width: 3px;
    background: var(--color);
    border-radius: 2px;
    opacity: calc(0.3 + var(--weight) * 0.7);
  }

  .formula-preview {
    background: var(--color-bg-tertiary);
    padding: 0.75rem;
    border-radius: 6px;
    margin-top: 0.5rem;
    overflow-x: auto;
  }

  .formula {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 0.75rem;
    color: var(--color-wave-impulse);
    white-space: nowrap;
  }
</style>
