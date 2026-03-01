<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import SettingsSection from './SettingsSection.svelte';
  import PresetSelector from './PresetSelector.svelte';
  import DFASettings from './DFASettings.svelte';
  import ThresholdSettings from './ThresholdSettings.svelte';
  import RegimeSettings from './RegimeSettings.svelte';
  import ConfidenceSettings from './ConfidenceSettings.svelte';
  import ParameterSlider from './ParameterSlider.svelte';
  import {
    engineConfigStore,
    currentPresetName,
    hasUnsavedChanges,
    configWarnings,
  } from '$lib/stores/engineConfig';
  import { analysisStore } from '$lib/stores/analysis';

  let zigzagThreshold: number = 5.0;

  // Sync local zigzag value from store when panel opens
  $: if (isOpen) {
    const unsub = analysisStore.subscribe((s) => {
      zigzagThreshold = s.settings.zigzagThreshold;
    });
    unsub();
  }

  export let isOpen: boolean = false;

  const dispatch = createEventDispatcher<{
    close: void;
    apply: void;
  }>();

  function handleClose() {
    dispatch('close');
  }

  function handleApply() {
    engineConfigStore.markAsApplied();
    analysisStore.updateSettings({ zigzagThreshold });
    dispatch('apply');
  }

  function handleReset() {
    engineConfigStore.resetToDefaults();
  }

  function handleRevert() {
    engineConfigStore.revertChanges();
  }

  function handlePresetSelect(event: CustomEvent<string>) {
    engineConfigStore.applyPreset(event.detail);
  }

  function handleFibonacciChange(event: CustomEvent<number>) {
    engineConfigStore.updateFibonacciTolerance(event.detail);
  }

  function handleZigzagChange(event: CustomEvent<number>) {
    zigzagThreshold = event.detail;
  }

  function handleBackdropClick(event: MouseEvent) {
    if (event.target === event.currentTarget) {
      handleClose();
    }
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      handleClose();
    }
  }

  $: config = $engineConfigStore.config;
</script>

<svelte:window on:keydown={handleKeydown} />

