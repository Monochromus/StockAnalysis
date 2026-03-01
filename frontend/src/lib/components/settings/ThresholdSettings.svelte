<script lang="ts">
  import ParameterSlider from './ParameterSlider.svelte';
  import { engineConfigStore } from '$lib/stores/engineConfig';

  $: config = $engineConfigStore.config.threshold;

  function handleChange(key: string, value: number) {
    engineConfigStore.updateThreshold({ [key]: value });
  }
</script>

<div class="threshold-settings">
  <ParameterSlider
    label="ATR Periode"
    description="Periode für die Average True Range Berechnung."
    value={config.atr_period}
    min={5}
    max={50}
    step={1}
    unit="Kerzen"
    on:change={(e) => handleChange('atr_period', e.detail)}
  />

  <div class="beta-range">
    <div class="beta-header">
      <span class="beta-label">Multiplikator-Bereich</span>
      <span class="beta-value">{config.beta_min.toFixed(1)} - {config.beta_max.toFixed(1)}</span>
    </div>

    <ParameterSlider
      label="β min (Mean-Reverting)"
      description="Minimaler Multiplikator für mean-reverting Märkte. Niedriger = mehr Pivots."
      value={config.beta_min}
      min={0.1}
      max={2.0}
      step={0.1}
      on:change={(e) => handleChange('beta_min', e.detail)}
    />

    <ParameterSlider
      label="β max (Trending)"
      description="Maximaler Multiplikator für Trendmärkte. Höher = weniger Pivots."
      value={config.beta_max}
      min={1.0}
      max={5.0}
      step={0.1}
      on:change={(e) => handleChange('beta_max', e.detail)}
    />
  </div>

  <ParameterSlider
    label="Sigmoid Steilheit (k)"
    description="Steilheit des Übergangs. Höher = schärferer Übergang zwischen Regimes."
    value={config.sigmoid_k}
    min={1}
    max={50}
    step={1}
    on:change={(e) => handleChange('sigmoid_k', e.detail)}
  />

  <ParameterSlider
    label="α Mittelpunkt"
    description="Wendepunkt der Sigmoid-Funktion. Normalerweise 0.5 (Random Walk)."
    value={config.alpha_mid}
    min={0.3}
    max={0.7}
    step={0.05}
    on:change={(e) => handleChange('alpha_mid', e.detail)}
  />

  <div class="formula-preview">
    <span class="formula">τ = ATR({config.atr_period}) × f(α)</span>
    <p class="formula-description">
      Der adaptive Threshold kombiniert Volatilität (ATR) mit Markt-Regime (α).
    </p>
  </div>
</div>

<style>
  .threshold-settings {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .beta-range {
    background: var(--color-bg-tertiary);
    padding: 0.75rem;
    border-radius: 6px;
    margin: 0.5rem 0;
  }

  .beta-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
  }

  .beta-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--color-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .beta-value {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--color-wave-impulse);
    font-variant-numeric: tabular-nums;
  }

  .formula-preview {
    background: var(--color-bg-tertiary);
    padding: 0.75rem;
    border-radius: 6px;
    margin-top: 0.5rem;
  }

  .formula {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 0.875rem;
    color: var(--color-wave-impulse);
  }

  .formula-description {
    font-size: 0.75rem;
    color: var(--color-text-muted);
    margin: 0.5rem 0 0;
  }
</style>
