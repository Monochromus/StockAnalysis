<script lang="ts">
  import { onMount } from 'svelte';
  import { hmmStore } from '$lib/stores/hmm';
  import type { Preset } from '$lib/types';

  let { symbol = null }: { symbol: string | null } = $props();

  let showSaveDialog = $state(false);
  let presetName = $state('');
  let selectedPreset = $state<Preset | null>(null);
  let showDeleteConfirm = $state(false);
  let presetToDelete = $state<Preset | null>(null);

  // Load presets on mount
  onMount(() => {
    hmmStore.loadPresets();
  });

  function generateDefaultName(): string {
    if (!symbol) return '';
    return `${symbol}_${$hmmStore.settings.interval}_${$hmmStore.settings.period}`;
  }

  function openSaveDialog() {
    presetName = generateDefaultName();
    showSaveDialog = true;
  }

  async function handleSave() {
    if (!presetName.trim()) return;

    const preset = await hmmStore.savePreset(presetName.trim());
    if (preset) {
      showSaveDialog = false;
      presetName = '';
    }
  }

  async function handleLoad() {
    if (!selectedPreset) return;
    await hmmStore.loadPreset(selectedPreset);
  }

  function confirmDelete(preset: Preset, event: MouseEvent) {
    event.stopPropagation();
    presetToDelete = preset;
    showDeleteConfirm = true;
  }

  async function handleDelete() {
    if (!presetToDelete) return;

    const success = await hmmStore.deletePreset(presetToDelete.name);
    if (success) {
      if (selectedPreset?.name === presetToDelete.name) {
        selectedPreset = null;
      }
    }
    showDeleteConfirm = false;
    presetToDelete = null;
  }

  function formatDate(isoString: string): string {
    const date = new Date(isoString);
    return date.toLocaleDateString('de-DE', {
      day: '2-digit',
      month: '2-digit',
      year: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  function formatAlpha(alpha: number | undefined | null): string {
    if (alpha === undefined || alpha === null) return '-';
    return `${alpha >= 0 ? '+' : ''}${alpha.toFixed(1)}%`;
  }

  function selectPreset(preset: Preset) {
    selectedPreset = selectedPreset?.name === preset.name ? null : preset;
  }

  function closeOverlay() {
    showSaveDialog = false;
  }

  function closeDeleteConfirm() {
    showDeleteConfirm = false;
  }

  function stopPropagation(event: MouseEvent) {
    event.stopPropagation();
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Enter') {
      handleSave();
    }
  }
</script>

<div class="preset-manager">
  <div class="preset-header">
    <h4>Presets</h4>
    <button
      class="save-btn"
      onclick={openSaveDialog}
      disabled={!symbol}
      title={!symbol ? 'Wähle zuerst ein Symbol' : 'Aktuelle Einstellungen speichern'}
    >
      Speichern
    </button>
  </div>

  {#if $hmmStore.presetsLoading}
    <div class="loading">Lade Presets...</div>
  {:else if $hmmStore.presets.length === 0}
    <div class="empty">Keine Presets gespeichert</div>
  {:else}
    <div class="preset-list">
      {#each $hmmStore.presets as preset}
        <div
          class="preset-item"
          class:selected={selectedPreset?.name === preset.name}
          onclick={() => selectPreset(preset)}
          onkeydown={(e) => e.key === 'Enter' && selectPreset(preset)}
          role="button"
          tabindex="0"
        >
          <div class="preset-info">
            <span class="preset-name">{preset.name}</span>
            <span class="preset-meta">
              {preset.symbol} | {preset.interval} | {preset.period}
            </span>
            <span class="preset-date">{formatDate(preset.updated_at)}</span>
          </div>
          <div class="preset-metrics">
            {#if preset.saved_alpha !== undefined && preset.saved_alpha !== null}
              <span class="alpha" class:positive={preset.saved_alpha >= 0} class:negative={preset.saved_alpha < 0}>
                Alpha: {formatAlpha(preset.saved_alpha)}
              </span>
            {/if}
          </div>
          <button
            class="delete-btn"
            onclick={(e) => confirmDelete(preset, e)}
            title="Preset löschen"
          >
            ×
          </button>
        </div>
      {/each}
    </div>

    {#if selectedPreset}
      <div class="preset-actions">
        <button class="load-btn" onclick={handleLoad}>
          Preset laden
        </button>
        <div class="preset-details">
          <span>States: {selectedPreset.n_states}</span>
          <span>Model: {selectedPreset.model_type}</span>
          <span>Features: {selectedPreset.selected_features.length}</span>
        </div>
      </div>
    {/if}
  {/if}
</div>

<!-- Save Dialog -->
{#if showSaveDialog}
  <div class="dialog-overlay" onclick={closeOverlay} role="button" tabindex="-1" onkeydown={() => {}}>
    <div class="dialog" onclick={stopPropagation} role="dialog" aria-modal="true">
      <h3>Preset speichern</h3>
      <div class="dialog-content">
        <label>
          Name:
          <input
            type="text"
            bind:value={presetName}
            placeholder="z.B. BTC-USD_1d_1y"
            onkeydown={handleKeydown}
          />
        </label>
        <p class="hint">
          Enthält HMM-Modell und Strategie-Parameter.
          {#if $hmmStore.backtestResult}
            <br/>Aktueller Alpha: {formatAlpha($hmmStore.backtestResult.alpha)}
          {/if}
        </p>
      </div>
      <div class="dialog-actions">
        <button class="cancel-btn" onclick={closeOverlay}>
          Abbrechen
        </button>
        <button class="confirm-btn" onclick={handleSave} disabled={!presetName.trim()}>
          Speichern
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- Delete Confirmation -->
{#if showDeleteConfirm && presetToDelete}
  <div class="dialog-overlay" onclick={closeDeleteConfirm} role="button" tabindex="-1" onkeydown={() => {}}>
    <div class="dialog" onclick={stopPropagation} role="dialog" aria-modal="true">
      <h3>Preset löschen?</h3>
      <div class="dialog-content">
        <p>Möchtest du das Preset "{presetToDelete.name}" wirklich löschen?</p>
      </div>
      <div class="dialog-actions">
        <button class="cancel-btn" onclick={closeDeleteConfirm}>
          Abbrechen
        </button>
        <button class="delete-confirm-btn" onclick={handleDelete}>
          Löschen
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .preset-manager {
    background: var(--bg-secondary, #1a1a2e);
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 16px;
  }

  .preset-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }

  .preset-header h4 {
    margin: 0;
    font-size: 14px;
    color: var(--text-primary, #e0e0e0);
  }

  .save-btn {
    background: var(--accent-color, #4a9eff);
    color: white;
    border: none;
    padding: 6px 12px;
    border-radius: 4px;
    font-size: 12px;
    cursor: pointer;
    transition: background 0.2s;
  }

  .save-btn:hover:not(:disabled) {
    background: var(--accent-hover, #3a8eef);
  }

  .save-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .loading, .empty {
    color: var(--text-secondary, #888);
    font-size: 12px;
    text-align: center;
    padding: 12px;
  }

  .preset-list {
    max-height: 200px;
    overflow-y: auto;
    margin-bottom: 8px;
  }

  .preset-item {
    display: flex;
    align-items: center;
    padding: 8px;
    border-radius: 4px;
    cursor: pointer;
    transition: background 0.2s;
    margin-bottom: 4px;
    background: var(--bg-tertiary, #252540);
    border: 1px solid transparent;
    width: 100%;
    text-align: left;
    user-select: none;
  }

  .preset-item:hover {
    background: var(--bg-hover, #2a2a4a);
  }

  .preset-item.selected {
    background: rgba(74, 158, 255, 0.2);
    border: 1px solid var(--accent-color, #4a9eff);
  }

  .preset-info {
    flex: 1;
    min-width: 0;
  }

  .preset-name {
    display: block;
    font-size: 13px;
    font-weight: 500;
    color: var(--text-primary, #e0e0e0);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .preset-meta {
    display: block;
    font-size: 11px;
    color: var(--text-secondary, #888);
  }

  .preset-date {
    display: block;
    font-size: 10px;
    color: var(--text-tertiary, #666);
  }

  .preset-metrics {
    margin-right: 8px;
  }

  .alpha {
    font-size: 12px;
    font-weight: 500;
    padding: 2px 6px;
    border-radius: 4px;
  }

  .alpha.positive {
    color: #4caf50;
    background: rgba(76, 175, 80, 0.1);
  }

  .alpha.negative {
    color: #f44336;
    background: rgba(244, 67, 54, 0.1);
  }

  .delete-btn {
    background: transparent;
    border: none;
    color: var(--text-secondary, #888);
    font-size: 18px;
    cursor: pointer;
    padding: 4px 8px;
    border-radius: 4px;
    transition: all 0.2s;
  }

  .delete-btn:hover {
    background: rgba(244, 67, 54, 0.2);
    color: #f44336;
  }

  .preset-actions {
    border-top: 1px solid var(--border-color, #333);
    padding-top: 8px;
    margin-top: 8px;
  }

  .load-btn {
    width: 100%;
    background: var(--accent-color, #4a9eff);
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-size: 13px;
    cursor: pointer;
    transition: background 0.2s;
    margin-bottom: 8px;
  }

  .load-btn:hover {
    background: var(--accent-hover, #3a8eef);
  }

  .preset-details {
    display: flex;
    gap: 12px;
    font-size: 11px;
    color: var(--text-secondary, #888);
    justify-content: center;
  }

  /* Dialog Styles */
  .dialog-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.7);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }

  .dialog {
    background: var(--bg-secondary, #1a1a2e);
    border-radius: 12px;
    padding: 20px;
    min-width: 320px;
    max-width: 90vw;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  }

  .dialog h3 {
    margin: 0 0 16px 0;
    font-size: 16px;
    color: var(--text-primary, #e0e0e0);
  }

  .dialog-content {
    margin-bottom: 20px;
  }

  .dialog-content label {
    display: block;
    font-size: 13px;
    color: var(--text-secondary, #888);
    margin-bottom: 8px;
  }

  .dialog-content input {
    width: 100%;
    padding: 10px 12px;
    background: var(--bg-tertiary, #252540);
    border: 1px solid var(--border-color, #333);
    border-radius: 6px;
    color: var(--text-primary, #e0e0e0);
    font-size: 14px;
    margin-top: 4px;
  }

  .dialog-content input:focus {
    outline: none;
    border-color: var(--accent-color, #4a9eff);
  }

  .hint {
    font-size: 12px;
    color: var(--text-secondary, #888);
    margin-top: 8px;
  }

  .dialog-actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
  }

  .cancel-btn {
    background: var(--bg-tertiary, #252540);
    color: var(--text-primary, #e0e0e0);
    border: none;
    padding: 8px 16px;
    border-radius: 6px;
    font-size: 13px;
    cursor: pointer;
  }

  .confirm-btn {
    background: var(--accent-color, #4a9eff);
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 6px;
    font-size: 13px;
    cursor: pointer;
  }

  .confirm-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .delete-confirm-btn {
    background: #f44336;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 6px;
    font-size: 13px;
    cursor: pointer;
  }

  .delete-confirm-btn:hover {
    background: #d32f2f;
  }
</style>
