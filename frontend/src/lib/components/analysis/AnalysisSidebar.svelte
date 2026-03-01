<script lang="ts">
  import { Card, ModuleActivateToggle } from '$lib/components/ui';
  import WaveCountCard from './WaveCountCard.svelte';
  import ValidationBadge from './ValidationBadge.svelte';
  import RiskRewardComponent from './RiskReward.svelte';
  import { analysisStore, activeWaveCount, validationSummary, fibonacciSummary, manualModeState } from '$lib/stores/analysis';
  import type { FibonacciScore, ElliottWaveMode } from '$lib/types';

  let {
    isActive = false,
    onToggle = () => {},
  }: {
    isActive?: boolean;
    onToggle?: () => void;
  } = $props();

  let data = $derived($analysisStore.result);
  let loading = $derived($analysisStore.loading);
  let error = $derived($analysisStore.error);
  let selectedIndex = $derived($analysisStore.selectedCountIndex);
  let activeCount = $derived($activeWaveCount);
  let mode = $derived($manualModeState.mode);
  let manualPivotCount = $derived($manualModeState.pivotCount);
  let canAnalyze = $derived($manualModeState.canAnalyze);
  let nextWaveLabel = $derived($manualModeState.nextWaveLabel);
  let pivots = $derived($analysisStore.pivotsOnly);

  function selectPrimary() {
    analysisStore.selectCount(null);
  }

  function selectAlternative(index: number) {
    // Toggle: click again to deselect back to primary
    if (selectedIndex === index) {
      analysisStore.selectCount(null);
    } else {
      analysisStore.selectCount(index);
    }
  }

  function setMode(newMode: ElliottWaveMode) {
    analysisStore.setMode(newMode);
  }

  function removeLastPivot() {
    analysisStore.removeLastManualPivot();
  }

  function clearManualPivots() {
    analysisStore.clearManualPivots();
  }

  async function analyzeManual() {
    await analysisStore.analyzeManual();
  }

  function getScoreColor(score: number): string {
    if (score >= 70) return 'text-emerald-400';
    if (score >= 40) return 'text-amber-400';
    return 'text-red-400';
  }

  function getScoreBarColor(score: number): string {
    if (score >= 70) return 'bg-emerald-400';
    if (score >= 40) return 'bg-amber-400';
    return 'bg-red-400';
  }

  function getScoreLabel(score: number): string {
    if (score >= 90) return 'Excellent';
    if (score >= 70) return 'Good';
    if (score >= 50) return 'Fair';
    if (score >= 30) return 'Weak';
    return 'Poor';
  }

  // Get wave labels for display
  function getWaveLabels(count: number): string[] {
    const labels = ['1', '2', '3', '4', '5'];
    return labels.slice(0, Math.min(count, 5));
  }
</script>

