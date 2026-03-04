<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { createChart, CandlestickSeries, type IChartApi, type ISeriesApi, ColorType, type Range, type Time } from 'lightweight-charts';
  import type { Candle, Wave, Pivot, RiskReward, HigherDegreeAnalysis, ProjectedZone, FibonacciLevel, RegimeDataPoint, IndicatorSeries, IndicatorToggleState, Trade, ProphetForecastSeries, ProphetHorizonToggles } from '$lib/types';
  import { debugStore } from '$lib/stores/debug';
  import { pinnedZonesStore, combinedProjectedZones } from '$lib/stores/pinnedZones';
  import { ElliottWavePrimitive, TargetZonePrimitive, PivotHighlightPrimitive, HigherDegreePrimitive, ProjectedZonePrimitive, RegimeBackgroundPrimitive, IndicatorOverlayPrimitive, VolumeOverlayPrimitive, TradeMarkerPrimitive, ProphetForecastPrimitive, type WaveData } from './primitives';

  /**
   * Normalize timestamp to UTC midnight for consistent comparison across timezones.
   * This ensures BTC-USD (UTC) and other assets (EST/other) use the same reference point.
   */
  function normalizeTimestamp(timestamp: string): number {
    // Extract just the date part (YYYY-MM-DD) and treat as UTC midnight
    const dateOnly = timestamp.substring(0, 10);
    return Math.floor(new Date(dateOnly + 'T00:00:00Z').getTime() / 1000);
  }

  let {
    candles = [],
    waves = [],
    pivots = [],
    riskReward = null,
    higherDegree = null,
    projectedZones = [],
    fibonacciLevels = [],
    selectedPivot = null,
    currentSymbol = '',
    onPivotSelected = (pivot: Pivot) => {},
    onVisibleRangeChange = (range: Range<Time> | null) => {},
    // Manual mode props
    manualPivotIndices = [],
    // HMM props
    regimeData = [],
    indicators = null,
    indicatorToggles = null,
    hmmEnabled = false,
    // Backtest trades
    trades = [],
    showTradeMarkers = false,
    // Prophet props
    prophetForecasts = [],
    prophetHorizonToggles = null,
    prophetEnabled = false,
    prophetTrainingEndDate = null,
    // Backtest props
    prophetBacktestMode = false,
    prophetBacktestCutoffDate = null,
    prophetBacktestTodayDate = null,
  }: {
    candles: Candle[];
    waves: (Wave & { color: string })[];
    pivots: Pivot[];
    riskReward: RiskReward | null;
    higherDegree?: HigherDegreeAnalysis | null;
    projectedZones?: ProjectedZone[];
    fibonacciLevels?: FibonacciLevel[];
    selectedPivot?: Pivot | null;
    currentSymbol?: string;
    onPivotSelected?: (pivot: Pivot) => void;
    onVisibleRangeChange?: (range: Range<Time> | null) => void;
    // Manual mode props
    manualPivotIndices?: number[];
    // HMM props
    regimeData?: RegimeDataPoint[];
    indicators?: IndicatorSeries | null;
    indicatorToggles?: IndicatorToggleState | null;
    hmmEnabled?: boolean;
    // Backtest trades
    trades?: Trade[];
    showTradeMarkers?: boolean;
    // Prophet props
    prophetForecasts?: ProphetForecastSeries[];
    prophetHorizonToggles?: ProphetHorizonToggles | null;
    prophetEnabled?: boolean;
    prophetTrainingEndDate?: string | null;
    // Backtest props
    prophetBacktestMode?: boolean;
    prophetBacktestCutoffDate?: string | null;
    prophetBacktestTodayDate?: string | null;
  } = $props();

  let chartContainer: HTMLDivElement;
  let chart: IChartApi | null = $state<IChartApi | null>(null);
  let candlestickSeries: ISeriesApi<'Candlestick'> | null = $state<ISeriesApi<'Candlestick'> | null>(null);
  let chartReady = $state(false);

  // Primitives
  let wavePrimitive: ElliottWavePrimitive | null = null;
  let zonePrimitive: TargetZonePrimitive | null = null;
  let pivotPrimitive: PivotHighlightPrimitive | null = null;
  let higherDegreePrimitive: HigherDegreePrimitive | null = null;
  let projectedZonePrimitive: ProjectedZonePrimitive | null = null;
  // HMM Primitives
  let regimeBackgroundPrimitive: RegimeBackgroundPrimitive | null = null;
  let indicatorOverlayPrimitive: IndicatorOverlayPrimitive | null = null;
  let volumeOverlayPrimitive: VolumeOverlayPrimitive | null = null;
  // Trade Marker Primitive
  let tradeMarkerPrimitive: TradeMarkerPrimitive | null = null;
  // Prophet Forecast Primitive
  let prophetForecastPrimitive: ProphetForecastPrimitive | null = null;

  function log(message: string, data?: any) {
    if (typeof import.meta !== 'undefined' && !import.meta.env?.DEV) return;
    const entry = { timestamp: new Date().toISOString(), source: 'Chart', message, data };
    console.log(`[Chart] ${message}`, data ?? '');
    debugStore.addLog(entry);
  }

  const chartOptions = {
    layout: {
      background: { type: ColorType.Solid, color: 'transparent' },
      textColor: '#A8A29E',
    },
    grid: {
      vertLines: { color: 'rgba(41, 37, 36, 0.6)' },
      horzLines: { color: 'rgba(41, 37, 36, 0.6)' },
    },
    crosshair: {
      mode: 1,
      vertLine: { color: 'rgba(168, 162, 158, 0.3)', style: 2 },
      horzLine: { color: 'rgba(168, 162, 158, 0.3)', style: 2 },
    },
    rightPriceScale: {
      borderColor: '#292524',
    },
    timeScale: {
      borderColor: '#292524',
      timeVisible: true,
      secondsVisible: false,
      // Allow scrolling beyond data boundaries
      fixLeftEdge: false,
      fixRightEdge: false,
    },
  };

  function findExtremeVisiblePivots(): Pivot[] {
    if (!chart || !pivotPrimitive || pivots.length === 0) return [];

    const visibleRange = chart.timeScale().getVisibleRange();
    if (!visibleRange) return [];

    const rangeFrom = Number(visibleRange.from);
    const rangeTo = Number(visibleRange.to);

    let lowestPivot: Pivot | null = null;
    let lowestPrice = Infinity;
    let highestPivot: Pivot | null = null;
    let highestPrice = -Infinity;

    for (const pivot of pivots) {
      const time = normalizeTimestamp(pivot.timestamp);
      if (time < rangeFrom || time > rangeTo) continue;

      if (pivot.type === 'low' && pivot.price < lowestPrice) {
        lowestPrice = pivot.price;
        lowestPivot = pivot;
      }
      if (pivot.type === 'high' && pivot.price > highestPrice) {
        highestPrice = pivot.price;
        highestPivot = pivot;
      }
    }

    const result: Pivot[] = [];
    if (lowestPivot) result.push(lowestPivot);
    if (highestPivot) result.push(highestPivot);
    return result;
  }

  function updatePreSelectedPivots() {
    if (!pivotPrimitive) return;
    const extremes = findExtremeVisiblePivots();
    pivotPrimitive.setPreSelectedPivots(extremes);
  }

  function initChart() {
    if (!chartContainer || chart) return;

    const width = chartContainer.clientWidth || 800;
    const height = chartContainer.clientHeight || 500;

    log('Initializing chart', { width, height });

    try {
      chart = createChart(chartContainer, {
        ...chartOptions,
        width,
        height,
      });

      // lightweight-charts v5 API: use addSeries with CandlestickSeries
      candlestickSeries = chart.addSeries(CandlestickSeries, {
        upColor: '#34D399',
        downColor: '#F87171',
        borderUpColor: '#34D399',
        borderDownColor: '#F87171',
        wickUpColor: '#34D399',
        wickDownColor: '#F87171',
      });

      // Create and attach primitives
      try {
        wavePrimitive = new ElliottWavePrimitive();
        zonePrimitive = new TargetZonePrimitive();
        pivotPrimitive = new PivotHighlightPrimitive();
        higherDegreePrimitive = new HigherDegreePrimitive();
        projectedZonePrimitive = new ProjectedZonePrimitive();
        // HMM primitives
        regimeBackgroundPrimitive = new RegimeBackgroundPrimitive();
        indicatorOverlayPrimitive = new IndicatorOverlayPrimitive();
        volumeOverlayPrimitive = new VolumeOverlayPrimitive();
        // Trade marker primitive
        tradeMarkerPrimitive = new TradeMarkerPrimitive();
        // Prophet forecast primitive
        prophetForecastPrimitive = new ProphetForecastPrimitive();

        // Attach HMM primitives first (bottom layer)
        candlestickSeries.attachPrimitive(regimeBackgroundPrimitive);
        candlestickSeries.attachPrimitive(volumeOverlayPrimitive);
        candlestickSeries.attachPrimitive(indicatorOverlayPrimitive);
        // Then attach other primitives
        candlestickSeries.attachPrimitive(wavePrimitive);
        candlestickSeries.attachPrimitive(zonePrimitive);
        candlestickSeries.attachPrimitive(pivotPrimitive);
        candlestickSeries.attachPrimitive(higherDegreePrimitive);
        candlestickSeries.attachPrimitive(projectedZonePrimitive);
        // Trade markers on top
        candlestickSeries.attachPrimitive(tradeMarkerPrimitive);
        // Prophet forecast on top
        candlestickSeries.attachPrimitive(prophetForecastPrimitive);

        // Set up pin click callback
        projectedZonePrimitive.setOnPinClick(handlePinClick);

        log('Primitives attached successfully');

        // Subscribe to crosshair move for hover detection on pivots, zones, stop-loss, and trades
        chart.subscribeCrosshairMove((param) => {
          if (!param.point) {
            if (pivotPrimitive) pivotPrimitive.setHoveredPivot(null);
            if (projectedZonePrimitive) projectedZonePrimitive.setHoverPoint(null, null);
            if (zonePrimitive) zonePrimitive.setHoverPoint(null, null);
            if (tradeMarkerPrimitive) tradeMarkerPrimitive.setHoveredTrade(null);
            return;
          }

          if (pivotPrimitive) {
            const nearestPivot = pivotPrimitive.findNearestPivot(param.point.x, param.point.y);
            pivotPrimitive.setHoveredPivot(nearestPivot);
          }

          if (projectedZonePrimitive) {
            projectedZonePrimitive.setHoverPoint(param.point.x, param.point.y);
          }

          if (zonePrimitive) {
            zonePrimitive.setHoverPoint(param.point.x, param.point.y);
          }

          // Check for trade marker hover
          if (tradeMarkerPrimitive) {
            const nearestTrade = tradeMarkerPrimitive.findNearestTrade(param.point.x, param.point.y);
            tradeMarkerPrimitive.setHoveredTrade(nearestTrade?.trade ?? null);
          }
        });

        // Subscribe to visible range changes for pre-selected pivot tracking
        chart.timeScale().subscribeVisibleTimeRangeChange(() => {
          updatePreSelectedPivots();
        });

        // Subscribe to visible time range for subplot syncing (use time-based range for accurate sync)
        chart.timeScale().subscribeVisibleTimeRangeChange((range) => {
          onVisibleRangeChange(range);
        });
      } catch (error) {
        log('ERROR attaching primitives', { error: String(error) });
      }

      // If we already have candles, set them now
      if (candles.length > 0) {
        updateChartData();
      }
    } catch (error) {
      log('ERROR creating chart', { error: String(error) });
    }
  }

  function updateChartData() {
    if (!candlestickSeries || candles.length === 0) return;

    // Reset chartReady - will be set to true after fitContent
    chartReady = false;

    try {
      const chartData = candles.map((c) => ({
        time: normalizeTimestamp(c.timestamp) as any,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }));

      candlestickSeries.setData(chartData);

      // Set visible range to last 6 months + 2 months future, then update overlays
      setTimeout(() => {
        if (chart && chartData.length > 0) {
          const lastCandle = chartData[chartData.length - 1];
          const lastTimestamp = lastCandle.time as number;

          // Calculate 6 months back (approximately 180 days)
          const sixMonthsInSeconds = 180 * 24 * 60 * 60;
          const twoMonthsInSeconds = 60 * 24 * 60 * 60;

          const fromTime = lastTimestamp - sixMonthsInSeconds;
          const toTime = lastTimestamp + twoMonthsInSeconds;

          // Set the visible time range
          chart.timeScale().setVisibleRange({
            from: fromTime as Time,
            to: toTime as Time,
          });

          // Reset price scale to auto-fit (like double-click on price axis)
          chart.priceScale('right').applyOptions({ autoScale: true });
        } else {
          chart?.timeScale().fitContent();
        }

        // Mark chart as ready - coordinates can now be calculated correctly
        chartReady = true;

        // Now that the chart is properly laid out, update waves and risk/reward
        if (waves.length > 0) {
          updateWaves();
        }
        if (riskReward) {
          updateRiskReward();
        }
        if (higherDegree) {
          updateHigherDegree();
        }
        if (projectedZones.length > 0) {
          updateProjectedZones();
        }

        // Update pre-selected pivot after chart is laid out
        updatePreSelectedPivots();
      }, 0);
    } catch (error) {
      log('ERROR setting chart data', { error: String(error) });
    }
  }

  function updateWaves() {
    if (!wavePrimitive) return;

    try {
      const waveData: WaveData[] = waves.map((w) => ({
        ...w,
        color: w.color,
      }));

      wavePrimitive.setWaves(waveData);
    } catch (error) {
      log('ERROR updating waves', { error: String(error) });
    }
  }

  function updateRiskReward() {
    if (!zonePrimitive) return;

    try {
      zonePrimitive.setRiskReward(riskReward);
    } catch (error) {
      log('ERROR updating risk/reward', { error: String(error) });
    }
  }

  function updateHigherDegree() {
    if (!higherDegreePrimitive) return;

    try {
      higherDegreePrimitive.setData(higherDegree);
    } catch (error) {
      log('ERROR updating higher degree', { error: String(error) });
    }
  }

  function updateProjectedZones(zonesToRender?: ProjectedZone[]) {
    if (!projectedZonePrimitive) return;

    try {
      // Use provided zones or fall back to prop
      const zones = zonesToRender ?? projectedZones;

      // Derive direction from wave data
      let direction: 'up' | 'down' = 'up';
      if (waves.length > 0) {
        const firstWave = waves[0];
        direction = firstWave.end_price > firstWave.start_price ? 'up' : 'down';
      }

      // Compute bar interval from candle data for future time extrapolation
      let barIntervalSec = 0;
      let lastBarTimeSec = 0;
      let lastBarIndex = 0;
      if (candles.length >= 2) {
        const n = Math.min(20, candles.length);
        const recent = candles.slice(-n);
        const totalSec = (new Date(recent[recent.length - 1].timestamp).getTime() - new Date(recent[0].timestamp).getTime()) / 1000;
        barIntervalSec = totalSec / (recent.length - 1);
        lastBarTimeSec = normalizeTimestamp(candles[candles.length - 1].timestamp);
        lastBarIndex = candles.length - 1;
      }

      projectedZonePrimitive.setZones(zones, direction, fibonacciLevels, barIntervalSec, lastBarTimeSec, lastBarIndex);
    } catch (error) {
      log('ERROR updating projected zones', { error: String(error) });
    }
  }

  onMount(() => {
    if (!chartContainer) return;

    // Initialize chart with a small delay to ensure container is laid out
    setTimeout(() => {
      initChart();
    }, 50);

    // Handle window resize for fullscreen chart
    function handleResize() {
      if (!chartContainer) return;

      const width = window.innerWidth;
      const height = window.innerHeight;

      if (!chart && width > 0 && height > 0) {
        initChart();
      } else if (chart) {
        chart.applyOptions({ width, height });
      }
    }

    // Also observe container for any layout changes
    const resizeObserver = new ResizeObserver((entries) => {
      if (entries[0]) {
        const { width, height } = entries[0].contentRect;

        if (!chart && width > 0 && height > 0) {
          initChart();
        } else if (chart) {
          chart.applyOptions({ width, height });
        }
      }
    });

    window.addEventListener('resize', handleResize);
    resizeObserver.observe(chartContainer);

    return () => {
      window.removeEventListener('resize', handleResize);
      resizeObserver.disconnect();
    };
  });

  onDestroy(() => {
    chartReady = false;

    if (candlestickSeries) {
      if (wavePrimitive) {
        candlestickSeries.detachPrimitive(wavePrimitive);
        wavePrimitive = null;
      }
      if (zonePrimitive) {
        candlestickSeries.detachPrimitive(zonePrimitive);
        zonePrimitive = null;
      }
      if (pivotPrimitive) {
        candlestickSeries.detachPrimitive(pivotPrimitive);
        pivotPrimitive = null;
      }
      if (higherDegreePrimitive) {
        candlestickSeries.detachPrimitive(higherDegreePrimitive);
        higherDegreePrimitive = null;
      }
      if (projectedZonePrimitive) {
        candlestickSeries.detachPrimitive(projectedZonePrimitive);
        projectedZonePrimitive = null;
      }
      // Detach HMM primitives
      if (regimeBackgroundPrimitive) {
        candlestickSeries.detachPrimitive(regimeBackgroundPrimitive);
        regimeBackgroundPrimitive = null;
      }
      if (indicatorOverlayPrimitive) {
        candlestickSeries.detachPrimitive(indicatorOverlayPrimitive);
        indicatorOverlayPrimitive = null;
      }
      if (volumeOverlayPrimitive) {
        candlestickSeries.detachPrimitive(volumeOverlayPrimitive);
        volumeOverlayPrimitive = null;
      }
      // Detach trade marker primitive
      if (tradeMarkerPrimitive) {
        candlestickSeries.detachPrimitive(tradeMarkerPrimitive);
        tradeMarkerPrimitive = null;
      }
      // Detach prophet forecast primitive
      if (prophetForecastPrimitive) {
        candlestickSeries.detachPrimitive(prophetForecastPrimitive);
        prophetForecastPrimitive = null;
      }
    }

    if (chart) {
      chart.remove();
      chart = null;
    }
  });

  // Update chart data when candles change
  $effect(() => {
    const currentCandles = candles;
    const currentCandleCount = currentCandles.length;

    if (currentCandleCount > 0 && candlestickSeries) {
      updateChartData();
    }
  });

  // Update wave primitive when waves change
  $effect(() => {
    const currentWaves = waves;
    const currentWaveCount = currentWaves.length;
    const isReady = chartReady;

    if (wavePrimitive && isReady && currentWaveCount > 0) {
      updateWaves();
    } else if (wavePrimitive && isReady && currentWaveCount === 0) {
      wavePrimitive.setWaves([]);
    }
  });

  // Update risk/reward primitive when riskReward changes
  $effect(() => {
    const currentRiskReward = riskReward;
    const isReady = chartReady;

    if (zonePrimitive && isReady) {
      updateRiskReward();
    }
  });

  // Update pivot primitive when pivots change
  $effect(() => {
    const currentPivots = pivots;
    const currentSelectedPivot = selectedPivot;
    const isReady = chartReady;

    if (pivotPrimitive && isReady) {
      pivotPrimitive.setPivots(currentPivots);
      pivotPrimitive.setSelectedPivot(currentSelectedPivot);
      // Update pre-selected after pivots change
      updatePreSelectedPivots();
    }
  });

  // Update manual pivot indices on pivot primitive
  $effect(() => {
    const currentManualIndices = manualPivotIndices;
    const isReady = chartReady;

    if (pivotPrimitive && isReady) {
      pivotPrimitive.setManualPivotIndices(currentManualIndices);
    }
  });

  // Update higher degree primitive
  $effect(() => {
    const currentHigherDegree = higherDegree;
    const isReady = chartReady;

    if (higherDegreePrimitive && isReady) {
      updateHigherDegree();
    }
  });

  // Update projected zones primitive (using combined zones from store)
  $effect(() => {
    const combinedZones = $combinedProjectedZones;
    const combinedZoneCount = combinedZones.length;
    const isReady = chartReady;

    if (projectedZonePrimitive && isReady) {
      updateProjectedZones(combinedZones);
    }
  });

  // Update HMM regime background primitive
  $effect(() => {
    const currentRegimeData = regimeData;
    const currentHmmEnabled = hmmEnabled;
    const isReady = chartReady;

    if (regimeBackgroundPrimitive && isReady) {
      regimeBackgroundPrimitive.setVisible(currentHmmEnabled);
      if (currentHmmEnabled && currentRegimeData.length > 0) {
        regimeBackgroundPrimitive.setRegimeData(currentRegimeData);
      } else {
        regimeBackgroundPrimitive.setRegimeData([]);
      }
    }
  });

  // Update HMM indicator overlay primitive
  $effect(() => {
    const currentIndicators = indicators;
    const currentToggles = indicatorToggles;
    const currentHmmEnabled = hmmEnabled;
    const isReady = chartReady;

    if (indicatorOverlayPrimitive && isReady && currentHmmEnabled && currentIndicators) {
      // Set indicator data
      indicatorOverlayPrimitive.setIndicatorData({
        sma_20: currentIndicators.sma_20,
        sma_50: currentIndicators.sma_50,
        sma_200: currentIndicators.sma_200,
        ema_12: currentIndicators.ema_12,
        ema_26: currentIndicators.ema_26,
        bb_upper: currentIndicators.bb_upper,
        bb_middle: currentIndicators.bb_middle,
        bb_lower: currentIndicators.bb_lower,
      });

      // Set toggles
      if (currentToggles) {
        indicatorOverlayPrimitive.setToggles({
          sma_20: currentToggles.sma_20,
          sma_50: currentToggles.sma_50,
          sma_200: currentToggles.sma_200,
          ema_12: currentToggles.ema_12,
          ema_26: currentToggles.ema_26,
          bollinger: currentToggles.bollinger,
        });
      }
    } else if (indicatorOverlayPrimitive && isReady) {
      // Clear all toggles when HMM is disabled
      indicatorOverlayPrimitive.setToggles({
        sma_20: false,
        sma_50: false,
        sma_200: false,
        ema_12: false,
        ema_26: false,
        bollinger: false,
      });
    }
  });

  // Update volume overlay primitive
  $effect(() => {
    const currentCandles = candles;
    const currentToggles = indicatorToggles;
    const currentHmmEnabled = hmmEnabled;
    const isReady = chartReady;

    if (volumeOverlayPrimitive && isReady) {
      // Volume is shown when HMM is enabled AND volume toggle is on
      const showVolume = currentHmmEnabled && currentToggles?.volume;
      volumeOverlayPrimitive.setVisible(showVolume ?? false);

      if (showVolume && currentCandles.length > 0) {
        volumeOverlayPrimitive.setCandles(currentCandles);
      }
    }
  });

  // Update trade marker primitive
  $effect(() => {
    const currentTrades = trades;
    const currentHmmEnabled = hmmEnabled;
    const currentShowTradeMarkers = showTradeMarkers;
    const isReady = chartReady;

    if (tradeMarkerPrimitive && isReady) {
      // Show trades only when HMM is enabled AND showTradeMarkers is true
      const shouldShowTrades = currentHmmEnabled && currentShowTradeMarkers;
      tradeMarkerPrimitive.setVisible(shouldShowTrades);
      if (shouldShowTrades && currentTrades.length > 0) {
        tradeMarkerPrimitive.setTrades(currentTrades);
      } else {
        tradeMarkerPrimitive.setTrades([]);
      }
    }
  });

  // Update Prophet forecast primitive
  $effect(() => {
    const currentForecasts = prophetForecasts;
    const currentToggles = prophetHorizonToggles;
    const currentProphetEnabled = prophetEnabled;
    const currentTrainingEndDate = prophetTrainingEndDate;
    const currentBacktestMode = prophetBacktestMode;
    const currentBacktestCutoffDate = prophetBacktestCutoffDate;
    const currentBacktestTodayDate = prophetBacktestTodayDate;
    const isReady = chartReady;

    log('Prophet effect', {
      prophetEnabled: currentProphetEnabled,
      forecastCount: currentForecasts.length,
      isReady,
      hasPrimitive: !!prophetForecastPrimitive,
      trainingEndDate: currentTrainingEndDate,
      backtestMode: currentBacktestMode,
    });

    if (prophetForecastPrimitive && isReady && chart) {
      // Handle backtest mode
      if (currentBacktestMode && currentBacktestCutoffDate && currentBacktestTodayDate) {
        prophetForecastPrimitive.setBacktestMode(true, currentBacktestCutoffDate, currentBacktestTodayDate);
      } else {
        prophetForecastPrimitive.clearBacktestMode();
      }

      if (currentProphetEnabled && currentForecasts.length > 0) {
        log('Setting Prophet forecasts', {
          horizons: currentForecasts.map(f => f.horizon),
          seriesLengths: currentForecasts.map(f => f.series.length),
        });

        // Debug: Compare candle and Prophet timestamp formats
        if (candles.length > 0 && currentForecasts[0]?.series.length > 0) {
          const sampleCandle = candles[candles.length - 1];
          const sampleProphet = currentForecasts[0].series[0];
          const candleTs = normalizeTimestamp(sampleCandle.timestamp);
          const prophetTs = normalizeTimestamp(sampleProphet.timestamp);
          log('Timestamp comparison', {
            candleTimestamp: sampleCandle.timestamp,
            candleUnix: candleTs,
            prophetTimestamp: sampleProphet.timestamp,
            prophetUnix: prophetTs,
            candleCoord: chart.timeScale().timeToCoordinate(candleTs as Time),
            prophetCoord: chart.timeScale().timeToCoordinate(prophetTs as Time),
          });
        }

        prophetForecastPrimitive.setForecasts(currentForecasts, currentTrainingEndDate ?? undefined);
        if (currentToggles) {
          prophetForecastPrimitive.setToggles(currentToggles);
        }

        // Calculate how many days the forecast extends into the future
        // and set appropriate right offset to show the forecast
        let maxForecastDate: number | null = null;
        let lastCandleDate: number | null = null;

        if (candles.length > 0) {
          lastCandleDate = normalizeTimestamp(candles[candles.length - 1].timestamp);
        }

        for (const forecast of currentForecasts) {
          if (forecast.series.length > 0) {
            const lastPoint = forecast.series[forecast.series.length - 1];
            const timestamp = normalizeTimestamp(lastPoint.timestamp);
            if (maxForecastDate === null || timestamp > maxForecastDate) {
              maxForecastDate = timestamp;
            }
          }
        }

        if (maxForecastDate !== null && lastCandleDate !== null && maxForecastDate > lastCandleDate) {
          // Calculate how many days the forecast extends
          const forecastDays = Math.ceil((maxForecastDate - lastCandleDate) / (24 * 60 * 60));

          log('Forecast extends beyond candles', {
            lastCandleDate,
            maxForecastDate,
            forecastDays,
          });

          // Use setVisibleLogicalRange to show forecast area
          // Get current logical range and extend it
          const logicalRange = chart.timeScale().getVisibleLogicalRange();
          if (logicalRange) {
            // Add bars to the right for the forecast period
            // Each bar is typically one day for daily data
            const newTo = logicalRange.to + forecastDays + 10; // Add 10 bars padding
            chart.timeScale().setVisibleLogicalRange({
              from: logicalRange.from,
              to: newTo,
            });
          }
        }
      } else {
        prophetForecastPrimitive.clear();
      }
    }
  });

  // Handle pin button click on projected zones
  function handlePinClick(zone: ProjectedZone, isPinned: boolean) {
    log('Pin click', { zone: zone.label, isPinned, currentSymbol });

    if (isPinned && zone.id) {
      // Unpin the zone
      pinnedZonesStore.unpinZone(zone.id);
      log('Zone unpinned', { zoneId: zone.id });
    } else if (!isPinned && currentSymbol) {
      // Pin the zone
      const newId = pinnedZonesStore.pinZone(zone, currentSymbol);
      log('Zone pinned', { zoneId: newId, symbol: currentSymbol });
    }
  }

  // Handle click on chart for pivot selection (always active, both HIGH and LOW pivots)
  function handleChartClick(event: MouseEvent) {
    if (!chartContainer) return;

    const rect = chartContainer.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    // First check if a pin button was clicked
    if (projectedZonePrimitive?.checkPinButtonClick(x, y)) {
      // Pin button click handled, don't process pivot selection
      return;
    }

    // Otherwise check for pivot selection
    if (pivotPrimitive) {
      const nearestPivot = pivotPrimitive.findNearestPivot(x, y);
      if (nearestPivot) {
        log('Pivot clicked', { pivot: nearestPivot });
        onPivotSelected(nearestPivot);
      }
    }
  }
</script>

<div class="absolute inset-0">
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    bind:this={chartContainer}
    class="absolute inset-0 cursor-crosshair"
    onclick={handleChartClick}
  ></div>
  {#if candles.length === 0}
    <div class="absolute inset-0 flex items-center justify-center text-text-muted">
      <div class="liquid-glass rounded-2xl px-8 py-6 text-center">
        <svg class="w-16 h-16 mx-auto text-stone-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
        <p class="text-lg font-medium text-stone-400">Search for a ticker to view chart</p>
        <p class="text-sm text-stone-600 mt-1">Use the search bar above to get started</p>
      </div>
    </div>
  {/if}
</div>
