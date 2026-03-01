<script lang="ts">
  import type { ProphetSettings } from '$lib/types';

  let {
    settings,
    onUpdateSettings,
    onResetSettings,
  }: {
    settings: ProphetSettings;
    onUpdateSettings: (settings: Partial<ProphetSettings>) => void;
    onResetSettings: () => void;
  } = $props();
</script>

<div class="px-3 pb-3 space-y-4">
  <!-- Data Period -->
  <div>
    <label class="block text-xs font-medium text-text-muted mb-1">Daten-Periode</label>
    <select
      class="w-full px-3 py-2 text-sm liquid-glass-subtle rounded-lg bg-stone-800/50 text-text-primary border border-stone-600/30 focus:outline-none focus:border-blue-500/50"
      value={settings.period}
      onchange={(e) => onUpdateSettings({ period: e.currentTarget.value })}
    >
      <option value="1y">1 Jahr</option>
      <option value="2y">2 Jahre</option>
      <option value="5y">5 Jahre</option>
      <option value="10y">10 Jahre</option>
      <option value="max">Maximum</option>
    </select>
  </div>

  <!-- Forecast Periods -->
  <div>
    <label class="block text-xs font-medium text-text-muted mb-1">Prognose-Tage</label>
    <input
      type="number"
      class="w-full px-3 py-2 text-sm liquid-glass-subtle rounded-lg bg-stone-800/50 text-text-primary border border-stone-600/30 focus:outline-none focus:border-blue-500/50"
      min="30"
      max="730"
      value={settings.forecast_periods}
      onchange={(e) => onUpdateSettings({ forecast_periods: parseInt(e.currentTarget.value) })}
    />
    <p class="text-xs text-text-muted mt-1">30 - 730 Tage</p>
  </div>

  <!-- Seasonality -->
  <div>
    <label class="block text-xs font-medium text-text-muted mb-2">Saisonalität</label>
    <div class="space-y-2">
      <label class="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={settings.yearly_seasonality}
          class="w-4 h-4 rounded border-stone-600 bg-stone-700 text-blue-500 focus:ring-blue-500 focus:ring-offset-0"
          onchange={(e) => onUpdateSettings({ yearly_seasonality: e.currentTarget.checked })}
        />
        <span class="text-sm text-text-primary">Jährlich</span>
      </label>
      <label class="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={settings.weekly_seasonality}
          class="w-4 h-4 rounded border-stone-600 bg-stone-700 text-blue-500 focus:ring-blue-500 focus:ring-offset-0"
          onchange={(e) => onUpdateSettings({ weekly_seasonality: e.currentTarget.checked })}
        />
        <span class="text-sm text-text-primary">Wöchentlich</span>
      </label>
    </div>
  </div>

  <!-- Changepoint Prior Scale -->
  <div>
    <label class="block text-xs font-medium text-text-muted mb-1">
      Changepoint Flexibilität
      <span class="text-text-muted font-normal">({settings.changepoint_prior_scale})</span>
    </label>
    <input
      type="range"
      min="0.001"
      max="0.5"
      step="0.001"
      value={settings.changepoint_prior_scale}
      class="w-full h-2 bg-stone-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
      oninput={(e) => onUpdateSettings({ changepoint_prior_scale: parseFloat(e.currentTarget.value) })}
    />
    <div class="flex justify-between text-xs text-text-muted mt-1">
      <span>Stabil</span>
      <span>Flexibel</span>
    </div>
  </div>

  <!-- Confidence Interval -->
  <div>
    <label class="block text-xs font-medium text-text-muted mb-1">
      Konfidenzintervall
      <span class="text-text-muted font-normal">({(settings.interval_width * 100).toFixed(0)}%)</span>
    </label>
    <input
      type="range"
      min="0.5"
      max="0.99"
      step="0.01"
      value={settings.interval_width}
      class="w-full h-2 bg-stone-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
      oninput={(e) => onUpdateSettings({ interval_width: parseFloat(e.currentTarget.value) })}
    />
    <div class="flex justify-between text-xs text-text-muted mt-1">
      <span>50%</span>
      <span>99%</span>
    </div>
  </div>

  <!-- Reset Button -->
  <button
    class="w-full px-3 py-2 text-sm text-text-muted hover:text-text-primary liquid-glass-subtle rounded-lg transition-all"
    onclick={onResetSettings}
  >
    Zurücksetzen
  </button>
</div>
