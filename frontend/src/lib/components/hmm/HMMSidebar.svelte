<script lang="ts">
  import type { RegimeInfo, TradingSignal, BacktestResult, IndicatorToggleState, IndicatorSignals, StrategyParams, FeatureConfig, ModelType, EmissionDistribution, OptimizationState } from '$lib/types';
  import { ModuleActivateToggle } from '$lib/components/ui';
  import RegimeStatus from './RegimeStatus.svelte';
  import ConfirmationDetails from './ConfirmationDetails.svelte';
  import BacktestResults from './BacktestResults.svelte';
  import IndicatorTogglePanel from './IndicatorTogglePanel.svelte';
  import HMMSettingsPanel from './HMMSettingsPanel.svelte';

  let {
    regime,
    signal,
    backtestResult,
    indicatorToggles,
    indicatorSignals,
    settings,
    strategyParams,
    backtestSettings,
    modelConfig,
    featureConfig,
    rollingRefitConfig,
    hmmOptimization,
    strategyOptimization,
    symbol = null,
    isModelTrained = false,
    loading = false,
    trainingLoading = false,
    backtestLoading = false,
    error = null,
    onTrain,
    onToggleIndicator,
    onRunBacktest,
    onUpdateSettings,
    onUpdateStrategyParams,
    onUpdateBacktestSettings,
    onResetStrategyParams,
    onUpdateModelConfig,
    onUpdateFeatureConfig,
    onUpdateRollingRefitConfig,
    onStartHMMOptimization,
    onStartStrategyOptimization,
    onCancelOptimization,
    onReanalyze,
    isActive = false,
    onToggle,
  }: {
    regime: RegimeInfo | null;
    signal: TradingSignal | null;
    backtestResult: BacktestResult | null;
    indicatorToggles: IndicatorToggleState;
    indicatorSignals: IndicatorSignals | null;
    settings: { nStates: number; nIter: number; period: string; interval: string };
    strategyParams: StrategyParams;
    backtestSettings: { leverage: number; slippagePct: number; commissionPct: number; initialCapital: number };
    modelConfig: { modelType: ModelType; emissionDistribution: EmissionDistribution; studentTDf: number };
    featureConfig: FeatureConfig;
    rollingRefitConfig: { enabled: boolean; windowSize: number; refitInterval: number };
    hmmOptimization: OptimizationState;
    strategyOptimization: OptimizationState;
    symbol?: string | null;
    isModelTrained?: boolean;
    loading?: boolean;
    trainingLoading?: boolean;
    backtestLoading?: boolean;
    error?: string | null;
    onTrain: () => void;
    onToggleIndicator: (indicator: keyof IndicatorToggleState) => void;
    onRunBacktest: () => void;
    onUpdateSettings: (settings: { nStates?: number; nIter?: number; period?: string; interval?: string }) => void;
    onUpdateStrategyParams: (params: Partial<StrategyParams>) => void;
    onUpdateBacktestSettings: (settings: { leverage?: number; slippagePct?: number; commissionPct?: number; initialCapital?: number }) => void;
    onResetStrategyParams: () => void;
    onUpdateModelConfig: (config: { modelType?: ModelType; emissionDistribution?: EmissionDistribution; studentTDf?: number }) => void;
    onUpdateFeatureConfig: (config: Partial<FeatureConfig>) => void;
    onUpdateRollingRefitConfig: (config: { enabled?: boolean; windowSize?: number; refitInterval?: number }) => void;
    onStartHMMOptimization: () => void;
    onStartStrategyOptimization: () => void;
    onCancelOptimization: (type: 'hmm' | 'strategy') => void;
    onReanalyze: () => void;
    isActive?: boolean;
    onToggle: () => void;
  } = $props();

  // Collapsible sections
  let showIndicatorPanel = $state(false);
  let showConfirmations = $state(false);
  let showBacktest = $state(false);
  let showSettings = $state(false);
</script>

