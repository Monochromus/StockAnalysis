<script lang="ts">
  import { type Range, type Time } from 'lightweight-charts';
  import TickerSearch from '$lib/components/search/TickerSearch.svelte';
  import Chart from '$lib/components/chart/Chart.svelte';
  import ChartToolbar from '$lib/components/chart/ChartToolbar.svelte';
  import SettingsPanel from '$lib/components/settings/SettingsPanel.svelte';
  import SubplotChart from '$lib/components/chart/SubplotChart.svelte';
  import { AnalysisSidebar } from '$lib/components/analysis';
  import { HMMSidebar } from '$lib/components/hmm';
  import ProphetSidebar from '$lib/components/prophet/ProphetSidebar.svelte';
  import { SeasonalityCalendarView } from '$lib/components/calendar';
  import { WatchlistButton } from '$lib/components/watchlist';
  import ViewToggle from '$lib/components/ui/ViewToggle.svelte';
  import { NewsDashboard } from '$lib/components/news';
  import { tickerStore } from '$lib/stores/ticker';
  import { analysisStore, waveOverlayData } from '$lib/stores/analysis';
  import { hmmStore } from '$lib/stores/hmm';
  import { prophetStore, visiblePriceForecasts, trainingEndDate } from '$lib/stores/prophet';
  import { xgboostStore, visibleHybridForecasts } from '$lib/stores/xgboost';
  import { modulesStore, type ModuleId } from '$lib/stores/modules';
  import { pinnedZonesStore } from '$lib/stores/pinnedZones';
  import { uiStore } from '$lib/stores/ui';
  import { subplotHeightsStore } from '$lib/stores/subplotHeights';
  import { watchlistStore } from '$lib/stores/watchlist';
  import type { IndicatorToggleState, ProphetHorizonToggles, ProphetSettings, XGBoostSettings, XGBoostFeatureToggles } from '$lib/types';

  let currentSymbol = $state('');
  let currentPeriod = $state('5y');
  let currentInterval = $state('1d');
  let settingsOpen = $state(false);
  let visibleRange = $state<Range<Time> | null>(null);

  async function loadData(symbol: string, period: string, interval: string) {
    // Load market data only - module-specific analyses are handled separately
    // Each module maintains its own period/interval settings
    await tickerStore.setSymbol(symbol, period, interval);
  }

  async function handleTickerSelect(event: CustomEvent<string>) {
    const symbol = event.detail;

    // Clear pinned zones when switching to a different symbol
    if (symbol !== currentSymbol) {
      pinnedZonesStore.clearAllPinned();
      // Clear XGBoost analysis data for the old symbol
      xgboostStore.clearAnalysis();
    }

    currentSymbol = symbol;

    // Enable only Prophet by default - Elliott Waves and HMM are off
    modulesStore.setModules({ elliottWaves: false, hmm: false, prophet: true });
    hmmStore.setHMMEnabled(false);

    await loadData(symbol, currentPeriod, currentInterval);

    // Run Prophet + XGBoost analysis
    // Prophet uses its own settings (default 5y, 1d) - matches loaded chart data
    // XGBoost runs automatically after Prophet for hybrid forecasting
    await (async () => {
      await prophetStore.analyze(symbol);
      // Always run XGBoost after Prophet for hybrid forecasting
      await xgboostStore.analyze(symbol, false, currentPeriod, currentInterval);
    })();
  }

  async function handlePeriodChange(event: CustomEvent<string>) {
    const period = event.detail;

    // Clear pinned zones when period changes (data range and bar indices change)
    if (period !== currentPeriod) {
      pinnedZonesStore.clearAllPinned();
    }

    currentPeriod = period;
    if (currentSymbol) {
      await loadData(currentSymbol, period, currentInterval);

      // Re-run analyses for all enabled modules
      // Each module uses its own period settings, not the chart period
      const analyses: Promise<unknown>[] = [];

      // Elliott Waves: Re-fetch pivots and re-analyze (uses its own period setting)
      if ($modulesStore.elliottWaves) {
        analyses.push((async () => {
          const response = await analysisStore.fetchPivots(currentSymbol);
          if (response?.pivots && response.pivots.length > 0) {
            const lastPivot = response.pivots[response.pivots.length - 1];
            await analysisStore.selectStartPivot(lastPivot);
          }
        })());
      }

      // HMM: Re-run analysis (uses its own period setting)
      if ($modulesStore.hmm) {
        analyses.push((async () => {
          await hmmStore.analyze(currentSymbol);
        })());
      }

      // Prophet: Re-run analysis - sync with chart period since it uses full data
      // Then automatically run XGBoost if enabled
      if ($modulesStore.prophet) {
        analyses.push((async () => {
          prophetStore.updateSettings({ period, interval: currentInterval });
          await prophetStore.analyze(currentSymbol, true);
          // Always run XGBoost after Prophet for hybrid forecasting
          await xgboostStore.analyze(currentSymbol, true, period, currentInterval);
        })());
      }

      await Promise.all(analyses);
    }
  }

  async function handleIntervalChange(event: CustomEvent<string>) {
    const interval = event.detail;

    // Clear pinned zones when interval changes (bar indices become invalid)
    if (interval !== currentInterval) {
      pinnedZonesStore.clearAllPinned();
    }

    currentInterval = interval;
    if (currentSymbol) {
      await loadData(currentSymbol, currentPeriod, interval);

      // Re-run analyses for all enabled modules
      // Interval changes affect all modules
      const analyses: Promise<unknown>[] = [];

      // Elliott Waves: Re-fetch pivots and re-analyze with new interval
      if ($modulesStore.elliottWaves) {
        analyses.push((async () => {
          analysisStore.updateSettings({ interval });
          const response = await analysisStore.fetchPivots(currentSymbol);
          if (response?.pivots && response.pivots.length > 0) {
            const lastPivot = response.pivots[response.pivots.length - 1];
            await analysisStore.selectStartPivot(lastPivot);
          }
        })());
      }

      // HMM: Re-run analysis with new interval
      if ($modulesStore.hmm) {
        analyses.push((async () => {
          hmmStore.updateSettings({ interval });
          await hmmStore.analyze(currentSymbol);
        })());
      }

      // Prophet: Re-run analysis with new interval
      // Then automatically run XGBoost if enabled
      if ($modulesStore.prophet) {
        analyses.push((async () => {
          prophetStore.updateSettings({ interval });
          await prophetStore.analyze(currentSymbol, true);
          // Always run XGBoost after Prophet for hybrid forecasting
          await xgboostStore.analyze(currentSymbol, true, currentPeriod, interval);
        })());
      }

      await Promise.all(analyses);
    }
  }

  function handlePivotSelected(pivot: import('$lib/types').Pivot) {
    // Only allow pivot selection if Elliott Waves module is enabled
    if ($modulesStore.elliottWaves) {
      // Check if we're in manual mode
      if ($analysisStore.mode === 'manual') {
        // In manual mode, add pivot to manual selection
        analysisStore.addManualPivot(pivot);
      } else {
        // In auto mode, trigger automatic analysis from this pivot
        analysisStore.selectStartPivot(pivot);
      }
    }
  }

  async function handleResetAnalysis() {
    analysisStore.clearAnalysis();
    if (currentSymbol && $modulesStore.elliottWaves) {
      await analysisStore.fetchPivots(currentSymbol);
    }
  }

  function handleOpenSettings() {
    settingsOpen = true;
  }

  function handleCloseSettings() {
    settingsOpen = false;
  }

  async function handleApplySettings() {
    settingsOpen = false;
    if (currentSymbol) {
      await loadData(currentSymbol, currentPeriod, currentInterval);
    }
  }

  // Sidebar select handler (toolbar button click - only opens sidebar, doesn't activate module)
  function handleSidebarSelect(event: CustomEvent<{ moduleId: ModuleId }>) {
    // Sidebar selection is already handled by uiStore.toggleActiveSidebar in ChartToolbar
    // This handler can be used for additional logic if needed
  }

  // Module activation handler (toggle in sidebar - activates/deactivates module on chart)
  async function handleModuleActivate(moduleId: ModuleId) {
    const newState = !$modulesStore[moduleId];
    modulesStore.toggle(moduleId);

    if (moduleId === 'elliottWaves') {
      if (newState && currentSymbol) {
        // Fetch pivots and auto-start wave counting when Elliott Waves module is enabled
        const response = await analysisStore.fetchPivots(currentSymbol);
        if (response?.pivots && response.pivots.length > 0) {
          // Select the last significant pivot to trigger auto wave counting
          const lastPivot = response.pivots[response.pivots.length - 1];
          await analysisStore.selectStartPivot(lastPivot);
        }
      } else {
        // Clear analysis when Elliott Waves module is disabled
        analysisStore.clearAnalysis();
      }
    }

    if (moduleId === 'hmm') {
      hmmStore.setHMMEnabled(newState);

      if (newState && currentSymbol) {
        // Analyze with HMM's own settings (default 1y, 1d)
        await hmmStore.analyze(currentSymbol);
      }
    }

    if (moduleId === 'prophet') {
      if (newState && currentSymbol) {
        // Analyze with Prophet's own settings (default 5y, 1d)
        await prophetStore.analyze(currentSymbol);
        // Always run XGBoost after Prophet for hybrid forecasting
        await xgboostStore.analyze(currentSymbol, false, currentPeriod, currentInterval);
      } else if (!newState) {
        // Clear analysis when disabled
        prophetStore.clearAnalysis();
        xgboostStore.clearAnalysis();
      }
    }
  }

  // HMM specific handlers
  async function handleHMMTrain() {
    if (currentSymbol) {
      hmmStore.updateSettings({ period: currentPeriod, interval: currentInterval });
      await hmmStore.train(currentSymbol);
    }
  }

  function handleToggleIndicator(indicator: keyof IndicatorToggleState) {
    hmmStore.toggleIndicator(indicator);
  }

  async function handleRunBacktest() {
    if (currentSymbol) {
      await hmmStore.runBacktest(currentSymbol);
    }
  }

  // HMM Settings handlers
  function handleUpdateHMMSettings(settings: { nStates?: number; nIter?: number; period?: string; interval?: string }) {
    hmmStore.updateSettings(settings);
  }

  function handleUpdateStrategyParams(params: Partial<import('$lib/types').StrategyParams>) {
    hmmStore.updateStrategyParams(params);
  }

  function handleUpdateBacktestSettings(settings: { leverage?: number; slippagePct?: number; commissionPct?: number; initialCapital?: number }) {
    hmmStore.updateBacktestSettings(settings);
  }

  function handleResetStrategyParams() {
    hmmStore.resetStrategyParams();
  }

  function handleUpdateModelConfig(config: { modelType?: import('$lib/types').ModelType; emissionDistribution?: import('$lib/types').EmissionDistribution; studentTDf?: number }) {
    hmmStore.updateModelConfig(config);
  }

  function handleUpdateFeatureConfig(config: Partial<import('$lib/types').FeatureConfig>) {
    hmmStore.updateFeatureConfig(config);
  }

  function handleUpdateRollingRefitConfig(config: { enabled?: boolean; windowSize?: number; refitInterval?: number }) {
    hmmStore.updateRollingRefitConfig(config);
  }

  async function handleReanalyzeHMM() {
    if (currentSymbol) {
      // Force retrain to apply new settings
      await hmmStore.analyze(currentSymbol, true);
    }
  }

  // HMM Optimization handlers
  async function handleStartHMMOptimization() {
    if (currentSymbol) {
      await hmmStore.startHMMOptimization(currentSymbol);
    }
  }

  async function handleStartStrategyOptimization() {
    if (currentSymbol) {
      await hmmStore.startStrategyOptimization(currentSymbol);
    }
  }

  function handleCancelOptimization(type: 'hmm' | 'strategy') {
    hmmStore.cancelOptimization(type);
  }

  function handleToggleTradeMarkers() {
    hmmStore.toggleTradeMarkers();
  }

  // Prophet specific handlers
  async function handleProphetAnalyze() {
    if (currentSymbol) {
      prophetStore.updateSettings({ period: currentPeriod, interval: currentInterval });
      await prophetStore.analyze(currentSymbol, true);

      // Always run XGBoost after Prophet for hybrid forecasting
      await xgboostStore.analyze(currentSymbol, true, currentPeriod, currentInterval);
    }
  }

  function handleProphetToggleHorizon(horizon: keyof ProphetHorizonToggles) {
    prophetStore.toggleHorizon(horizon);
  }

  function handleProphetToggleComponents() {
    prophetStore.toggleComponents();
  }

  function handleProphetSetActiveComponentWidget(widget: 'trend' | 'weekly' | 'monthly' | 'yearly' | null) {
    prophetStore.setActiveComponentWidget(widget);
  }

  function handleProphetUpdateSettings(settings: Partial<ProphetSettings>) {
    prophetStore.updateSettings(settings);
  }

  function handleProphetResetSettings() {
    prophetStore.resetSettings();
  }

  async function handleProphetFetchComponents(horizon: string) {
    if (currentSymbol) {
      await prophetStore.fetchComponents(currentSymbol, horizon);
    }
  }

  // XGBoost specific handlers
  async function handleToggleXGBoost() {
    const wasEnabled = $xgboostStore.enabled;
    xgboostStore.toggle();

    // If enabling XGBoost and Prophet forecasts exist, run XGBoost analysis
    if (!wasEnabled && currentSymbol && $prophetStore.priceForecasts.length > 0) {
      await xgboostStore.analyze(currentSymbol, false, currentPeriod, currentInterval);
    }
  }

  async function handleXGBoostAnalyze() {
    if (currentSymbol && $xgboostStore.enabled) {
      await xgboostStore.analyze(currentSymbol, true, currentPeriod, currentInterval);
    }
  }

  function handleUpdateXGBoostSettings(settings: Partial<XGBoostSettings>) {
    xgboostStore.updateSettings(settings);
  }

  function handleUpdateXGBoostFeatureToggles(toggles: Partial<XGBoostFeatureToggles>) {
    xgboostStore.updateFeatureToggles(toggles);
  }

  function handleResetXGBoostSettings() {
    xgboostStore.resetSettings();
  }

  // Chart visible range handler for subplot sync (using time-based range for accurate sync)
  function handleVisibleRangeChange(range: Range<Time> | null) {
    visibleRange = range;
  }

  // UI Toggle handlers
  function toggleFullscreen() {
    if ($uiStore.headerVisible || $uiStore.toolbarVisible || $uiStore.sidebarVisible) {
      uiStore.hideAllOverlays();
    } else {
      uiStore.showAllOverlays();
    }
  }

  // Derived: Pivots to show (only when Elliott Waves is enabled)
  let visiblePivots = $derived(
    $modulesStore.elliottWaves ? $waveOverlayData.pivots : []
  );

  // Derived: Manual pivot indices for chart display
  let manualPivotIndices = $derived(
    $modulesStore.elliottWaves && $analysisStore.mode === 'manual'
      ? $analysisStore.manualPivotIndices
      : []
  );

  // Derived: Check which sidebar to show (based on activeSidebar, not module state)
  let showProphetSidebar = $derived($uiStore.activeSidebar === 'prophet');
  let showHMMSidebar = $derived($uiStore.activeSidebar === 'hmm');
  let showElliottSidebar = $derived($uiStore.activeSidebar === 'elliottWaves');
  let showAnySidebar = $derived($uiStore.activeSidebar !== null);

  // Calculate total subplot height for chart bottom padding
  let totalSubplotHeight = $derived(
    $modulesStore.hmm && $hmmStore.indicators
      ? ($hmmStore.indicatorToggles?.rsi ? $subplotHeightsStore.rsi : 0) +
        ($hmmStore.indicatorToggles?.macd ? $subplotHeightsStore.macd : 0) +
        ($hmmStore.indicatorToggles?.adx ? $subplotHeightsStore.adx : 0) +
        ($hmmStore.indicatorToggles?.atr ? $subplotHeightsStore.atr : 0)
      : 0
  );

  // Derived: Apply XGBoost corrections to Prophet forecasts when enabled
  // When XGBoost is enabled, show a single combined forecast line (emerald green)
  // XGBoost now includes both historical corrections AND future predictions
  // The line is shifted so it meets the current price at the last candle date
  let correctedPriceForecasts = $derived.by(() => {
    // Access store values to establish reactivity
    const xgboostState = $xgboostStore;
    const prophetForecasts = $visiblePriceForecasts;
    const candles = $tickerStore.candles;

    const xgboostEnabled = xgboostState.enabled;
    const hybridForecasts = xgboostState.hybridForecasts;
    const xgboostLoading = xgboostState.loading;

    // If XGBoost is not enabled, return original Prophet forecasts
    if (!xgboostEnabled) {
      return prophetForecasts;
    }

    // If XGBoost is loading, show Prophet forecasts while waiting
    if (xgboostLoading) {
      return prophetForecasts;
    }

    // If no hybrid data yet, return Prophet forecasts
    if (!hybridForecasts || hybridForecasts.length === 0) {
      return prophetForecasts;
    }

    // Get the combined hybrid forecast data
    const hybridData = hybridForecasts[0];

    if (!hybridData || !hybridData.series || hybridData.series.length === 0) {
      return prophetForecasts;
    }

    // Get the current (last) actual price and date from candles
    const lastCandle = candles.length > 0 ? candles[candles.length - 1] : null;
    const currentPrice = lastCandle?.close ?? null;
    const lastCandleDate = lastCandle?.timestamp?.substring(0, 10) ?? null;

    // Find the hybrid point that matches the last candle date
    let anchorPointIdx = -1;
    if (lastCandleDate) {
      anchorPointIdx = hybridData.series.findIndex(p =>
        p.timestamp.substring(0, 10) === lastCandleDate
      );
    }

    // If no exact match, find the closest point before the last candle date
    if (anchorPointIdx === -1 && lastCandleDate) {
      for (let i = hybridData.series.length - 1; i >= 0; i--) {
        if (hybridData.series[i].timestamp.substring(0, 10) <= lastCandleDate) {
          anchorPointIdx = i;
          break;
        }
      }
    }

    // Calculate the offset to anchor line to current price
    let priceOffset = 0;
    if (currentPrice !== null && anchorPointIdx >= 0) {
      const anchorValue = hybridData.series[anchorPointIdx].hybrid_value;
      priceOffset = currentPrice - anchorValue;
    }

    // XGBoost now includes both historical AND future predictions
    // Shift entire line by offset
    const shiftedSeries = hybridData.series.map((point) => ({
      timestamp: point.timestamp,
      value: point.hybrid_value + priceOffset,
      lower: point.lower + priceOffset,
      upper: point.upper + priceOffset,
      is_forecast: point.is_forecast,
    }));

    // Count future points for logging
    const futureCount = shiftedSeries.filter(p => p.is_forecast).length;
    console.log('[XGBoost] Hybrid forecast:', {
      totalPoints: shiftedSeries.length,
      futurePoints: futureCount,
      priceOffset: priceOffset.toFixed(2),
      trainingEnd: hybridData.training_end_date,
      forecastStart: hybridData.forecast_start_date,
    });

    // Return a single combined forecast with calm brown color
    return [{
      horizon: 'combined',
      display_name: 'Kombiniert (Prophet+XGBoost)',
      color: '#8B7355',  // Calm brown
      training_end_date: hybridData.training_end_date,
      forecast_start_date: hybridData.forecast_start_date,
      mape: null,
      rmse: null,
      series: shiftedSeries,
    }];
  });
