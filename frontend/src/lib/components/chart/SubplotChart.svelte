<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { createChart, LineSeries, HistogramSeries, type IChartApi, type ISeriesApi, ColorType, type Range, type Time } from 'lightweight-charts';
  import type { IndicatorDataPoint } from '$lib/types';
  import { subplotHeightsStore } from '$lib/stores/subplotHeights';

  type SubplotType = 'rsi' | 'macd' | 'adx' | 'volume' | 'atr';

  let {
    type,
    data = [],
    secondaryData = [],
    tertiaryData = [],
    histogramData = [],
    visibleRange = null,
    onHeightChange,
  }: {
    type: SubplotType;
    data: IndicatorDataPoint[];
    secondaryData?: IndicatorDataPoint[];
    tertiaryData?: IndicatorDataPoint[];
    histogramData?: IndicatorDataPoint[];
    visibleRange?: Range<Time> | null;
    onHeightChange?: (type: SubplotType, height: number) => void;
  } = $props();

  let chartContainer: HTMLDivElement;
  let chart: IChartApi | null = $state<IChartApi | null>(null);
  let mainSeries: ISeriesApi<'Line'> | null = $state<ISeriesApi<'Line'> | null>(null);
  let secondSeries: ISeriesApi<'Line'> | null = $state<ISeriesApi<'Line'> | null>(null);
  let thirdSeries: ISeriesApi<'Line'> | null = $state<ISeriesApi<'Line'> | null>(null);
  let histSeries: ISeriesApi<'Histogram'> | null = $state<ISeriesApi<'Histogram'> | null>(null);

  // Drag state
  let isDragging = $state(false);
  let startY = $state(0);
  let startHeight = $state(0);
  let currentHeight = $state(80);

  // Subscribe to heights store
  $effect(() => {
    const unsubscribe = subplotHeightsStore.subscribe((heights) => {
      currentHeight = heights[type];
    });
    return unsubscribe;
  });

  // Configuration per indicator type
  const CONFIG: Record<SubplotType, {
    title: string;
    mainColor: string;
    secondColor?: string;
    thirdColor?: string;
    histColor?: string;
    levels?: { value: number; color: string; label: string }[];
    minValue?: number;
    maxValue?: number;
  }> = {
    rsi: {
      title: 'RSI',
      mainColor: '#9C27B0',
      levels: [
        { value: 70, color: 'rgba(239, 68, 68, 0.5)', label: 'Overbought' },
        { value: 30, color: 'rgba(16, 185, 129, 0.5)', label: 'Oversold' },
        { value: 50, color: 'rgba(148, 163, 184, 0.3)', label: 'Mid' },
      ],
      minValue: 0,
      maxValue: 100,
    },
    macd: {
      title: 'MACD',
      mainColor: '#2196F3',
      secondColor: '#FF9800',
      histColor: '#4CAF50',
    },
    adx: {
      title: 'ADX',
      mainColor: '#FFEB3B',
      secondColor: '#4CAF50',
      thirdColor: '#F44336',
      levels: [
        { value: 25, color: 'rgba(148, 163, 184, 0.3)', label: 'Trend' },
      ],
    },
    volume: {
      title: 'Volume',
      mainColor: '#64B5F6',
    },
    atr: {
      title: 'ATR',
      mainColor: '#FF7043',
    },
  };

  const chartOptions = {
    layout: {
      background: { type: ColorType.Solid, color: 'transparent' },
      textColor: '#A8A29E',
    },
    grid: {
      vertLines: { color: 'rgba(41, 37, 36, 0.4)' },
      horzLines: { color: 'rgba(41, 37, 36, 0.4)' },
    },
    crosshair: {
      mode: 1,
      vertLine: { color: 'rgba(168, 162, 158, 0.3)', style: 2 },
      horzLine: { color: 'rgba(168, 162, 158, 0.3)', style: 2 },
    },
    rightPriceScale: {
      borderColor: '#292524',
      scaleMargins: {
        top: 0.1,
        bottom: 0.1,
      },
    },
    timeScale: {
      visible: false,
      borderColor: '#292524',
      // Allow scrolling beyond data boundaries (sync with main chart)
      fixLeftEdge: false,
      fixRightEdge: false,
    },
    // Disable direct user interaction - sync is controlled by main chart
    handleScroll: false,
    handleScale: false,
  };

  function initChart() {
    if (!chartContainer || chart) return;

    const width = chartContainer.clientWidth || 800;
    const config = CONFIG[type];

    chart = createChart(chartContainer, {
      ...chartOptions,
      width,
      height: currentHeight,
    });

    // Add main series
    if (type === 'volume') {
      histSeries = chart.addSeries(HistogramSeries, {
        color: config.mainColor,
        priceFormat: {
          type: 'volume',
        },
      });
    } else {
      mainSeries = chart.addSeries(LineSeries, {
        color: config.mainColor,
        lineWidth: 1.5,
        priceFormat: {
          type: 'price',
          precision: 2,
          minMove: 0.01,
        },
      });

      if (config.secondColor) {
        secondSeries = chart.addSeries(LineSeries, {
          color: config.secondColor,
          lineWidth: 1,
        });
      }

      if (config.thirdColor) {
        thirdSeries = chart.addSeries(LineSeries, {
          color: config.thirdColor,
          lineWidth: 1,
        });
      }

      if (type === 'macd' && config.histColor) {
        histSeries = chart.addSeries(HistogramSeries, {
          color: config.histColor,
        });
      }
    }

    if (config.minValue !== undefined && config.maxValue !== undefined) {
      chart.priceScale('right').applyOptions({
        autoScale: false,
      });
    }

    updateData();
  }

  function updateData() {
    if (!chart) return;

    const convertData = (points: IndicatorDataPoint[]) =>
      points.map((p) => ({
        time: Math.floor(new Date(p.timestamp).getTime() / 1000) as any,
        value: p.value,
      }));

    const convertHistData = (points: IndicatorDataPoint[]) =>
      points.map((p) => ({
        time: Math.floor(new Date(p.timestamp).getTime() / 1000) as any,
        value: p.value,
        color: p.value >= 0 ? 'rgba(76, 175, 80, 0.7)' : 'rgba(244, 67, 54, 0.7)',
      }));

    if (type === 'volume' && histSeries && data.length > 0) {
      histSeries.setData(convertData(data));
    } else {
      if (mainSeries && data.length > 0) {
        mainSeries.setData(convertData(data));
      }

      if (secondSeries && secondaryData.length > 0) {
        secondSeries.setData(convertData(secondaryData));
      }

      if (thirdSeries && tertiaryData.length > 0) {
        thirdSeries.setData(convertData(tertiaryData));
      }

      if (histSeries && histogramData.length > 0) {
        histSeries.setData(convertHistData(histogramData));
      }
    }

    // Apply visible range from main chart (using time-based range for accurate sync)
    // Always apply the range if provided, otherwise fit content only on initial load
    if (visibleRange) {
      try {
        chart.timeScale().setVisibleRange(visibleRange);
      } catch (e) {
        // Range might be outside data bounds, ignore
        console.debug('[SubplotChart] Could not apply visible range:', e);
      }
    }
  }

  // Sync visible range when it changes from main chart (using time-based range)
  $effect(() => {
    const range = visibleRange;
    if (chart && range) {
      try {
        chart.timeScale().setVisibleRange(range);
      } catch (e) {
        // Range might be outside data bounds - this can happen when scrolling
        // beyond data boundaries, which is expected behavior
      }
    }
  });

  // Update chart height when currentHeight changes
  $effect(() => {
    const height = currentHeight;
    if (chart) {
      chart.applyOptions({ height });
    }
  });

  // Drag handlers
  function handleDragStart(e: MouseEvent) {
    isDragging = true;
    startY = e.clientY;
    startHeight = currentHeight;
    document.body.style.cursor = 'ns-resize';
    document.body.style.userSelect = 'none';
  }

  function handleDragMove(e: MouseEvent) {
    if (!isDragging) return;

    const deltaY = startY - e.clientY;
    const newHeight = startHeight + deltaY;
    const clampedHeight = Math.max(subplotHeightsStore.getMinHeight(), Math.min(subplotHeightsStore.getMaxHeight(), newHeight));

    subplotHeightsStore.setHeight(type, clampedHeight);
    onHeightChange?.(type, clampedHeight);
  }

  function handleDragEnd() {
    if (isDragging) {
      isDragging = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    }
  }

  onMount(() => {
    if (!chartContainer) return;

    setTimeout(() => {
      initChart();
    }, 50);

    const resizeObserver = new ResizeObserver((entries) => {
      if (entries[0] && chart) {
        const { width } = entries[0].contentRect;
        chart.applyOptions({ width });
      }
    });

    resizeObserver.observe(chartContainer);

    // Add global mouse event listeners for dragging
    window.addEventListener('mousemove', handleDragMove);
    window.addEventListener('mouseup', handleDragEnd);

    return () => {
      resizeObserver.disconnect();
      window.removeEventListener('mousemove', handleDragMove);
      window.removeEventListener('mouseup', handleDragEnd);
    };
  });

  onDestroy(() => {
    if (chart) {
      chart.remove();
      chart = null;
    }
  });

  // Update data when props change
  $effect(() => {
    const currentData = data;
    const currentSecondary = secondaryData;
    const currentTertiary = tertiaryData;
    const currentHist = histogramData;

    if (chart && currentData.length > 0) {
      updateData();
    }
  });
</script>

<div class="relative liquid-glass-subtle" style="height: {currentHeight}px;">
  <!-- Drag Handle at top -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="absolute top-0 left-0 right-0 h-2 cursor-ns-resize z-20 group"
    onmousedown={handleDragStart}
  >
    <div class="absolute inset-x-0 top-0 h-0.5 bg-stone-600/30 group-hover:bg-amber-500/50 transition-colors {isDragging ? 'bg-amber-500/70' : ''}"></div>
    <div class="absolute left-1/2 -translate-x-1/2 top-0.5 w-8 h-1 rounded-full bg-stone-600/50 group-hover:bg-amber-500/60 transition-colors {isDragging ? 'bg-amber-500/80' : ''}"></div>
  </div>

  <!-- Label -->
  <div class="absolute top-2 left-3 z-10 text-xs text-text-muted font-medium px-1.5 py-0.5 rounded liquid-glass-subtle">
    {CONFIG[type].title}
  </div>

  <!-- Chart Container -->
  <div
    bind:this={chartContainer}
    class="w-full h-full pt-1"
  ></div>
</div>
