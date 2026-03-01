<script lang="ts">
  import type { ProphetForecastSeries, ProphetHorizonSummary, ProphetComponentSeries, ProphetHorizonToggles, ProphetSettings } from '$lib/types';
  import { ModuleActivateToggle } from '$lib/components/ui';
  import ProphetForecastStatus from './ProphetForecastStatus.svelte';
  import ProphetSettingsPanel from './ProphetSettingsPanel.svelte';
  import ProphetComponentWidget from './ProphetComponentWidget.svelte';

  let {
    priceSummaries = [],
    components = null,
    horizonToggles,
    settings,
    activeComponentWidget = null,
    showComponents = false,
    symbol = null,
    loading = false,
    fromCache = false,
    lastAnalyzedAt = null,
    error = null,
    onAnalyze,
    onToggleHorizon,
    onToggleComponents,
    onSetActiveComponentWidget,
    onUpdateSettings,
    onResetSettings,
    onFetchComponents,
    isActive = false,
    onToggle,
  }: {
    priceSummaries?: ProphetHorizonSummary[];
    components?: ProphetComponentSeries | null;
    horizonToggles: ProphetHorizonToggles;
    settings: ProphetSettings;
    activeComponentWidget?: 'trend' | 'weekly' | 'monthly' | 'yearly' | null;
    showComponents?: boolean;
    symbol?: string | null;
    loading?: boolean;
    fromCache?: boolean;
    lastAnalyzedAt?: string | null;
    error?: string | null;
    onAnalyze: () => void;
    onToggleHorizon: (horizon: keyof ProphetHorizonToggles) => void;
    onToggleComponents: () => void;
    onSetActiveComponentWidget: (widget: 'trend' | 'weekly' | 'monthly' | 'yearly' | null) => void;
    onUpdateSettings: (settings: Partial<ProphetSettings>) => void;
    onResetSettings: () => void;
    onFetchComponents: (horizon: string) => void;
    isActive?: boolean;
    onToggle: () => void;
  } = $props();

  // UI state
  let showSettings = $state(false);
  let showComponentsSection = $state(false);

  const hasForecasts = $derived(priceSummaries.length > 0);

  function formatDate(dateStr: string | null): string {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString('de-DE', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }
</script>

<div class="h-full flex flex-col overflow-hidden">
  <!-- Header -->
  <div class="p-4 border-b border-stone-700/30">
    <div class="flex items-center justify-between">
      <h2 class="text-sm font-semibold text-text-primary">Prophet Forecast</h2>
      <div class="flex items-center gap-2">
        <ModuleActivateToggle
          moduleId="prophet"
          {isActive}
          {onToggle}
          color="blue"
        />
        {#if isActive}
          <button
            class="px-3 py-1 text-xs liquid-glass-subtle bg-blue-600/80 text-white rounded-lg hover:bg-blue-500/80 transition-all disabled:opacity-50"
            onclick={onAnalyze}
            disabled={loading || !symbol}
          >
            {loading ? 'Analysiere...' : hasForecasts ? 'Aktualisieren' : 'Analyze'}
          </button>
        {/if}
      </div>
    </div>

    {#if error}
      <div class="mt-2 p-2 liquid-glass-subtle border border-red-500/30 rounded-lg bg-red-900/20">
        <p class="text-xs text-red-400">{error}</p>
      </div>
    {/if}

    {#if fromCache && lastAnalyzedAt}
      <div class="mt-2 text-xs text-text-muted">
        Aus Cache: {formatDate(lastAnalyzedAt)}
      </div>
    {/if}
  </div>

  <!-- Scrollable Content -->
  <div class="flex-1 overflow-y-auto">
    {#if loading}
      <div class="flex items-center justify-center py-12">
        <div class="text-center">
          <div class="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-2"></div>
          <p class="text-xs text-text-muted">Prophet Training...</p>
          <p class="text-xs text-text-muted mt-1">Dies kann einige Sekunden dauern</p>
        </div>
      </div>
    {:else if !hasForecasts}
      <div class="p-6 text-center">
        <div class="w-16 h-16 mx-auto mb-4 rounded-full liquid-glass-subtle flex items-center justify-center">
          <svg class="w-8 h-8 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
          </svg>
        </div>
        <h3 class="text-sm font-medium text-text-primary mb-2">Keine Prognose</h3>
        <p class="text-xs text-text-muted mb-4">
          Klicken Sie auf "Analyze" um eine Prophet-Prognose für Preis, Volatilität und RSI zu erstellen.
        </p>
        {#if symbol}
          <button
            class="px-4 py-2 text-sm liquid-glass bg-gradient-to-r from-blue-600/80 to-blue-500/80 text-white rounded-xl hover:from-blue-500/90 hover:to-blue-400/90 transition-all"
            onclick={onAnalyze}
          >
            Analyze {symbol}
          </button>
        {:else}
          <p class="text-xs text-text-muted">Wählen Sie zuerst ein Symbol</p>
        {/if}
      </div>
    {:else}
      <!-- Forecast Status -->
      <ProphetForecastStatus
        summaries={priceSummaries}
        {horizonToggles}
        {onToggleHorizon}
      />

      <!-- Components Section -->
      <div class="border-t border-stone-700/30">
        <button
          class="w-full p-3 flex items-center justify-between text-left hover:bg-stone-700/30 transition-all"
          onclick={() => showComponentsSection = !showComponentsSection}
        >
          <span class="text-xs font-medium text-text-muted uppercase tracking-wide">Komponenten</span>
          <svg
            class="w-4 h-4 text-text-muted transition-transform duration-200"
            class:rotate-180={showComponentsSection}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {#if showComponentsSection}
          <div class="px-3 pb-3">
            <p class="text-xs text-text-muted mb-3">
              Zeige saisonale Komponenten der Prophet-Zerlegung.
            </p>
            <div class="grid grid-cols-2 gap-2">
              <button
                class="p-2 text-xs liquid-glass-subtle rounded-lg transition-all hover:bg-blue-500/20 {activeComponentWidget === 'trend' ? 'border border-blue-500/50 bg-blue-500/20' : ''}"
                onclick={() => {
                  onSetActiveComponentWidget(activeComponentWidget === 'trend' ? null : 'trend');
                  if (activeComponentWidget !== 'trend') onFetchComponents('long_term');
                }}
              >
                <div class="w-3 h-3 rounded-full bg-blue-500 mx-auto mb-1"></div>
                Trend
              </button>
              <button
                class="p-2 text-xs liquid-glass-subtle rounded-lg transition-all hover:bg-orange-500/20 {activeComponentWidget === 'weekly' ? 'border border-orange-500/50 bg-orange-500/20' : ''}"
                onclick={() => {
                  onSetActiveComponentWidget(activeComponentWidget === 'weekly' ? null : 'weekly');
                  if (activeComponentWidget !== 'weekly') onFetchComponents('long_term');
                }}
              >
                <div class="w-3 h-3 rounded-full bg-orange-500 mx-auto mb-1"></div>
                Wöchentlich
              </button>
              <button
                class="p-2 text-xs liquid-glass-subtle rounded-lg transition-all hover:bg-green-500/20 {activeComponentWidget === 'monthly' ? 'border border-green-500/50 bg-green-500/20' : ''}"
                onclick={() => {
                  onSetActiveComponentWidget(activeComponentWidget === 'monthly' ? null : 'monthly');
                  if (activeComponentWidget !== 'monthly') onFetchComponents('long_term');
                }}
              >
                <div class="w-3 h-3 rounded-full bg-green-500 mx-auto mb-1"></div>
                Monatlich
              </button>
              <button
                class="p-2 text-xs liquid-glass-subtle rounded-lg transition-all hover:bg-red-500/20 {activeComponentWidget === 'yearly' ? 'border border-red-500/50 bg-red-500/20' : ''}"
                onclick={() => {
                  onSetActiveComponentWidget(activeComponentWidget === 'yearly' ? null : 'yearly');
                  if (activeComponentWidget !== 'yearly') onFetchComponents('long_term');
                }}
              >
                <div class="w-3 h-3 rounded-full bg-red-500 mx-auto mb-1"></div>
                Jährlich
              </button>
            </div>
          </div>
        {/if}
      </div>

      <!-- Settings Section -->
      <div class="border-t border-stone-700/30">
        <button
          class="w-full p-3 flex items-center justify-between text-left hover:bg-stone-700/30 transition-all"
          onclick={() => showSettings = !showSettings}
        >
          <span class="text-xs font-medium text-text-muted uppercase tracking-wide">Einstellungen</span>
          <svg
            class="w-4 h-4 text-text-muted transition-transform duration-200"
            class:rotate-180={showSettings}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {#if showSettings}
          <ProphetSettingsPanel
            {settings}
            {onUpdateSettings}
            {onResetSettings}
          />
          <!-- Re-analyze button -->
          <div class="px-3 pb-3">
            <button
              class="w-full px-4 py-2 text-sm liquid-glass bg-gradient-to-r from-blue-600/80 to-blue-500/80 text-white rounded-xl hover:from-blue-500/90 hover:to-blue-400/90 transition-all disabled:opacity-50"
              onclick={onAnalyze}
              disabled={loading}
            >
              {loading ? 'Analysiere...' : 'Neu analysieren'}
            </button>
          </div>
        {/if}
      </div>
    {/if}
  </div>
</div>

<!-- Component Widget (floating) -->
<ProphetComponentWidget
  {components}
  {activeComponentWidget}
  onClose={() => onSetActiveComponentWidget(null)}
/>
