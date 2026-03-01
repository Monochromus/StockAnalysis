<script lang="ts">
  import type { StrategyParams, FeatureConfig, ModelType, EmissionDistribution, OptimizationState } from '$lib/types';
  import FeatureSelector from './FeatureSelector.svelte';
  import OptimizationButton from './OptimizationButton.svelte';
  import OptimizationProgress from './OptimizationProgress.svelte';
  import PresetManager from './PresetManager.svelte';

  let {
    settings,
    strategyParams,
    backtestSettings,
    modelConfig,
    featureConfig,
    rollingRefitConfig,
    hmmOptimization,
    strategyOptimization,
    symbol,
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
  }: {
    settings: {
      nStates: number;
      nIter: number;
      period: string;
      interval: string;
    };
    strategyParams: StrategyParams;
    backtestSettings: {
      leverage: number;
      slippagePct: number;
      commissionPct: number;
      initialCapital: number;
    };
    modelConfig: {
      modelType: ModelType;
      emissionDistribution: EmissionDistribution;
      studentTDf: number;
    };
    featureConfig: FeatureConfig;
    rollingRefitConfig: {
      enabled: boolean;
      windowSize: number;
      refitInterval: number;
    };
    hmmOptimization: OptimizationState;
    strategyOptimization: OptimizationState;
    symbol: string | null;
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
  } = $props();

  // Section toggles
  let showTrainingParams = $state(true);
  let showModelConfig = $state(false);
  let showFeatureConfig = $state(false);
  let showRollingRefit = $state(false);
  let showStrategyParams = $state(true);
  let showRiskManagement = $state(false);
  let showExitBehavior = $state(false);
  let showRegimeConfig = $state(false);
  let showBacktestParams = $state(true);

  // Available regimes for selection
  const availableRegimes = [
    'Crash',
    'Bear',
    'Neutral Down',
    'Chop',
    'Neutral Up',
    'Bull',
    'Bull Run',
  ];

  // MA period options
  const maPeriodOptions = [
    { value: 20, label: 'SMA 20' },
    { value: 50, label: 'SMA 50' },
    { value: 100, label: 'SMA 100' },
    { value: 200, label: 'SMA 200' },
  ];

  // Period options
  const periodOptions = [
    { value: '6mo', label: '6 Monate' },
    { value: '1y', label: '1 Jahr' },
    { value: '2y', label: '2 Jahre' },
    { value: '5y', label: '5 Jahre' },
  ];

  // Interval options
  const intervalOptions = [
    { value: '1h', label: '1 Stunde' },
    { value: '4h', label: '4 Stunden' },
    { value: '1d', label: '1 Tag' },
    { value: '1wk', label: '1 Woche' },
  ];

  // Model type options
  const modelTypeOptions: { value: ModelType; label: string; description: string }[] = [
    { value: 'hmm_gaussian', label: 'HMM (Gaussian)', description: 'Standard Hidden Markov Model mit Gauß-Verteilung' },
    { value: 'hmm_student_t', label: 'HMM (Student-t)', description: 'HMM mit Student-t Verteilung für schwere Enden' },
    { value: 'rs_garch', label: 'RS-GARCH', description: 'Regime-Switching GARCH für Volatilitäts-Clustering' },
    { value: 'bayesian_hmm', label: 'Bayesian HMM', description: 'Bayesianisches HMM mit Unsicherheitsquantifizierung' },
  ];
</script>

