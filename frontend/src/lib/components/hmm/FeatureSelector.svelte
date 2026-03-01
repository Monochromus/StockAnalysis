<script lang="ts">
  import type { FeatureConfig } from '$lib/types';
  import { FEATURE_INFO, DEFAULT_FEATURE_CONFIG } from '$lib/types';

  let {
    featureConfig,
    onUpdateFeatureConfig,
  }: {
    featureConfig: FeatureConfig;
    onUpdateFeatureConfig: (config: Partial<FeatureConfig>) => void;
  } = $props();

  // Group features by category
  const groupedFeatures = $derived({
    basic: FEATURE_INFO.filter(f => f.group === 'basic'),
    momentum: FEATURE_INFO.filter(f => f.group === 'momentum'),
    trend: FEATURE_INFO.filter(f => f.group === 'trend'),
    volatility: FEATURE_INFO.filter(f => f.group === 'volatility'),
    ma_distance: FEATURE_INFO.filter(f => f.group === 'ma_distance'),
    volume: FEATURE_INFO.filter(f => f.group === 'volume'),
  });

  const groupLabels: Record<string, string> = {
    basic: 'Basis',
    momentum: 'Momentum',
    trend: 'Trend',
    volatility: 'Volatilität',
    ma_distance: 'MA Distanz',
    volume: 'Volumen',
  };

  const groupColors: Record<string, string> = {
    basic: 'amber',
    momentum: 'blue',
    trend: 'green',
    volatility: 'red',
    ma_distance: 'purple',
    volume: 'cyan',
  };

  // Count selected features
  const selectedCount = $derived(
    FEATURE_INFO.filter(f => featureConfig[f.key]).length
  );

  // Calculate max warmup period
  const maxWarmup = $derived(
    Math.max(
      ...FEATURE_INFO
        .filter(f => featureConfig[f.key])
        .map(f => f.warmup),
      0
    )
  );

  function toggleFeature(key: keyof FeatureConfig) {
    onUpdateFeatureConfig({ [key]: !featureConfig[key] });
  }

  function selectAll() {
    const allTrue: Partial<FeatureConfig> = {};
    FEATURE_INFO.forEach(f => {
      allTrue[f.key] = true;
    });
    onUpdateFeatureConfig(allTrue);
  }

  function selectBasicOnly() {
    const config: Partial<FeatureConfig> = {};
    FEATURE_INFO.forEach(f => {
      config[f.key] = f.group === 'basic';
    });
    onUpdateFeatureConfig(config);
  }

  function resetToDefault() {
    onUpdateFeatureConfig(DEFAULT_FEATURE_CONFIG);
  }
</script>

<div class="space-y-3">
  <!-- Header with counts -->
  <div class="flex items-center justify-between">
    <div class="text-xs text-text-muted">
      <span class="text-amber-400 font-mono">{selectedCount}</span> Features ausgewählt
    </div>
    <div class="text-xs text-text-muted">
      Warmup: <span class="text-amber-400 font-mono">{maxWarmup}</span> Tage
    </div>
  </div>

  <!-- Quick action buttons -->
  <div class="flex gap-2">
    <button
      class="flex-1 px-2 py-1 text-[10px] text-text-muted hover:text-text-primary border border-stone-600/50 rounded hover:bg-stone-700/30 transition-all"
      onclick={selectAll}
    >
      Alle
    </button>
    <button
      class="flex-1 px-2 py-1 text-[10px] text-text-muted hover:text-text-primary border border-stone-600/50 rounded hover:bg-stone-700/30 transition-all"
      onclick={selectBasicOnly}
    >
      Nur Basis
    </button>
    <button
      class="flex-1 px-2 py-1 text-[10px] text-text-muted hover:text-text-primary border border-stone-600/50 rounded hover:bg-stone-700/30 transition-all"
      onclick={resetToDefault}
    >
      Standard
    </button>
  </div>

  <!-- Feature groups -->
  {#each Object.entries(groupedFeatures) as [groupKey, features]}
    <div class="space-y-1.5">
      <div class="text-[10px] text-{groupColors[groupKey]}-400 uppercase tracking-wide font-medium">
        {groupLabels[groupKey]}
      </div>
      <div class="flex flex-wrap gap-1.5">
        {#each features as feature}
          <button
            class="px-2 py-1 text-[10px] rounded transition-all {
              featureConfig[feature.key]
                ? `bg-${groupColors[groupKey]}-500/20 border border-${groupColors[groupKey]}-500/50 text-${groupColors[groupKey]}-400`
                : 'bg-stone-800/50 border border-stone-600/30 text-text-muted hover:border-stone-500/50'
            }"
            onclick={() => toggleFeature(feature.key)}
            title="{feature.label} (Warmup: {feature.warmup} Tage)"
          >
            {feature.label}
          </button>
        {/each}
      </div>
    </div>
  {/each}

  <!-- Warmup info -->
  {#if maxWarmup > 50}
    <div class="text-[10px] text-amber-400/70 bg-amber-500/10 border border-amber-500/20 rounded p-2">
      Hinweis: Hoher Warmup-Zeitraum ({maxWarmup} Tage) kann die verfügbaren Datenpunkte reduzieren.
    </div>
  {/if}
</div>
