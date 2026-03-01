<script lang="ts">
  import ParameterSlider from './ParameterSlider.svelte';
  import { engineConfigStore } from '$lib/stores/engineConfig';

  $: config = $engineConfigStore.config.regime;

  function handleChange(key: string, value: number) {
    engineConfigStore.updateRegime({ [key]: value });
  }
</script>

<div class="regime-settings">
  <div class="ewma-section">
    <div class="section-header">
      <span class="section-label">EWMA Glättung</span>
    </div>

    <ParameterSlider
      label="λ langsam"
      description="Glättungsfaktor für stabile Regime. Niedriger = glatter."
      value={config.ewma_lambda_slow}
      min={0.01}
      max={0.2}
      step={0.01}
      on:change={(e) => handleChange('ewma_lambda_slow', e.detail)}
    />

    <ParameterSlider
      label="λ schnell"
      description="Glättungsfaktor bei Regime-Wechseln. Höher = reaktiver."
      value={config.ewma_lambda_fast}
      min={0.1}
      max={0.5}
      step={0.05}
      on:change={(e) => handleChange('ewma_lambda_fast', e.detail)}
    />
  </div>

  <ParameterSlider
    label="Regime-Wechsel-Schwelle"
    description="α-Änderung ab der schnelle Glättung verwendet wird."
    value={config.regime_change_threshold}
    min={0.05}
    max={0.3}
    step={0.01}
    on:change={(e) => handleChange('regime_change_threshold', e.detail)}
  />

  <div class="thresholds-section">
    <div class="section-header">
      <span class="section-label">Regime-Klassifikation</span>
    </div>

    <div class="regime-visualization">
      <div class="regime-bar">
        <div
          class="regime-zone mean-reverting"
          style="width: {config.mean_reverting_threshold * 100}%"
        >
          <span class="regime-label">Mean-Rev.</span>
        </div>
        <div
          class="regime-zone neutral"
          style="width: {(config.trending_threshold - config.mean_reverting_threshold) * 100}%"
        >
          <span class="regime-label">Neutral</span>
        </div>
        <div
          class="regime-zone trending"
          style="width: {(1 - config.trending_threshold) * 100}%"
        >
          <span class="regime-label">Trending</span>
        </div>
      </div>
      <div class="alpha-scale">
        <span>0</span>
        <span>{config.mean_reverting_threshold}</span>
        <span>{config.trending_threshold}</span>
        <span>1</span>
      </div>
    </div>

    <ParameterSlider
      label="Mean-Reverting Schwelle"
      description="α unter diesem Wert = Mean-Reverting Regime."
      value={config.mean_reverting_threshold}
      min={0.2}
      max={0.45}
      step={0.05}
      on:change={(e) => handleChange('mean_reverting_threshold', e.detail)}
    />

    <ParameterSlider
      label="Trending Schwelle"
      description="α über diesem Wert = Trending Regime."
      value={config.trending_threshold}
      min={0.55}
      max={0.8}
      step={0.05}
      on:change={(e) => handleChange('trending_threshold', e.detail)}
    />
  </div>
</div>

<style>
  .regime-settings {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .ewma-section,
  .thresholds-section {
    background: var(--color-bg-tertiary);
    padding: 0.75rem;
    border-radius: 6px;
    margin: 0.5rem 0;
  }

  .section-header {
    margin-bottom: 0.5rem;
  }

  .section-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--color-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .regime-visualization {
    margin: 0.75rem 0;
  }

  .regime-bar {
    display: flex;
    height: 24px;
    border-radius: 4px;
    overflow: hidden;
  }

  .regime-zone {
    display: flex;
    align-items: center;
    justify-content: center;
    transition: width 0.3s ease;
  }

  .regime-zone.mean-reverting {
    background: #ef4444;
  }

  .regime-zone.neutral {
    background: #f59e0b;
  }

  .regime-zone.trending {
    background: #10b981;
  }

  .regime-label {
    font-size: 0.625rem;
    font-weight: 600;
    color: white;
    text-transform: uppercase;
  }

  .alpha-scale {
    display: flex;
    justify-content: space-between;
    margin-top: 0.25rem;
    font-size: 0.625rem;
    color: var(--color-text-muted);
  }
</style>