<div class="h-full flex flex-col overflow-hidden">
  <!-- Header -->
  <div class="p-4 border-b border-stone-700/30">
    <div class="flex items-center justify-between">
      <h2 class="text-sm font-semibold text-text-primary">HMM Analysis</h2>
      <div class="flex items-center gap-2">
        <ModuleActivateToggle
          moduleId="hmm"
          {isActive}
          {onToggle}
          color="emerald"
        />
        {#if isActive && !isModelTrained && !loading}
          <button
            class="px-3 py-1 text-xs liquid-glass-subtle bg-emerald-600/80 text-white rounded-lg hover:bg-emerald-500/80 transition-all disabled:opacity-50"
            onclick={onTrain}
            disabled={trainingLoading}
          >
            {trainingLoading ? 'Training...' : 'Train Model'}
          </button>
        {/if}
      </div>
    </div>

    {#if error}
      <div class="mt-2 p-2 liquid-glass-subtle border border-red-500/30 rounded-lg bg-red-900/20">
        <p class="text-xs text-red-400">{error}</p>
      </div>
    {/if}
  </div>

  <!-- Scrollable Content -->
  <div class="flex-1 overflow-y-auto">
    {#if loading}
      <div class="flex items-center justify-center py-12">
        <div class="text-center">
          <div class="animate-spin w-8 h-8 border-2 border-accent-primary border-t-transparent rounded-full mx-auto mb-2"></div>
          <p class="text-xs text-text-muted">Analyzing...</p>
        </div>
      </div>
    {:else if !isModelTrained}
      <div class="p-6 text-center">
        <div class="w-16 h-16 mx-auto mb-4 rounded-full liquid-glass-subtle flex items-center justify-center">
          <svg class="w-8 h-8 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        </div>
        <h3 class="text-sm font-medium text-text-primary mb-2">No Model Trained</h3>
        <p class="text-xs text-text-muted mb-4">
          Train an HMM model to detect market regimes and generate trading signals.
        </p>
        <button
          class="px-4 py-2 text-sm liquid-glass bg-gradient-to-r from-amber-600/80 to-amber-500/80 text-white rounded-xl hover:from-amber-500/90 hover:to-amber-400/90 transition-all disabled:opacity-50"
          onclick={onTrain}
          disabled={trainingLoading}
        >
          {trainingLoading ? 'Training...' : 'Train Model'}
        </button>
      </div>
    {:else}
      <!-- Regime Status & Signal -->
      <RegimeStatus {regime} {signal} />

      <!-- Indicator Signals Summary -->
      {#if indicatorSignals}
        <div class="p-4 border-t border-stone-700/30">
          <h3 class="text-xs font-medium text-text-muted uppercase tracking-wide mb-2">Indicator Signals</h3>
          <div class="grid grid-cols-3 gap-2 text-xs">
            {#each Object.entries(indicatorSignals) as [name, status]}
              <div class="p-2 liquid-glass-subtle rounded-lg text-center">
                <div class="text-text-muted">{name}</div>
                <div class="font-medium"
                  class:text-green-400={status.includes('bullish') || status === 'oversold'}
                  class:text-red-400={status.includes('bearish') || status === 'overbought'}
                  class:text-yellow-400={status === 'neutral' || status === 'mixed' || status === 'weak_trend'}
                >
                  {status.replace('_', ' ')}
                </div>
              </div>
            {/each}
          </div>
        </div>
      {/if}

      <!-- Collapsible: Indicator Toggles -->
      <div class="border-t border-stone-700/30">
        <button
          class="w-full p-3 flex items-center justify-between text-left hover:bg-stone-700/30 transition-all"
          onclick={() => showIndicatorPanel = !showIndicatorPanel}
        >
          <span class="text-xs font-medium text-text-muted uppercase tracking-wide">Indicators</span>
          <svg
            class="w-4 h-4 text-text-muted transition-transform duration-200"
            class:rotate-180={showIndicatorPanel}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        {#if showIndicatorPanel}
          <IndicatorTogglePanel toggles={indicatorToggles} onToggle={onToggleIndicator} />
        {/if}
      </div>

      <!-- Collapsible: Confirmation Details -->
      <div class="border-t border-stone-700/30">
        <button
          class="w-full p-3 flex items-center justify-between text-left hover:bg-stone-700/30 transition-all"
          onclick={() => showConfirmations = !showConfirmations}
        >
          <span class="text-xs font-medium text-text-muted uppercase tracking-wide">Confirmations</span>
          <svg
            class="w-4 h-4 text-text-muted transition-transform duration-200"
            class:rotate-180={showConfirmations}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        {#if showConfirmations}
          <ConfirmationDetails {signal} />
        {/if}
      </div>

      <!-- Collapsible: Backtest Results -->
      <div class="border-t border-stone-700/30">
        <button
          class="w-full p-3 flex items-center justify-between text-left hover:bg-stone-700/30 transition-all"
          onclick={() => showBacktest = !showBacktest}
        >
          <span class="text-xs font-medium text-text-muted uppercase tracking-wide">Backtest</span>
          <svg
            class="w-4 h-4 text-text-muted transition-transform duration-200"
            class:rotate-180={showBacktest}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        {#if showBacktest}
          <BacktestResults result={backtestResult} loading={backtestLoading} {onRunBacktest} />
        {/if}
      </div>

      <!-- Collapsible: Settings -->
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
          <HMMSettingsPanel
            {settings}
            {strategyParams}
            {backtestSettings}
            {modelConfig}
            {featureConfig}
            {rollingRefitConfig}
            {hmmOptimization}
            {strategyOptimization}
            {symbol}
            {onUpdateSettings}
            {onUpdateStrategyParams}
            {onUpdateBacktestSettings}
            {onResetStrategyParams}
            {onUpdateModelConfig}
            {onUpdateFeatureConfig}
            {onUpdateRollingRefitConfig}
            {onStartHMMOptimization}
            {onStartStrategyOptimization}
            {onCancelOptimization}
          />
          <!-- Apply Button -->
          <div class="px-3 pb-3">
            <button
              class="w-full px-4 py-2 text-sm liquid-glass bg-gradient-to-r from-amber-600/80 to-amber-500/80 text-white rounded-xl hover:from-amber-500/90 hover:to-amber-400/90 transition-all disabled:opacity-50"
              onclick={onReanalyze}
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