<aside class="h-full flex flex-col overflow-hidden">
  <!-- Header with Activate Toggle -->
  <div class="p-4 border-b border-stone-700/30">
    <div class="flex items-center justify-between">
      <h2 class="text-sm font-semibold text-text-primary">Elliott Waves</h2>
      <ModuleActivateToggle
        moduleId="elliottWaves"
        {isActive}
        {onToggle}
        color="amber"
      />
    </div>
  </div>

  <!-- Scrollable Content -->
  <div class="flex-1 overflow-y-auto space-y-4 p-4">
  <!-- Mode Toggle -->
  <Card padding="sm">
    <div class="flex items-center justify-between">
      <span class="text-sm font-medium text-stone-400">Modus</span>
      <div class="flex bg-stone-800/60 rounded-lg p-0.5">
        <button
          class="px-3 py-1.5 text-xs font-medium rounded-md transition-all {mode === 'auto' ? 'bg-amber-500/20 text-amber-400' : 'text-stone-500 hover:text-stone-300'}"
          onclick={() => setMode('auto')}
        >
          Auto
        </button>
        <button
          class="px-3 py-1.5 text-xs font-medium rounded-md transition-all {mode === 'manual' ? 'bg-amber-500/20 text-amber-400' : 'text-stone-500 hover:text-stone-300'}"
          onclick={() => setMode('manual')}
        >
          Manuell
        </button>
      </div>
    </div>
  </Card>

  <!-- Manual Mode Instructions -->
  {#if mode === 'manual'}
    <Card padding="md">
      <div class="space-y-3">
        <div class="flex items-center justify-between">
          <h3 class="font-semibold text-stone-50">Manuelle Wellenzählung</h3>
          <span class="text-xs px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400">
            {manualPivotCount}/6 Punkte
          </span>
        </div>

        <p class="text-xs text-stone-500">
          Klicke nacheinander auf Pivots im Chart, um die Elliott-Wellen zu definieren.
        </p>

        <!-- Wave Progress -->
        <div class="flex gap-1">
          {#each ['1', '2', '3', '4', '5'] as label, i}
            <div
              class="flex-1 h-1.5 rounded-full transition-all {manualPivotCount > i ? 'bg-amber-500' : 'bg-stone-700/50'}"
            ></div>
          {/each}
        </div>

        <!-- Next Step Indicator -->
        <div class="flex items-center gap-2 p-2 bg-stone-800/40 rounded-lg">
          <div class="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></div>
          <span class="text-sm text-stone-300">Nächster: <span class="text-amber-400 font-medium">{nextWaveLabel}</span></span>
        </div>

        <!-- Selected Waves Display -->
        {#if manualPivotCount > 0}
          <div class="flex flex-wrap gap-1">
            {#each $analysisStore.manualPivotIndices as pivotIndex, i}
              <span class="px-2 py-0.5 text-xs rounded bg-stone-700/50 text-stone-300">
                {i === 0 ? 'Start' : `W${i}`}
              </span>
            {/each}
          </div>
        {/if}

        <!-- Action Buttons -->
        <div class="flex gap-2">
          {#if manualPivotCount > 0}
            <button
              class="flex-1 px-3 py-2 text-xs font-medium rounded-lg bg-stone-700/50 text-stone-300 hover:bg-stone-700 transition-colors"
              onclick={removeLastPivot}
            >
              Letzten entfernen
            </button>
            <button
              class="flex-1 px-3 py-2 text-xs font-medium rounded-lg bg-stone-700/50 text-stone-300 hover:bg-stone-700 transition-colors"
              onclick={clearManualPivots}
            >
              Alle löschen
            </button>
          {/if}
        </div>

        {#if canAnalyze}
          <button
            class="w-full px-4 py-2.5 text-sm font-medium rounded-lg bg-amber-500 text-stone-900 hover:bg-amber-400 transition-colors disabled:opacity-50"
            onclick={analyzeManual}
            disabled={loading}
          >
            {#if loading}
              <span class="flex items-center justify-center gap-2">
                <svg class="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" />
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Analysiere...
              </span>
            {:else}
              Wellen analysieren
            {/if}
          </button>
        {/if}
      </div>
    </Card>
  {/if}

  <!-- Auto Mode: Click on pivot instruction -->
  {#if mode === 'auto' && !data && !loading}
    <Card padding="md">
      <div class="text-center py-2">
        <p class="text-sm text-stone-400">Klicke auf einen Pivot im Chart, um die Elliott-Wellen-Analyse zu starten.</p>
      </div>
    </Card>
  {/if}

  {#if loading}
    <Card padding="lg">
      <div class="flex items-center justify-center py-8">
        <svg class="animate-spin h-8 w-8 text-amber-500" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
        <span class="ml-3 text-stone-400">Analyzing waves...</span>
      </div>
    </Card>
  {:else if error}
    <Card padding="lg">
      <div class="text-center py-4">
        <svg class="w-12 h-12 mx-auto text-amber-500 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <p class="text-stone-400">{error}</p>
      </div>
    </Card>
  {:else if !data}
    <Card padding="lg">
      <div class="text-center py-8">
        <svg class="w-16 h-16 mx-auto text-stone-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
        <p class="text-stone-500">Search for a ticker to see wave analysis</p>
      </div>
    </Card>
  {:else}
    <!-- Primary Wave Count -->
    {#if data.primary_count}
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div
        onclick={selectPrimary}
        class="cursor-pointer rounded-xl transition-all {selectedIndex === null ? 'ring-2 ring-amber-500/60' : 'opacity-70 hover:opacity-100'}"
      >
        <WaveCountCard waveCount={data.primary_count} isPrimary={true} />
      </div>

      <!-- Validation Results (follows active count) -->
      {#if activeCount}
        <Card padding="md">
          <h3 class="font-semibold text-stone-50 mb-3">Elliott Wave Rules</h3>
          <div class="space-y-2">
            {#each activeCount.validation_results as result}
              <ValidationBadge {result} />
            {/each}
          </div>
        </Card>

        <!-- Fibonacci Analysis (follows active count) -->
        <Card padding="md">
          <div class="flex items-center justify-between mb-3">
            <h3 class="font-semibold text-stone-50">Fibonacci Analysis</h3>
            <span class="text-sm {getScoreColor($fibonacciSummary.averageScore)}">
              {getScoreLabel($fibonacciSummary.averageScore)}
            </span>
          </div>
          <div class="space-y-3">
            {#each activeCount.fibonacci_scores as score}
              <div class="py-2 border-b border-stone-700/30 last:border-0">
                <div class="flex items-center justify-between mb-1.5">
                  <div>
                    <span class="font-medium text-stone-50">Wave {score.wave_label}</span>
                    <p class="text-xs text-stone-500">
                      Actual: {score.actual_ratio.toFixed(3)} | Expected: {score.expected_ratio.toFixed(3)}
                    </p>
                  </div>
                  <div class="text-right">
                    <span class="font-semibold {getScoreColor(score.score)}">{score.score.toFixed(0)}</span>
                    <p class="text-xs text-stone-500">{getScoreLabel(score.score)}</p>
                  </div>
                </div>
                <!-- Progress bar visualization -->
                <div class="w-full h-1.5 bg-stone-800/60 rounded-full overflow-hidden">
                  <div
                    class="h-full rounded-full transition-all duration-500 {getScoreBarColor(score.score)}"
                    style="width: {Math.min(100, score.score)}%"
                  ></div>
                </div>
              </div>
            {/each}
          </div>
        </Card>
      {/if}
    {:else}
      <Card padding="lg">
        <div class="text-center py-4">
          <svg class="w-12 h-12 mx-auto text-stone-500 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p class="text-stone-400">No Elliott Wave pattern detected</p>
          <p class="text-xs text-stone-500 mt-2">Try adjusting the zigzag threshold</p>
        </div>
      </Card>
    {/if}

    <!-- Risk/Reward -->
    {#if data.risk_reward}
      <RiskRewardComponent riskReward={data.risk_reward} />
    {/if}

    <!-- Alternative Counts -->
    {#if data.alternative_counts.length > 0}
      <Card padding="md">
        <h3 class="font-semibold text-stone-50 mb-3">Alternative Counts</h3>
        <div class="space-y-3">
          {#each data.alternative_counts.slice(0, 3) as alt, i}
            <!-- svelte-ignore a11y_click_events_have_key_events -->
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div
              onclick={() => selectAlternative(i)}
              class="p-3 bg-stone-800/30 rounded-xl border cursor-pointer transition-all
                {selectedIndex === i
                  ? 'border-amber-500/60 ring-2 ring-amber-500/40 bg-stone-800/50'
                  : 'border-stone-700/20 hover:border-stone-600/40 hover:bg-stone-800/40'}"
            >
              <div class="flex items-center justify-between mb-2">
                <span class="text-sm {selectedIndex === i ? 'text-amber-400 font-medium' : 'text-stone-400'}">
                  Alternative {i + 1} {selectedIndex === i ? '(active)' : ''}
                </span>
                <span class="text-sm font-medium text-amber-500">{alt.overall_confidence.toFixed(1)}%</span>
              </div>
              <div class="flex gap-1 flex-wrap">
                {#each alt.waves as wave}
                  <span class="px-1.5 py-0.5 text-xs rounded {wave.type === 'impulse' ? 'bg-emerald-400/15 text-emerald-400' : 'bg-amber-400/15 text-amber-400'}">
                    {wave.label}
                  </span>
                {/each}
              </div>
            </div>
          {/each}
        </div>
      </Card>
    {/if}
  {/if}
  </div>
</aside>
