<script lang="ts">
  import type {
    XGBoostSettings,
    XGBoostFeatureToggles,
    XGBoostMetrics,
    FeatureImportance,
  } from '$lib/types';

  let {
    settings,
    featureToggles,
    metrics = null,
    featureImportance = [],
    loading = false,
    onUpdateSettings,
    onUpdateFeatureToggles,
    onResetSettings,
    onAnalyze,
  }: {
    settings: XGBoostSettings;
    featureToggles: XGBoostFeatureToggles;
    metrics?: XGBoostMetrics | null;
    featureImportance?: FeatureImportance[];
    loading?: boolean;
    onUpdateSettings: (settings: Partial<XGBoostSettings>) => void;
    onUpdateFeatureToggles: (toggles: Partial<XGBoostFeatureToggles>) => void;
    onResetSettings: () => void;
    onAnalyze: () => void;
  } = $props();

  // Feature toggle groups
  const featureGroups = [
    { key: 'use_time_features', label: 'Zeit (5)', description: 'Monat, Wochentag, etc.' },
    { key: 'use_lag_features', label: 'Lags (8)', description: 'Residual & Preis Lags' },
    { key: 'use_rolling_features', label: 'Rolling (8)', description: 'Rolling Means & Stds' },
    { key: 'use_prophet_components', label: 'Prophet (3)', description: 'Trend & Seasonality' },
    { key: 'use_market_structure', label: 'Markt (3)', description: 'Momentum, Vol, etc.' },
  ] as const;

  function formatMetric(value: number | null | undefined, decimals: number = 2): string {
    if (value === null || value === undefined) return '-';
    return value.toFixed(decimals);
  }

  function getImprovementColor(value: number): string {
    if (value > 0) return 'text-emerald-400';
    if (value < 0) return 'text-red-400';
    return 'text-stone-400';
  }
</script>