</script>

<svelte:head>
  <title>CommodityCockpit - Saisonale Rohstoff-Analyse</title>
  <meta name="description" content="Saisonale Rohstoff-Analyse mit Prophet + XGBoost" />
</svelte:head>

<!-- Root Container: Fixed fullscreen -->
<div class="fixed inset-0 bg-bg-primary overflow-hidden">
  <!-- MAIN CONTENT LAYER (z-0) - Chart or Calendar View -->
  {#if $uiStore.viewMode === 'chart'}
    <!-- CHART LAYER - Standard chart view -->
    <div class="absolute inset-0 z-0" style="bottom: {totalSubplotHeight}px">
      <Chart
        candles={$tickerStore.candles}
        waves={$modulesStore.elliottWaves ? $waveOverlayData.waves : []}
        pivots={visiblePivots}
        riskReward={$modulesStore.elliottWaves ? $waveOverlayData.riskReward : null}
        higherDegree={$modulesStore.elliottWaves ? $waveOverlayData.higherDegree : null}
        projectedZones={$modulesStore.elliottWaves ? $waveOverlayData.projectedZones : []}
        fibonacciLevels={$modulesStore.elliottWaves ? $waveOverlayData.fibonacciLevels : []}
        selectedPivot={$modulesStore.elliottWaves ? $analysisStore.selectedStartPivot : null}
        currentSymbol={currentSymbol}
        onPivotSelected={handlePivotSelected}
        onVisibleRangeChange={handleVisibleRangeChange}
        manualPivotIndices={manualPivotIndices}
        regimeData={$modulesStore.hmm ? $hmmStore.regimeSeries : []}
        indicators={$modulesStore.hmm ? $hmmStore.indicators : null}
        indicatorToggles={$modulesStore.hmm ? $hmmStore.indicatorToggles : null}
        hmmEnabled={$modulesStore.hmm}
        trades={$modulesStore.hmm && $hmmStore.backtestResult ? $hmmStore.backtestResult.trades : []}
        showTradeMarkers={$hmmStore.showTradeMarkers}
        prophetForecasts={$modulesStore.prophet ? correctedPriceForecasts : []}
        prophetHorizonToggles={$modulesStore.prophet ? $prophetStore.horizonToggles : null}
        prophetEnabled={$modulesStore.prophet}
        prophetTrainingEndDate={$modulesStore.prophet ? $trainingEndDate : null}
      />

      <!-- Loading Overlay -->
      {#if $tickerStore.loading}
        <div class="absolute inset-0 z-20 flex items-center justify-center bg-bg-primary/80 backdrop-blur-sm">
          <div class="flex items-center gap-3">
            <svg class="animate-spin h-8 w-8 text-amber-500" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" />
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            <span class="text-stone-400">Loading chart data...</span>
          </div>
        </div>
      {/if}

      <!-- Error Message -->
      {#if $tickerStore.error && !$tickerStore.loading}
        <div class="absolute bottom-4 left-4 z-20" style="right: {$uiStore.sidebarVisible ? '420px' : '1rem'}">
          <div class="liquid-glass rounded-xl px-4 py-3 border-amber-500/40">
            <p class="text-amber-500 text-sm">{$tickerStore.error}</p>
          </div>
        </div>
      {/if}
    </div>
  {:else if $uiStore.viewMode === 'calendar'}
    <!-- CALENDAR LAYER - Seasonality calendar view -->
    {@const headerHeight = $uiStore.headerVisible ? 5.5 : 0}
    {@const toolbarHeight = $uiStore.toolbarVisible ? 3.5 : 0}
    {@const topOffset = headerHeight + toolbarHeight + ($uiStore.headerVisible || $uiStore.toolbarVisible ? 1.5 : 0)}
    <div class="absolute z-0 overflow-hidden" style="top: {topOffset}rem; left: 1rem; right: {$uiStore.sidebarVisible && showAnySidebar ? '420px' : '1rem'}; bottom: 1rem;">
      <div class="h-full bg-stone-900/50 rounded-xl overflow-hidden">
        <SeasonalityCalendarView symbol={currentSymbol} />
      </div>
    </div>
  {:else}
    <!-- NEWS LAYER - News dashboard view -->
    {@const headerHeight = $uiStore.headerVisible ? 5.5 : 0}
    {@const toolbarHeight = $uiStore.toolbarVisible ? 3.5 : 0}
    {@const topOffset = headerHeight + toolbarHeight + ($uiStore.headerVisible || $uiStore.toolbarVisible ? 1.5 : 0)}
    <div class="absolute z-0 overflow-hidden" style="top: {topOffset}rem; left: 1rem; right: {$uiStore.sidebarVisible && showAnySidebar ? '420px' : '1rem'}; bottom: 1rem;">
      <div class="h-full bg-stone-900/50 rounded-xl overflow-hidden">
        <NewsDashboard />
      </div>
    </div>
  {/if}

  <!-- SUBPLOT LAYER (z-5) - HMM Indicator subplots at bottom (only in chart mode) -->
  {#if $uiStore.viewMode === 'chart' && $modulesStore.hmm && $hmmStore.indicators}
    <div class="absolute bottom-0 left-0 z-5" style="right: {$uiStore.sidebarVisible ? '400px' : '0'}">
      {#if $hmmStore.indicatorToggles.rsi}
        <SubplotChart
          type="rsi"
          data={$hmmStore.indicators.rsi}
          visibleRange={visibleRange}
        />
      {/if}
      {#if $hmmStore.indicatorToggles.macd}
        <SubplotChart
          type="macd"
          data={$hmmStore.indicators.macd}
          secondaryData={$hmmStore.indicators.macd_signal}
          histogramData={$hmmStore.indicators.macd_histogram}
          visibleRange={visibleRange}
        />
      {/if}
      {#if $hmmStore.indicatorToggles.adx}
        <SubplotChart
          type="adx"
          data={$hmmStore.indicators.adx}
          secondaryData={$hmmStore.indicators.di_plus}
          tertiaryData={$hmmStore.indicators.di_minus}
          visibleRange={visibleRange}
        />
      {/if}
      {#if $hmmStore.indicatorToggles.atr}
        <SubplotChart
          type="atr"
          data={$hmmStore.indicators.atr}
          visibleRange={visibleRange}
        />
      {/if}
    </div>
  {/if}

  <!-- OVERLAY LAYER (z-10+) -->

  <!-- Header Overlay -->
  {#if $uiStore.headerVisible}
    <header class="fixed top-0 left-4 mt-4 z-20 liquid-glass-intense rounded-2xl animate-liquid-slide-top" style="right: {$uiStore.sidebarVisible && showAnySidebar ? '420px' : '1rem'}">
      <div class="px-6 py-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-4">
            <h1 class="text-xl font-bold text-stone-50">
              <span class="text-amber-500">Commodity</span>Cockpit
              <span class="ml-2 text-sm font-normal text-stone-400">Saisonale Rohstoff-Analyse</span>
            </h1>
            {#if currentSymbol}
              <span class="text-stone-500">|</span>
              <span class="text-lg font-semibold text-stone-50">{currentSymbol}</span>
              <WatchlistButton symbol={currentSymbol} size="md" />
            {/if}
          </div>
          <div class="flex items-center gap-4">
            <ViewToggle
              viewMode={$uiStore.viewMode}
              onToggle={() => uiStore.toggleViewMode()}
              onSetMode={(mode) => uiStore.setViewMode(mode)}
            />
            <div class="w-96">
              <TickerSearch on:select={handleTickerSelect} />
            </div>
          </div>
        </div>
      </div>
    </header>
  {/if}

  <!-- ChartToolbar Overlay -->
  {#if $uiStore.toolbarVisible}
    <div class="fixed left-4 z-20 liquid-glass-intense rounded-xl animate-liquid-slide-top" style="top: {$uiStore.headerVisible ? '5.5rem' : '1rem'}; right: {$uiStore.sidebarVisible && showAnySidebar ? '420px' : '1rem'}">
      <ChartToolbar
        symbol={currentSymbol}
        period={currentPeriod}
        interval={currentInterval}
        candleCount={$tickerStore.candles.length}
        loading={$tickerStore.loading}
        hasAnalysis={$analysisStore.result !== null}
        provider={$tickerStore.provider}
        on:periodChange={handlePeriodChange}
        on:intervalChange={handleIntervalChange}
        on:resetAnalysis={handleResetAnalysis}
        on:openSettings={handleOpenSettings}
        on:sidebarSelect={handleSidebarSelect}
      />
    </div>
  {/if}

  <!-- Sidebar Overlay -->
  {#if $uiStore.sidebarVisible && showAnySidebar}
    <aside class="fixed top-4 bottom-4 right-4 w-96 z-20 liquid-glass-intense rounded-2xl overflow-hidden animate-liquid-slide-right">
      {#if showProphetSidebar}
        <ProphetSidebar
          priceSummaries={$prophetStore.priceSummaries}
          components={$prophetStore.components}
          horizonToggles={$prophetStore.horizonToggles}
          settings={$prophetStore.settings}
          activeComponentWidget={$prophetStore.activeComponentWidget}
          showComponents={$prophetStore.showComponents}
          symbol={currentSymbol || null}
          loading={$prophetStore.loading}
          fromCache={$prophetStore.fromCache}
          lastAnalyzedAt={$prophetStore.lastAnalyzedAt}
          error={$prophetStore.error}
          onAnalyze={handleProphetAnalyze}
          onToggleHorizon={handleProphetToggleHorizon}
          onToggleComponents={handleProphetToggleComponents}
          onSetActiveComponentWidget={handleProphetSetActiveComponentWidget}
          onUpdateSettings={handleProphetUpdateSettings}
          onResetSettings={handleProphetResetSettings}
          onFetchComponents={handleProphetFetchComponents}
          isActive={$modulesStore.prophet}
          onToggle={() => handleModuleActivate('prophet')}
          xgboostEnabled={$xgboostStore.enabled}
          xgboostLoading={$xgboostStore.loading}
          xgboostSettings={$xgboostStore.settings}
          xgboostFeatureToggles={$xgboostStore.featureToggles}
          xgboostMetrics={$xgboostStore.metrics}
          xgboostFeatureImportance={$xgboostStore.featureImportance}
          onToggleXGBoost={handleToggleXGBoost}
          onAnalyzeXGBoost={handleXGBoostAnalyze}
          onUpdateXGBoostSettings={handleUpdateXGBoostSettings}
          onUpdateXGBoostFeatureToggles={handleUpdateXGBoostFeatureToggles}
          onResetXGBoostSettings={handleResetXGBoostSettings}
        />
      {:else if showHMMSidebar}
        <HMMSidebar
          regime={$hmmStore.currentRegime}
          signal={$hmmStore.currentSignal}
          backtestResult={$hmmStore.backtestResult}
          indicatorToggles={$hmmStore.indicatorToggles}
          indicatorSignals={$hmmStore.indicatorSignals}
          settings={$hmmStore.settings}
          strategyParams={$hmmStore.strategyParams}
          backtestSettings={$hmmStore.backtestSettings}
          modelConfig={$hmmStore.modelConfig}
          featureConfig={$hmmStore.featureConfig}
          rollingRefitConfig={$hmmStore.rollingRefitConfig}
          hmmOptimization={$hmmStore.hmmOptimization}
          strategyOptimization={$hmmStore.strategyOptimization}
          symbol={currentSymbol || null}
          showTradeMarkers={$hmmStore.showTradeMarkers}
          isModelTrained={$hmmStore.isModelTrained}
          loading={$hmmStore.loading}
          trainingLoading={$hmmStore.trainingLoading}
          backtestLoading={$hmmStore.backtestLoading}
          error={$hmmStore.error}
          onTrain={handleHMMTrain}
          onToggleIndicator={handleToggleIndicator}
          onRunBacktest={handleRunBacktest}
          onUpdateSettings={handleUpdateHMMSettings}
          onUpdateStrategyParams={handleUpdateStrategyParams}
          onUpdateBacktestSettings={handleUpdateBacktestSettings}
          onResetStrategyParams={handleResetStrategyParams}
          onUpdateModelConfig={handleUpdateModelConfig}
          onUpdateFeatureConfig={handleUpdateFeatureConfig}
          onUpdateRollingRefitConfig={handleUpdateRollingRefitConfig}
          onStartHMMOptimization={handleStartHMMOptimization}
          onStartStrategyOptimization={handleStartStrategyOptimization}
          onCancelOptimization={handleCancelOptimization}
          onToggleTradeMarkers={handleToggleTradeMarkers}
          onReanalyze={handleReanalyzeHMM}
          isActive={$modulesStore.hmm}
          onToggle={() => handleModuleActivate('hmm')}
        />
      {:else if showElliottSidebar}
        <AnalysisSidebar
          isActive={$modulesStore.elliottWaves}
          onToggle={() => handleModuleActivate('elliottWaves')}
        />
      {/if}
    </aside>
  {/if}

  <!-- Footer Overlay (optional, hidden by default) -->
  {#if $uiStore.footerVisible}
    <footer class="fixed bottom-0 left-4 mb-4 z-20 liquid-glass rounded-xl animate-liquid-slide-bottom" style="right: {$uiStore.sidebarVisible && showAnySidebar ? '420px' : '1rem'}">
      <div class="px-6 py-3">
        <div class="flex items-center justify-between text-xs text-stone-500">
          <span>CommodityCockpit v1.0 – Prophet + XGBoost</span>
          <div class="flex items-center gap-4">
            <span>Powered by TradingView Lightweight Charts</span>
            {#if $tickerStore.provider}
              <span class="flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full {$tickerStore.provider.from_cache ? 'bg-amber-500' : 'bg-emerald-500'}"></span>
                Data: {$tickerStore.provider.provider_display_name}
                {#if $tickerStore.provider.from_cache}
                  <span class="text-stone-600">(cached)</span>
                {/if}
              </span>
            {:else}
              <span>Data: Yahoo Finance</span>
            {/if}
          </div>
        </div>
      </div>
    </footer>
  {/if}

  <!-- CONTROL LAYER (z-30) - Toggle Buttons -->
  <div class="fixed bottom-6 left-1/2 -translate-x-1/2 z-30 flex items-center gap-2" style="bottom: {$uiStore.viewMode === 'chart' ? totalSubplotHeight + 24 : 24}px">
    <div class="liquid-glass-intense rounded-full px-2 py-1.5 flex items-center gap-1">
      <!-- Header Toggle -->
      <button
        class="p-2 rounded-full transition-colors {$uiStore.headerVisible ? 'text-amber-400 bg-amber-500/20' : 'text-stone-500 hover:text-stone-300 hover:bg-stone-700/50'}"
        onclick={() => uiStore.toggleHeader()}
        title="Toggle Header"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
          <line x1="3" y1="9" x2="21" y2="9"/>
        </svg>
      </button>

      <!-- Toolbar Toggle -->
      <button
        class="p-2 rounded-full transition-colors {$uiStore.toolbarVisible ? 'text-amber-400 bg-amber-500/20' : 'text-stone-500 hover:text-stone-300 hover:bg-stone-700/50'}"
        onclick={() => uiStore.toggleToolbar()}
        title="Toggle Toolbar"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="4" y1="6" x2="20" y2="6"/>
          <line x1="4" y1="12" x2="20" y2="12"/>
          <line x1="4" y1="18" x2="20" y2="18"/>
        </svg>
      </button>

      <!-- Sidebar Toggle -->
      <button
        class="p-2 rounded-full transition-colors {$uiStore.sidebarVisible ? 'text-amber-400 bg-amber-500/20' : 'text-stone-500 hover:text-stone-300 hover:bg-stone-700/50'}"
        onclick={() => uiStore.toggleSidebar()}
        title="Toggle Sidebar"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
          <line x1="15" y1="3" x2="15" y2="21"/>
        </svg>
      </button>

      <div class="w-px h-6 bg-stone-600/50 mx-1"></div>

      <!-- Fullscreen Toggle -->
      <button
        class="p-2 rounded-full transition-colors {!$uiStore.headerVisible && !$uiStore.toolbarVisible && !$uiStore.sidebarVisible ? 'text-emerald-400 bg-emerald-500/20' : 'text-stone-500 hover:text-stone-300 hover:bg-stone-700/50'}"
        onclick={toggleFullscreen}
        title="Toggle Fullscreen"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          {#if !$uiStore.headerVisible && !$uiStore.toolbarVisible && !$uiStore.sidebarVisible}
            <path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3"/>
          {:else}
            <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/>
          {/if}
        </svg>
      </button>
    </div>
  </div>

  <!-- Settings Panel -->
  <SettingsPanel
    isOpen={settingsOpen}
    on:close={handleCloseSettings}
    on:apply={handleApplySettings}
  />
</div>