<div class="p-3 space-y-3">
  <!-- Preset Manager -->
  <PresetManager {symbol} />

  <!-- Training Parameters -->
  <div class="liquid-glass-subtle rounded-lg overflow-hidden">
    <button
      class="w-full p-3 flex items-center justify-between text-left hover:bg-stone-700/30 transition-all"
      onclick={() => showTrainingParams = !showTrainingParams}
    >
      <span class="text-xs font-medium text-amber-400 uppercase tracking-wide">HMM Training</span>
      <svg
        class="w-4 h-4 text-text-muted transition-transform duration-200"
        class:rotate-180={showTrainingParams}
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>

    {#if showTrainingParams}
      <div class="px-3 pb-3 space-y-3">
        <!-- Period -->
        <div>
          <label class="block text-xs text-text-muted mb-1">Zeitraum</label>
          <select
            class="w-full px-2 py-1.5 text-xs bg-stone-800/50 border border-stone-600/50 rounded-lg text-text-primary focus:outline-none focus:border-amber-500/50"
            value={settings.period}
            onchange={(e) => onUpdateSettings({ period: e.currentTarget.value })}
          >
            {#each periodOptions as opt}
              <option value={opt.value}>{opt.label}</option>
            {/each}
          </select>
        </div>

        <!-- Interval -->
        <div>
          <label class="block text-xs text-text-muted mb-1">Intervall</label>
          <select
            class="w-full px-2 py-1.5 text-xs bg-stone-800/50 border border-stone-600/50 rounded-lg text-text-primary focus:outline-none focus:border-amber-500/50"
            value={settings.interval}
            onchange={(e) => onUpdateSettings({ interval: e.currentTarget.value })}
          >
            {#each intervalOptions as opt}
              <option value={opt.value}>{opt.label}</option>
            {/each}
          </select>
        </div>

        <!-- n_states -->
        <div>
          <div class="flex justify-between mb-1">
            <label class="text-xs text-text-muted">Anzahl Regimes</label>
            <span class="text-xs text-amber-400 font-mono">{settings.nStates}</span>
          </div>
          <input
            type="range"
            min="3"
            max="10"
            step="1"
            value={settings.nStates}
            oninput={(e) => onUpdateSettings({ nStates: parseInt(e.currentTarget.value) })}
            class="w-full h-1.5 bg-stone-700 rounded-lg appearance-none cursor-pointer accent-amber-500"
          />
          <div class="flex justify-between text-[10px] text-text-muted mt-0.5">
            <span>3</span>
            <span>10</span>
          </div>
        </div>

        <!-- n_iter -->
        <div>
          <div class="flex justify-between mb-1">
            <label class="text-xs text-text-muted">Training Iterationen</label>
            <span class="text-xs text-amber-400 font-mono">{settings.nIter}</span>
          </div>
          <input
            type="range"
            min="50"
            max="500"
            step="50"
            value={settings.nIter}
            oninput={(e) => onUpdateSettings({ nIter: parseInt(e.currentTarget.value) })}
            class="w-full h-1.5 bg-stone-700 rounded-lg appearance-none cursor-pointer accent-amber-500"
          />
          <div class="flex justify-between text-[10px] text-text-muted mt-0.5">
            <span>50</span>
            <span>500</span>
          </div>
        </div>

        <!-- HMM Optimization -->
        <div class="pt-3 border-t border-stone-700/50">
          {#if hmmOptimization.isRunning || hmmOptimization.result}
            <OptimizationProgress
              progress={hmmOptimization.progress}
              result={hmmOptimization.result}
              onCancel={() => onCancelOptimization('hmm')}
            />
          {:else}
            <OptimizationButton
              label="HMM-Parameter optimieren"
              description="Grid Search (~60 Trials, ~2-3 Min.)"
              disabled={strategyOptimization.isRunning}
              onclick={onStartHMMOptimization}
            />
          {/if}
        </div>
      </div>
    {/if}
  </div>

  <!-- Model Configuration -->
  <div class="liquid-glass-subtle rounded-lg overflow-hidden">
    <button
      class="w-full p-3 flex items-center justify-between text-left hover:bg-stone-700/30 transition-all"
      onclick={() => showModelConfig = !showModelConfig}
    >
      <span class="text-xs font-medium text-purple-400 uppercase tracking-wide">Modell-Typ</span>
      <svg
        class="w-4 h-4 text-text-muted transition-transform duration-200"
        class:rotate-180={showModelConfig}
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>

    {#if showModelConfig}
      <div class="px-3 pb-3 space-y-3">
        <!-- Model Type -->
        <div>
          <label class="block text-xs text-text-muted mb-1">Modell</label>
          <select
            class="w-full px-2 py-1.5 text-xs bg-stone-800/50 border border-stone-600/50 rounded-lg text-text-primary focus:outline-none focus:border-purple-500/50"
            value={modelConfig.modelType}
            onchange={(e) => onUpdateModelConfig({ modelType: e.currentTarget.value as ModelType })}
          >
            {#each modelTypeOptions as opt}
              <option value={opt.value}>{opt.label}</option>
            {/each}
          </select>
          <p class="text-[10px] text-text-muted mt-1">
            {modelTypeOptions.find(o => o.value === modelConfig.modelType)?.description}
          </p>
        </div>

        <!-- Emission Distribution (only for HMM types) -->
        {#if modelConfig.modelType === 'hmm_gaussian' || modelConfig.modelType === 'hmm_student_t'}
          <div>
            <label class="block text-xs text-text-muted mb-1">Verteilung</label>
            <select
              class="w-full px-2 py-1.5 text-xs bg-stone-800/50 border border-stone-600/50 rounded-lg text-text-primary focus:outline-none focus:border-purple-500/50"
              value={modelConfig.emissionDistribution}
              onchange={(e) => onUpdateModelConfig({ emissionDistribution: e.currentTarget.value as EmissionDistribution })}
            >
              <option value="gaussian">Gaussian (Normal)</option>
              <option value="student_t">Student-t</option>
            </select>
          </div>

          <!-- Student-t degrees of freedom -->
          {#if modelConfig.emissionDistribution === 'student_t'}
            <div>
              <div class="flex justify-between mb-1">
                <label class="text-xs text-text-muted">Freiheitsgrade (df)</label>
                <span class="text-xs text-purple-400 font-mono">{modelConfig.studentTDf}</span>
              </div>
              <input
                type="range"
                min="2"
                max="30"
                step="1"
                value={modelConfig.studentTDf}
                oninput={(e) => onUpdateModelConfig({ studentTDf: parseFloat(e.currentTarget.value) })}
                class="w-full h-1.5 bg-stone-700 rounded-lg appearance-none cursor-pointer accent-purple-500"
              />
              <div class="flex justify-between text-[10px] text-text-muted mt-0.5">
                <span>2 (schwere Enden)</span>
                <span>30 (~ Normal)</span>
              </div>
            </div>
          {/if}
        {/if}
      </div>
    {/if}
  </div>

  <!-- Feature Configuration -->
  <div class="liquid-glass-subtle rounded-lg overflow-hidden">
    <button
      class="w-full p-3 flex items-center justify-between text-left hover:bg-stone-700/30 transition-all"
      onclick={() => showFeatureConfig = !showFeatureConfig}
    >
      <span class="text-xs font-medium text-cyan-400 uppercase tracking-wide">Feature-Auswahl</span>
      <svg
        class="w-4 h-4 text-text-muted transition-transform duration-200"
        class:rotate-180={showFeatureConfig}
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>

    {#if showFeatureConfig}
      <div class="px-3 pb-3">
        <FeatureSelector
          {featureConfig}
          onUpdateFeatureConfig={onUpdateFeatureConfig}
        />
      </div>
    {/if}
  </div>

  <!-- Rolling Refit Configuration -->
  <div class="liquid-glass-subtle rounded-lg overflow-hidden">
    <button
      class="w-full p-3 flex items-center justify-between text-left hover:bg-stone-700/30 transition-all"
      onclick={() => showRollingRefit = !showRollingRefit}
    >
      <span class="text-xs font-medium text-orange-400 uppercase tracking-wide">Rolling Refit</span>
      <svg
        class="w-4 h-4 text-text-muted transition-transform duration-200"
        class:rotate-180={showRollingRefit}
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>

    {#if showRollingRefit}
      <div class="px-3 pb-3 space-y-3">
        <!-- Enable toggle -->
        <label class="flex items-center justify-between cursor-pointer">
          <span class="text-xs text-text-muted">Rolling Refit aktivieren</span>
          <div class="relative">
            <input
              type="checkbox"
              checked={rollingRefitConfig.enabled}
              onchange={(e) => onUpdateRollingRefitConfig({ enabled: e.currentTarget.checked })}
              class="sr-only peer"
            />
            <div class="w-9 h-5 bg-stone-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-stone-400 after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-orange-500 peer-checked:after:bg-white"></div>
          </div>
        </label>

        {#if rollingRefitConfig.enabled}
          <!-- Window Size -->
          <div>
            <div class="flex justify-between mb-1">
              <label class="text-xs text-text-muted">Fenster-Größe</label>
              <span class="text-xs text-orange-400 font-mono">{rollingRefitConfig.windowSize} Tage</span>
            </div>
            <input
              type="range"
              min="63"
              max="504"
              step="21"
              value={rollingRefitConfig.windowSize}
              oninput={(e) => onUpdateRollingRefitConfig({ windowSize: parseInt(e.currentTarget.value) })}
              class="w-full h-1.5 bg-stone-700 rounded-lg appearance-none cursor-pointer accent-orange-500"
            />
            <div class="flex justify-between text-[10px] text-text-muted mt-0.5">
              <span>63 (~3 Mon.)</span>
              <span>504 (~2 Jahre)</span>
            </div>
          </div>

          <!-- Refit Interval -->
          <div>
            <div class="flex justify-between mb-1">
              <label class="text-xs text-text-muted">Refit-Intervall</label>
              <span class="text-xs text-orange-400 font-mono">{rollingRefitConfig.refitInterval} Tage</span>
            </div>
            <input
              type="range"
              min="21"
              max="126"
              step="21"
              value={rollingRefitConfig.refitInterval}
              oninput={(e) => onUpdateRollingRefitConfig({ refitInterval: parseInt(e.currentTarget.value) })}
              class="w-full h-1.5 bg-stone-700 rounded-lg appearance-none cursor-pointer accent-orange-500"
            />
            <div class="flex justify-between text-[10px] text-text-muted mt-0.5">
              <span>21 (~1 Mon.)</span>
              <span>126 (~6 Mon.)</span>
            </div>
          </div>

          <p class="text-[10px] text-text-muted bg-stone-800/50 rounded p-2">
            Das Modell wird alle {rollingRefitConfig.refitInterval} Tage auf den letzten {rollingRefitConfig.windowSize} Tagen neu trainiert.
          </p>
        {/if}
      </div>
    {/if}
  </div>

  <!-- Strategy Parameters - Basic -->
  <div class="liquid-glass-subtle rounded-lg overflow-hidden">
    <button
      class="w-full p-3 flex items-center justify-between text-left hover:bg-stone-700/30 transition-all"
      onclick={() => showStrategyParams = !showStrategyParams}
    >
      <span class="text-xs font-medium text-green-400 uppercase tracking-wide">Strategie Basis</span>
      <svg
        class="w-4 h-4 text-text-muted transition-transform duration-200"
        class:rotate-180={showStrategyParams}
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>

    {#if showStrategyParams}
      <div class="px-3 pb-3 space-y-3">
        <!-- Required Confirmations -->
        <div>
          <div class="flex justify-between mb-1">
            <label class="text-xs text-text-muted">Bestätigungen</label>
            <span class="text-xs text-green-400 font-mono">{strategyParams.required_confirmations}/8</span>
          </div>
          <input
            type="range"
            min="1"
            max="8"
            step="1"
            value={strategyParams.required_confirmations}
            oninput={(e) => onUpdateStrategyParams({ required_confirmations: parseInt(e.currentTarget.value) })}
            class="w-full h-1.5 bg-stone-700 rounded-lg appearance-none cursor-pointer accent-green-500"
          />
          <div class="flex justify-between text-[10px] text-text-muted mt-0.5">
            <span>1 (aggressiv)</span>
            <span>8 (konservativ)</span>
          </div>
        </div>

        <!-- Regime Confidence -->
        <div>
          <div class="flex justify-between mb-1">
            <label class="text-xs text-text-muted">Min. Regime Konfidenz</label>
            <span class="text-xs text-green-400 font-mono">{(strategyParams.regime_confidence_min * 100).toFixed(0)}%</span>
          </div>
          <input
            type="range"
            min="0.1"
            max="0.9"
            step="0.1"
            value={strategyParams.regime_confidence_min}
            oninput={(e) => onUpdateStrategyParams({ regime_confidence_min: parseFloat(e.currentTarget.value) })}
            class="w-full h-1.5 bg-stone-700 rounded-lg appearance-none cursor-pointer accent-green-500"
          />
        </div>

        <!-- Cooldown Periods -->
        <div>
          <div class="flex justify-between mb-1">
            <label class="text-xs text-text-muted">Cooldown Perioden</label>
            <span class="text-xs text-green-400 font-mono">{strategyParams.cooldown_periods}</span>
          </div>
          <input
            type="range"
            min="0"
            max="100"
            step="1"
            value={strategyParams.cooldown_periods}
            oninput={(e) => onUpdateStrategyParams({ cooldown_periods: parseInt(e.currentTarget.value) })}
            class="w-full h-1.5 bg-stone-700 rounded-lg appearance-none cursor-pointer accent-green-500"
          />
          <div class="flex justify-between text-[10px] text-text-muted mt-0.5">
            <span>0 (kein Cooldown)</span>
            <span>100</span>
          </div>
        </div>

        <!-- MA Period -->
        <div>
          <label class="block text-xs text-text-muted mb-1">Moving Average Periode</label>
          <select
            class="w-full px-2 py-1.5 text-xs bg-stone-800/50 border border-stone-600/50 rounded-lg text-text-primary focus:outline-none focus:border-green-500/50"
            value={strategyParams.ma_period}
            onchange={(e) => onUpdateStrategyParams({ ma_period: parseInt(e.currentTarget.value) })}
          >
            {#each maPeriodOptions as opt}
              <option value={opt.value}>{opt.label}</option>
            {/each}
          </select>
        </div>

        <!-- RSI Settings -->
        <div class="pt-2 border-t border-stone-700/50">
          <div class="text-xs text-text-muted mb-2 font-medium">RSI Schwellenwerte</div>
          <div class="grid grid-cols-2 gap-2">
            <div>
              <label class="text-[10px] text-text-muted">Oversold</label>
              <input
                type="number"
                min="10"
                max="40"
                value={strategyParams.rsi_oversold}
                onchange={(e) => onUpdateStrategyParams({ rsi_oversold: parseFloat(e.currentTarget.value) })}
                class="w-full px-2 py-1 text-xs bg-stone-800/50 border border-stone-600/50 rounded text-text-primary focus:outline-none focus:border-green-500/50"
              />
            </div>
            <div>
              <label class="text-[10px] text-text-muted">Overbought</label>
              <input
                type="number"
                min="60"
                max="90"
                value={strategyParams.rsi_overbought}
                onchange={(e) => onUpdateStrategyParams({ rsi_overbought: parseFloat(e.currentTarget.value) })}
                class="w-full px-2 py-1 text-xs bg-stone-800/50 border border-stone-600/50 rounded text-text-primary focus:outline-none focus:border-green-500/50"
              />
            </div>
            <div>
              <label class="text-[10px] text-text-muted">Bull Min</label>
              <input
                type="number"
                min="20"
                max="60"
                value={strategyParams.rsi_bull_min}
                onchange={(e) => onUpdateStrategyParams({ rsi_bull_min: parseFloat(e.currentTarget.value) })}
                class="w-full px-2 py-1 text-xs bg-stone-800/50 border border-stone-600/50 rounded text-text-primary focus:outline-none focus:border-green-500/50"
              />
            </div>
            <div>
              <label class="text-[10px] text-text-muted">Bear Max</label>
              <input
                type="number"
                min="40"
                max="80"
                value={strategyParams.rsi_bear_max}
                onchange={(e) => onUpdateStrategyParams({ rsi_bear_max: parseFloat(e.currentTarget.value) })}
                class="w-full px-2 py-1 text-xs bg-stone-800/50 border border-stone-600/50 rounded text-text-primary focus:outline-none focus:border-green-500/50"
              />
            </div>
          </div>
        </div>

        <!-- MACD, Momentum, ADX & Volume -->
        <div class="pt-2 border-t border-stone-700/50">
          <div class="text-xs text-text-muted mb-2 font-medium">Indikatoren</div>
          <div class="grid grid-cols-2 gap-2">
            <div>
              <label class="text-[10px] text-text-muted">MACD Threshold</label>
              <input
                type="number"
                min="-5"
                max="5"
                step="0.1"
                value={strategyParams.macd_threshold}
                onchange={(e) => onUpdateStrategyParams({ macd_threshold: parseFloat(e.currentTarget.value) })}
                class="w-full px-2 py-1 text-xs bg-stone-800/50 border border-stone-600/50 rounded text-text-primary focus:outline-none focus:border-green-500/50"
              />
            </div>
            <div>
              <label class="text-[10px] text-text-muted">Momentum Threshold</label>
              <input
                type="number"
                min="-5"
                max="5"
                step="0.1"
                value={strategyParams.momentum_threshold}
                onchange={(e) => onUpdateStrategyParams({ momentum_threshold: parseFloat(e.currentTarget.value) })}
                class="w-full px-2 py-1 text-xs bg-stone-800/50 border border-stone-600/50 rounded text-text-primary focus:outline-none focus:border-green-500/50"
              />
            </div>
            <div>
              <label class="text-[10px] text-text-muted">ADX Trend</label>
              <input
                type="number"
                min="10"
                max="50"
                value={strategyParams.adx_trend_threshold}
                onchange={(e) => onUpdateStrategyParams({ adx_trend_threshold: parseFloat(e.currentTarget.value) })}
                class="w-full px-2 py-1 text-xs bg-stone-800/50 border border-stone-600/50 rounded text-text-primary focus:outline-none focus:border-green-500/50"
              />
            </div>
            <div>
              <label class="text-[10px] text-text-muted">Volume Ratio</label>
              <input
                type="number"
                min="0.5"
                max="3"
                step="0.1"
                value={strategyParams.volume_ratio_threshold}
                onchange={(e) => onUpdateStrategyParams({ volume_ratio_threshold: parseFloat(e.currentTarget.value) })}
                class="w-full px-2 py-1 text-xs bg-stone-800/50 border border-stone-600/50 rounded text-text-primary focus:outline-none focus:border-green-500/50"
              />
            </div>
          </div>
        </div>

        <!-- Reset Button -->
        <button
          class="w-full mt-2 px-3 py-1.5 text-xs text-text-muted hover:text-text-primary border border-stone-600/50 rounded-lg hover:bg-stone-700/30 transition-all"
          onclick={onResetStrategyParams}
        >
          Auf Standard zurücksetzen
        </button>

        <!-- Strategy Optimization -->
        <div class="pt-3 border-t border-stone-700/50 mt-3">
          {#if strategyOptimization.isRunning || strategyOptimization.result}
            <OptimizationProgress
              progress={strategyOptimization.progress}
              result={strategyOptimization.result}
              onCancel={() => onCancelOptimization('strategy')}
            />
          {:else}
            <OptimizationButton
              label="Strategie-Parameter optimieren"
              description="Bayesian Optimization (200 Trials, ~3-5 Min.)"
              disabled={hmmOptimization.isRunning}
              onclick={onStartStrategyOptimization}
            />
          {/if}
        </div>
      </div>
    {/if}
  </div>

  <!-- Risk Management -->
  <div class="liquid-glass-subtle rounded-lg overflow-hidden">
    <button
      class="w-full p-3 flex items-center justify-between text-left hover:bg-stone-700/30 transition-all"
      onclick={() => showRiskManagement = !showRiskManagement}
    >
      <span class="text-xs font-medium text-red-400 uppercase tracking-wide">Risiko-Management</span>
      <svg
        class="w-4 h-4 text-text-muted transition-transform duration-200"
        class:rotate-180={showRiskManagement}
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>

    {#if showRiskManagement}
      <div class="px-3 pb-3 space-y-3">
        <!-- Stop Loss -->
        <div>
          <div class="flex justify-between mb-1">
            <label class="text-xs text-text-muted">Stop Loss</label>
            <span class="text-xs text-red-400 font-mono">
              {strategyParams.stop_loss_pct > 0 ? `${(strategyParams.stop_loss_pct * 100).toFixed(1)}%` : 'Aus'}
            </span>
          </div>
          <input
            type="range"
            min="0"
            max="0.2"
            step="0.005"
            value={strategyParams.stop_loss_pct}
            oninput={(e) => onUpdateStrategyParams({ stop_loss_pct: parseFloat(e.currentTarget.value) })}
            class="w-full h-1.5 bg-stone-700 rounded-lg appearance-none cursor-pointer accent-red-500"
          />
          <div class="flex justify-between text-[10px] text-text-muted mt-0.5">
            <span>Aus</span>
            <span>20%</span>
          </div>
        </div>

        <!-- Take Profit -->
        <div>
          <div class="flex justify-between mb-1">
            <label class="text-xs text-text-muted">Take Profit</label>
            <span class="text-xs text-green-400 font-mono">
              {strategyParams.take_profit_pct > 0 ? `${(strategyParams.take_profit_pct * 100).toFixed(1)}%` : 'Aus'}
            </span>
          </div>
          <input
            type="range"
            min="0"
            max="0.5"
            step="0.01"
            value={strategyParams.take_profit_pct}
            oninput={(e) => onUpdateStrategyParams({ take_profit_pct: parseFloat(e.currentTarget.value) })}
            class="w-full h-1.5 bg-stone-700 rounded-lg appearance-none cursor-pointer accent-green-500"
          />
          <div class="flex justify-between text-[10px] text-text-muted mt-0.5">
            <span>Aus</span>
            <span>50%</span>
          </div>
        </div>

        <!-- Trailing Stop -->
        <div>
          <div class="flex justify-between mb-1">
            <label class="text-xs text-text-muted">Trailing Stop</label>
            <span class="text-xs text-amber-400 font-mono">
              {strategyParams.trailing_stop_pct > 0 ? `${(strategyParams.trailing_stop_pct * 100).toFixed(1)}%` : 'Aus'}
            </span>
          </div>
          <input
            type="range"
            min="0"
            max="0.15"
            step="0.005"
            value={strategyParams.trailing_stop_pct}
            oninput={(e) => onUpdateStrategyParams({ trailing_stop_pct: parseFloat(e.currentTarget.value) })}
            class="w-full h-1.5 bg-stone-700 rounded-lg appearance-none cursor-pointer accent-amber-500"
          />
          <div class="flex justify-between text-[10px] text-text-muted mt-0.5">
            <span>Aus</span>
            <span>15%</span>
          </div>
        </div>

        <!-- Max Hold Periods -->
        <div>
          <div class="flex justify-between mb-1">
            <label class="text-xs text-text-muted">Max. Haltezeit</label>
            <span class="text-xs text-purple-400 font-mono">
              {strategyParams.max_hold_periods > 0 ? `${strategyParams.max_hold_periods} Perioden` : 'Unbegrenzt'}
            </span>
          </div>
          <input
            type="range"
            min="0"
            max="200"
            step="5"
            value={strategyParams.max_hold_periods}
            oninput={(e) => onUpdateStrategyParams({ max_hold_periods: parseInt(e.currentTarget.value) })}
            class="w-full h-1.5 bg-stone-700 rounded-lg appearance-none cursor-pointer accent-purple-500"
          />
          <div class="flex justify-between text-[10px] text-text-muted mt-0.5">
            <span>Unbegrenzt</span>
            <span>200</span>
          </div>
        </div>

        <p class="text-[10px] text-text-muted bg-stone-800/50 rounded p-2">
          Stop-Loss und Take-Profit werden im Backtest auf jeden Trade angewendet.
        </p>
      </div>
    {/if}
  </div>

  <!-- Exit Behavior -->
  <div class="liquid-glass-subtle rounded-lg overflow-hidden">
    <button
      class="w-full p-3 flex items-center justify-between text-left hover:bg-stone-700/30 transition-all"
      onclick={() => showExitBehavior = !showExitBehavior}
    >
      <span class="text-xs font-medium text-yellow-400 uppercase tracking-wide">Exit-Verhalten</span>
      <svg
        class="w-4 h-4 text-text-muted transition-transform duration-200"
        class:rotate-180={showExitBehavior}
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>

    {#if showExitBehavior}
      <div class="px-3 pb-3 space-y-3">
        <!-- Exit on Regime Change -->
        <label class="flex items-center justify-between cursor-pointer">
          <span class="text-xs text-text-muted">Exit bei Regime-Wechsel</span>
          <div class="relative">
            <input
              type="checkbox"
              checked={strategyParams.exit_on_regime_change}
              onchange={(e) => onUpdateStrategyParams({ exit_on_regime_change: e.currentTarget.checked })}
              class="sr-only peer"
            />
            <div class="w-9 h-5 bg-stone-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-stone-400 after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-yellow-500 peer-checked:after:bg-white"></div>
          </div>
        </label>

        <!-- Exit on Opposite Signal -->
        <label class="flex items-center justify-between cursor-pointer">
          <span class="text-xs text-text-muted">Exit bei Gegensignal</span>
          <div class="relative">
            <input
              type="checkbox"
              checked={strategyParams.exit_on_opposite_signal}
              onchange={(e) => onUpdateStrategyParams({ exit_on_opposite_signal: e.currentTarget.checked })}
              class="sr-only peer"
            />
            <div class="w-9 h-5 bg-stone-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-stone-400 after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-yellow-500 peer-checked:after:bg-white"></div>
          </div>
        </label>

        <p class="text-[10px] text-text-muted bg-stone-800/50 rounded p-2">
          Bestimmt, wann Positionen automatisch geschlossen werden.
        </p>
      </div>
    {/if}
  </div>

  <!-- Regime Configuration -->
  <div class="liquid-glass-subtle rounded-lg overflow-hidden">
    <button
      class="w-full p-3 flex items-center justify-between text-left hover:bg-stone-700/30 transition-all"
      onclick={() => showRegimeConfig = !showRegimeConfig}
    >
      <span class="text-xs font-medium text-teal-400 uppercase tracking-wide">Regime-Konfiguration</span>
      <svg
        class="w-4 h-4 text-text-muted transition-transform duration-200"
        class:rotate-180={showRegimeConfig}
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>

    {#if showRegimeConfig}
      <div class="px-3 pb-3 space-y-3">
        <!-- Bullish Regimes -->
        <div>
          <div class="text-xs text-text-muted mb-2 font-medium">Bullische Regimes (für LONG)</div>
          <div class="space-y-1">
            {#each availableRegimes as regime}
              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={strategyParams.bullish_regimes.includes(regime)}
                  onchange={(e) => {
                    const checked = e.currentTarget.checked;
                    const newRegimes = checked
                      ? [...strategyParams.bullish_regimes, regime]
                      : strategyParams.bullish_regimes.filter(r => r !== regime);
                    onUpdateStrategyParams({ bullish_regimes: newRegimes });
                  }}
                  class="w-3 h-3 rounded border-stone-600 bg-stone-800 text-green-500 focus:ring-green-500/30"
                />
                <span class="text-xs text-text-muted">{regime}</span>
              </label>
            {/each}
          </div>
        </div>

        <!-- Bearish Regimes -->
        <div class="pt-2 border-t border-stone-700/50">
          <div class="text-xs text-text-muted mb-2 font-medium">Bärische Regimes (für SHORT)</div>
          <div class="space-y-1">
            {#each availableRegimes as regime}
              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={strategyParams.bearish_regimes.includes(regime)}
                  onchange={(e) => {
                    const checked = e.currentTarget.checked;
                    const newRegimes = checked
                      ? [...strategyParams.bearish_regimes, regime]
                      : strategyParams.bearish_regimes.filter(r => r !== regime);
                    onUpdateStrategyParams({ bearish_regimes: newRegimes });
                  }}
                  class="w-3 h-3 rounded border-stone-600 bg-stone-800 text-red-500 focus:ring-red-500/30"
                />
                <span class="text-xs text-text-muted">{regime}</span>
              </label>
            {/each}
          </div>
        </div>
      </div>
    {/if}
  </div>

  <!-- Backtest Parameters -->
  <div class="liquid-glass-subtle rounded-lg overflow-hidden">
    <button
      class="w-full p-3 flex items-center justify-between text-left hover:bg-stone-700/30 transition-all"
      onclick={() => showBacktestParams = !showBacktestParams}
    >
      <span class="text-xs font-medium text-blue-400 uppercase tracking-wide">Backtest</span>
      <svg
        class="w-4 h-4 text-text-muted transition-transform duration-200"
        class:rotate-180={showBacktestParams}
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>

    {#if showBacktestParams}
      <div class="px-3 pb-3 space-y-3">
        <!-- Initial Capital -->
        <div>
          <label class="block text-xs text-text-muted mb-1">Startkapital ($)</label>
          <input
            type="number"
            min="100"
            max="1000000"
            step="1000"
            value={backtestSettings.initialCapital}
            onchange={(e) => onUpdateBacktestSettings({ initialCapital: parseFloat(e.currentTarget.value) })}
            class="w-full px-2 py-1.5 text-xs bg-stone-800/50 border border-stone-600/50 rounded-lg text-text-primary focus:outline-none focus:border-blue-500/50"
          />
        </div>

        <!-- Leverage -->
        <div>
          <div class="flex justify-between mb-1">
            <label class="text-xs text-text-muted">Hebel</label>
            <span class="text-xs text-blue-400 font-mono">{backtestSettings.leverage}x</span>
          </div>
          <input
            type="range"
            min="1"
            max="10"
            step="0.5"
            value={backtestSettings.leverage}
            oninput={(e) => onUpdateBacktestSettings({ leverage: parseFloat(e.currentTarget.value) })}
            class="w-full h-1.5 bg-stone-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
          />
          <div class="flex justify-between text-[10px] text-text-muted mt-0.5">
            <span>1x</span>
            <span>10x</span>
          </div>
        </div>

        <!-- Slippage & Commission -->
        <div class="grid grid-cols-2 gap-2">
          <div>
            <label class="text-[10px] text-text-muted">Slippage (%)</label>
            <input
              type="number"
              min="0"
              max="1"
              step="0.01"
              value={(backtestSettings.slippagePct * 100).toFixed(2)}
              onchange={(e) => onUpdateBacktestSettings({ slippagePct: parseFloat(e.currentTarget.value) / 100 })}
              class="w-full px-2 py-1 text-xs bg-stone-800/50 border border-stone-600/50 rounded text-text-primary focus:outline-none focus:border-blue-500/50"
            />
          </div>
          <div>
            <label class="text-[10px] text-text-muted">Kommission (%)</label>
            <input
              type="number"
              min="0"
              max="1"
              step="0.01"
              value={(backtestSettings.commissionPct * 100).toFixed(2)}
              onchange={(e) => onUpdateBacktestSettings({ commissionPct: parseFloat(e.currentTarget.value) / 100 })}
              class="w-full px-2 py-1 text-xs bg-stone-800/50 border border-stone-600/50 rounded text-text-primary focus:outline-none focus:border-blue-500/50"
            />
          </div>
        </div>
      </div>
    {/if}
  </div>
</div>