<div class="px-3 pb-3 space-y-4">
  <!-- Metrics Comparison -->
  {#if metrics}
    <div class="liquid-glass-subtle rounded-lg p-3">
      <h4 class="text-xs font-medium text-text-muted mb-2">Metriken-Vergleich</h4>
      <div class="grid grid-cols-2 gap-2 text-xs">
        <div></div>
        <div class="grid grid-cols-3 gap-1 text-center">
          <span class="text-stone-500">Prophet</span>
          <span class="text-emerald-500">Hybrid</span>
          <span class="text-stone-500">Verbess.</span>
        </div>

        <!-- MAE -->
        <div class="text-stone-400">MAE</div>
        <div class="grid grid-cols-3 gap-1 text-center">
          <span class="text-stone-300">{formatMetric(metrics.prophet_mae)}</span>
          <span class="text-emerald-300">{formatMetric(metrics.hybrid_mae)}</span>
          <span class={getImprovementColor(metrics.mae_improvement_pct)}>
            {metrics.mae_improvement_pct > 0 ? '+' : ''}{formatMetric(metrics.mae_improvement_pct, 1)}%
          </span>
        </div>

        <!-- RMSE -->
        <div class="text-stone-400">RMSE</div>
        <div class="grid grid-cols-3 gap-1 text-center">
          <span class="text-stone-300">{formatMetric(metrics.prophet_rmse)}</span>
          <span class="text-emerald-300">{formatMetric(metrics.hybrid_rmse)}</span>
          <span class={getImprovementColor(metrics.rmse_improvement_pct)}>
            {metrics.rmse_improvement_pct > 0 ? '+' : ''}{formatMetric(metrics.rmse_improvement_pct, 1)}%
          </span>
        </div>

        <!-- MAPE -->
        <div class="text-stone-400">MAPE</div>
        <div class="grid grid-cols-3 gap-1 text-center">
          <span class="text-stone-300">{formatMetric(metrics.prophet_mape, 1)}%</span>
          <span class="text-emerald-300">{formatMetric(metrics.hybrid_mape, 1)}%</span>
          <span class={getImprovementColor(metrics.mape_improvement_pct)}>
            {metrics.mape_improvement_pct > 0 ? '+' : ''}{formatMetric(metrics.mape_improvement_pct, 1)}%
          </span>
        </div>

        <!-- R² -->
        <div class="text-stone-400">R²</div>
        <div class="grid grid-cols-3 gap-1 text-center">
          <span class="text-stone-300">{formatMetric(metrics.prophet_r2, 3)}</span>
          <span class="text-emerald-300">{formatMetric(metrics.hybrid_r2, 3)}</span>
          <span class={getImprovementColor(metrics.r2_improvement_pct)}>
            {metrics.r2_improvement_pct > 0 ? '+' : ''}{formatMetric(metrics.r2_improvement_pct, 1)}%
          </span>
        </div>
      </div>
    </div>
  {/if}

  <!-- Feature Importance -->
  {#if featureImportance.length > 0}
    <div class="liquid-glass-subtle rounded-lg p-3">
      <h4 class="text-xs font-medium text-text-muted mb-2">Feature Importance (Top 10)</h4>
      <div class="space-y-1.5">
        {#each featureImportance as feature}
          <div class="flex items-center gap-2">
            <span class="text-xs text-stone-400 w-4">{feature.rank}.</span>
            <div class="flex-1">
              <div class="flex items-center justify-between mb-0.5">
                <span class="text-xs text-stone-300 truncate" title={feature.feature_name}>
                  {feature.feature_name}
                </span>
                <span class="text-xs text-stone-500">{(feature.importance * 100).toFixed(1)}%</span>
              </div>
              <div class="h-1 bg-stone-700 rounded-full overflow-hidden">
                <div
                  class="h-full bg-emerald-500 rounded-full transition-all"
                  style="width: {feature.importance * 100}%"
                ></div>
              </div>
            </div>
          </div>
        {/each}
      </div>
    </div>
  {/if}

  <!-- Feature Toggles -->
  <div class="liquid-glass-subtle rounded-lg p-3">
    <h4 class="text-xs font-medium text-text-muted mb-2">Feature-Gruppen</h4>
    <div class="space-y-2">
      {#each featureGroups as group}
        <label class="flex items-center justify-between cursor-pointer">
          <div class="flex-1">
            <span class="text-xs text-stone-300">{group.label}</span>
            <span class="text-xs text-stone-500 ml-1">- {group.description}</span>
          </div>
          <input
            type="checkbox"
            checked={featureToggles[group.key]}
            onchange={() => onUpdateFeatureToggles({ [group.key]: !featureToggles[group.key] })}
            class="w-4 h-4 rounded border-stone-600 bg-stone-800 text-emerald-500 focus:ring-emerald-500 focus:ring-offset-0"
          />
        </label>
      {/each}
    </div>
  </div>

  <!-- Hyperparameters -->
  <div class="liquid-glass-subtle rounded-lg p-3">
    <h4 class="text-xs font-medium text-text-muted mb-2">Hyperparameter</h4>
    <div class="space-y-3">
      <!-- n_estimators -->
      <div>
        <div class="flex items-center justify-between mb-1">
          <span class="text-xs text-stone-400">n_estimators</span>
          <span class="text-xs text-stone-300">{settings.n_estimators}</span>
        </div>
        <input
          type="range"
          min="100"
          max="1000"
          step="50"
          value={settings.n_estimators}
          oninput={(e) => onUpdateSettings({ n_estimators: parseInt(e.currentTarget.value) })}
          class="w-full h-1 bg-stone-700 rounded-lg appearance-none cursor-pointer accent-emerald-500"
        />
      </div>

      <!-- max_depth -->
      <div>
        <div class="flex items-center justify-between mb-1">
          <span class="text-xs text-stone-400">max_depth</span>
          <span class="text-xs text-stone-300">{settings.max_depth}</span>
        </div>
        <input
          type="range"
          min="2"
          max="10"
          step="1"
          value={settings.max_depth}
          oninput={(e) => onUpdateSettings({ max_depth: parseInt(e.currentTarget.value) })}
          class="w-full h-1 bg-stone-700 rounded-lg appearance-none cursor-pointer accent-emerald-500"
        />
      </div>

      <!-- learning_rate -->
      <div>
        <div class="flex items-center justify-between mb-1">
          <span class="text-xs text-stone-400">learning_rate</span>
          <span class="text-xs text-stone-300">{settings.learning_rate.toFixed(2)}</span>
        </div>
        <input
          type="range"
          min="0.01"
          max="0.3"
          step="0.01"
          value={settings.learning_rate}
          oninput={(e) => onUpdateSettings({ learning_rate: parseFloat(e.currentTarget.value) })}
          class="w-full h-1 bg-stone-700 rounded-lg appearance-none cursor-pointer accent-emerald-500"
        />
      </div>

      <!-- subsample -->
      <div>
        <div class="flex items-center justify-between mb-1">
          <span class="text-xs text-stone-400">subsample</span>
          <span class="text-xs text-stone-300">{settings.subsample.toFixed(2)}</span>
        </div>
        <input
          type="range"
          min="0.5"
          max="1.0"
          step="0.05"
          value={settings.subsample}
          oninput={(e) => onUpdateSettings({ subsample: parseFloat(e.currentTarget.value) })}
          class="w-full h-1 bg-stone-700 rounded-lg appearance-none cursor-pointer accent-emerald-500"
        />
      </div>
    </div>
  </div>

  <!-- Action Buttons -->
  <div class="flex gap-2">
    <button
      class="flex-1 px-3 py-2 text-xs liquid-glass-subtle rounded-lg text-stone-400 hover:text-stone-200 hover:bg-stone-700/50 transition-all"
      onclick={onResetSettings}
    >
      Zurücksetzen
    </button>
    <button
      class="flex-1 px-3 py-2 text-xs liquid-glass bg-gradient-to-r from-emerald-600/80 to-emerald-500/80 text-white rounded-lg hover:from-emerald-500/90 hover:to-emerald-400/90 transition-all disabled:opacity-50"
      onclick={onAnalyze}
      disabled={loading}
    >
      {loading ? 'Analysiere...' : 'Neu analysieren'}
    </button>
  </div>
</div>