{#if isOpen}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="backdrop" on:click={handleBackdropClick}>
    <div class="panel">
      <header class="panel-header">
        <div class="header-left">
          <h2 class="title">Wave Engine Einstellungen</h2>
          {#if $hasUnsavedChanges}
            <span class="unsaved-badge">Ungespeichert</span>
          {/if}
        </div>
        <div class="header-right">
          <PresetSelector
            currentPreset={$currentPresetName}
            on:select={handlePresetSelect}
          />
          <button class="close-btn" on:click={handleClose} type="button">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M18 6 6 18" />
              <path d="m6 6 12 12" />
            </svg>
          </button>
        </div>
      </header>

      {#if $configWarnings.length > 0}
        <div class="warnings">
          {#each $configWarnings as warning}
            <div class="warning-item">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
                <path d="M12 9v4" />
                <path d="M12 17h.01" />
              </svg>
              <span>{warning}</span>
            </div>
          {/each}
        </div>
      {/if}

      <div class="panel-content">
        <SettingsSection title="DFA Parameter" defaultOpen={true}>
          <DFASettings />
        </SettingsSection>

        <SettingsSection title="Adaptiver Threshold">
          <ThresholdSettings />
        </SettingsSection>

        <SettingsSection title="Regime-Erkennung">
          <RegimeSettings />
        </SettingsSection>

        <SettingsSection title="Konfidenz-Gewichte">
          <ConfidenceSettings />
        </SettingsSection>

        <SettingsSection title="Weitere Einstellungen">
          <ParameterSlider
            label="ZigZag Threshold"
            description="Minimale Preisbewegung in % für Pivot-Erkennung. Niedrigere Werte = mehr Pivots, höhere = nur große Swings."
            value={zigzagThreshold}
            min={1}
            max={15}
            step={0.5}
            unit="%"
            on:change={handleZigzagChange}
          />
          <ParameterSlider
            label="Fibonacci-Toleranz"
            description="Toleranz für Fibonacci-Ratio-Matching (±% Abweichung)."
            value={config.fibonacci_tolerance}
            min={0.01}
            max={0.2}
            step={0.01}
            on:change={handleFibonacciChange}
          />
        </SettingsSection>
      </div>

      <footer class="panel-footer">
        <div class="footer-left">
          <button class="btn btn-ghost" on:click={handleReset} type="button">
            Auf Standard zurücksetzen
          </button>
        </div>
        <div class="footer-right">
          {#if $hasUnsavedChanges}
            <button class="btn btn-secondary" on:click={handleRevert} type="button">
              Verwerfen
            </button>
          {/if}
          <button class="btn btn-primary" on:click={handleApply} type="button">
            Anwenden
          </button>
        </div>
      </footer>
    </div>
  </div>
{/if}

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    display: flex;
    justify-content: flex-end;
    z-index: 1000;
    animation: liquid-fade-in var(--liquid-duration) var(--liquid-easing);
  }

  .panel {
    width: 420px;
    max-width: 100%;
    height: 100%;
    background: var(--glass-bg-dark);
    backdrop-filter: blur(var(--blur-xl)) saturate(var(--saturation-intense));
    -webkit-backdrop-filter: blur(var(--blur-xl)) saturate(var(--saturation-intense));
    border-left: 1px solid var(--glass-border-light);
    box-shadow: -16px 0 64px rgba(0, 0, 0, 0.4);
    display: flex;
    flex-direction: column;
    animation: liquid-slide-right var(--liquid-duration) var(--liquid-spring);
  }

  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 1.25rem;
    border-bottom: 1px solid var(--glass-border-subtle);
    flex-shrink: 0;
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .title {
    font-size: 1rem;
    font-weight: 600;
    color: var(--color-text-primary);
    margin: 0;
  }

  .unsaved-badge {
    font-size: 0.625rem;
    font-weight: 600;
    text-transform: uppercase;
    padding: 0.125rem 0.375rem;
    background: #D97706;
    color: #fff;
    border-radius: 4px;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .close-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    background: none;
    border: none;
    border-radius: 8px;
    color: var(--color-text-muted);
    cursor: pointer;
    transition: all var(--liquid-duration) var(--liquid-easing);
  }

  .close-btn:hover {
    background: var(--glass-bg-light);
    color: var(--color-text-primary);
  }

  .warnings {
    padding: 0.75rem 1.25rem;
    background: rgba(248, 113, 113, 0.1);
    border-bottom: 1px solid rgba(248, 113, 113, 0.2);
    flex-shrink: 0;
  }

  .warning-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.75rem;
    color: #F87171;
  }

  .panel-content {
    flex: 1;
    overflow-y: auto;
    padding: 0 1.25rem;
  }

  .panel-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 1.25rem;
    border-top: 1px solid var(--glass-border-subtle);
    flex-shrink: 0;
  }

  .footer-left,
  .footer-right {
    display: flex;
    gap: 0.5rem;
  }

  .btn {
    padding: 0.5rem 1rem;
    font-size: 0.875rem;
    font-weight: 500;
    border-radius: 10px;
    cursor: pointer;
    transition: all var(--liquid-duration) var(--liquid-easing);
  }

  .btn-ghost {
    background: none;
    border: none;
    color: var(--color-text-muted);
  }

  .btn-ghost:hover {
    color: var(--color-text-primary);
  }

  .btn-secondary {
    background: var(--glass-bg-medium);
    backdrop-filter: blur(16px);
    border: 1px solid var(--glass-border-light);
    color: var(--color-text-primary);
  }

  .btn-secondary:hover {
    border-color: var(--glass-border-highlight);
    background: var(--glass-bg-light);
  }

  .btn-primary {
    background: linear-gradient(to right, #D97706, #F59E0B);
    border: 1px solid rgba(217, 119, 6, 0.5);
    color: white;
    box-shadow: 0 4px 16px rgba(217, 119, 6, 0.3);
  }

  .btn-primary:hover {
    filter: brightness(1.1);
    box-shadow: 0 6px 20px rgba(217, 119, 6, 0.4);
  }
</style>
