/**
 * Prophet Forecast Primitive for TradingView Lightweight Charts.
 *
 * Draws Prophet forecast lines with confidence bands for three horizons:
 * - Long-term (blue)
 * - Mid-term (green)
 * - Short-term (red)
 *
 * Each horizon can be toggled independently.
 */

import type {
  ISeriesPrimitive,
  SeriesAttachedParameter,
  Time,
  IPrimitivePaneView,
  IPrimitivePaneRenderer,
  PrimitiveHoveredItem,
  PrimitivePaneViewZOrder,
} from 'lightweight-charts';
import type { ProphetForecastSeries, ProphetHorizonToggles } from '$lib/types';

// Horizon colors - confidence bands are kept subtle to not obscure price action
const HORIZON_COLORS = {
  long_term: {
    line: '#1f77b4',        // Blue
    fill: 'rgba(31, 119, 180, 0.06)',   // Very subtle fill
    border: 'rgba(31, 119, 180, 0.25)', // Softer border
  },
  mid_term: {
    line: '#2ca02c',        // Green
    fill: 'rgba(44, 160, 44, 0.06)',
    border: 'rgba(44, 160, 44, 0.25)',
  },
  short_term: {
    line: '#d62728',        // Red
    fill: 'rgba(214, 39, 40, 0.06)',
    border: 'rgba(214, 39, 40, 0.25)',
  },
  combined: {
    line: '#8B7355',        // Calm brown - XGBoost combined forecast
    fill: 'rgba(139, 115, 85, 0.12)',   // Slightly more visible for confidence
    border: 'rgba(139, 115, 85, 0.35)',
  },
  backtest: {
    line: '#9333ea',        // Purple - Backtest forecast
    fill: 'rgba(147, 51, 234, 0.08)',
    border: 'rgba(147, 51, 234, 0.30)',
  },
};

// Backtest marker colors
const BACKTEST_MARKERS = {
  cutoff: '#9333ea',  // Purple - cutoff date
  today: '#22c55e',   // Green - today's date
};

interface Point {
  x: number;
  y: number;
}

interface LineSegment {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

interface ForecastLineData {
  horizon: string;
  mainLine: LineSegment[];
  upperBound: LineSegment[];
  lowerBound: LineSegment[];
  fillPolygon: Point[];
  color: typeof HORIZON_COLORS['long_term'];
  lineWidth: number;
  historicalEndX: number | null;
}

interface BacktestMarkers {
  cutoffX: number | null;
  todayX: number | null;
}

// Renderer
class ProphetForecastRenderer implements IPrimitivePaneRenderer {
  private _lines: ForecastLineData[] = [];
  private _backtestMarkers: BacktestMarkers | null = null;

  update(lines: ForecastLineData[], backtestMarkers?: BacktestMarkers | null): void {
    this._lines = lines;
    this._backtestMarkers = backtestMarkers ?? null;
  }

  draw(target: any): void {
    try {
      target.useMediaCoordinateSpace((scope: any) => {
        const ctx = scope.context as CanvasRenderingContext2D;
        this._drawContent(ctx);
      });
    } catch {
      // Drawing error - silently ignore
    }
  }

  private _drawContent(ctx: CanvasRenderingContext2D): void {
    // Draw each forecast horizon
    for (const line of this._lines) {
      this._drawForecastLine(ctx, line);
    }

    // Draw backtest markers if present
    if (this._backtestMarkers) {
      this._drawBacktestMarkers(ctx, this._backtestMarkers);
    }
  }

  private _drawBacktestMarkers(ctx: CanvasRenderingContext2D, markers: BacktestMarkers): void {
    const chartHeight = ctx.canvas.height;

    // Draw cutoff date line (purple dashed)
    if (markers.cutoffX !== null) {
      ctx.save();
      ctx.strokeStyle = BACKTEST_MARKERS.cutoff;
      ctx.lineWidth = 2;
      ctx.setLineDash([6, 4]);
      ctx.globalAlpha = 0.8;

      ctx.beginPath();
      ctx.moveTo(markers.cutoffX, 0);
      ctx.lineTo(markers.cutoffX, chartHeight);
      ctx.stroke();

      // Draw label
      ctx.setLineDash([]);
      ctx.fillStyle = BACKTEST_MARKERS.cutoff;
      ctx.font = '10px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('Cutoff', markers.cutoffX, 12);

      ctx.restore();
    }

    // Draw today line (green solid)
    if (markers.todayX !== null) {
      ctx.save();
      ctx.strokeStyle = BACKTEST_MARKERS.today;
      ctx.lineWidth = 2;
      ctx.setLineDash([]);
      ctx.globalAlpha = 0.8;

      ctx.beginPath();
      ctx.moveTo(markers.todayX, 0);
      ctx.lineTo(markers.todayX, chartHeight);
      ctx.stroke();

      // Draw label
      ctx.fillStyle = BACKTEST_MARKERS.today;
      ctx.font = '10px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('Heute', markers.todayX, 12);

      ctx.restore();
    }
  }

  private _drawForecastLine(ctx: CanvasRenderingContext2D, data: ForecastLineData): void {
    // Draw confidence band fill
    if (data.fillPolygon.length > 0) {
      ctx.save();
      ctx.beginPath();
      ctx.moveTo(data.fillPolygon[0].x, data.fillPolygon[0].y);
      for (let i = 1; i < data.fillPolygon.length; i++) {
        ctx.lineTo(data.fillPolygon[i].x, data.fillPolygon[i].y);
      }
      ctx.closePath();
      ctx.fillStyle = data.color.fill;
      ctx.fill();
      ctx.restore();
    }

    // Draw upper bound (dashed)
    if (data.upperBound.length > 0) {
      ctx.save();
      ctx.strokeStyle = data.color.border;
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.lineCap = 'round';
      ctx.beginPath();
      let isFirst = true;
      for (const seg of data.upperBound) {
        if (isFirst) {
          ctx.moveTo(seg.x1, seg.y1);
          isFirst = false;
        }
        ctx.lineTo(seg.x2, seg.y2);
      }
      ctx.stroke();
      ctx.restore();
    }

    // Draw lower bound (dashed)
    if (data.lowerBound.length > 0) {
      ctx.save();
      ctx.strokeStyle = data.color.border;
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.lineCap = 'round';
      ctx.beginPath();
      let isFirst = true;
      for (const seg of data.lowerBound) {
        if (isFirst) {
          ctx.moveTo(seg.x1, seg.y1);
          isFirst = false;
        }
        ctx.lineTo(seg.x2, seg.y2);
      }
      ctx.stroke();
      ctx.restore();
    }

    // Draw main forecast line
    if (data.mainLine.length > 0) {
      ctx.save();
      ctx.strokeStyle = data.color.line;
      ctx.lineWidth = data.lineWidth;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.beginPath();
      let isFirst = true;
      for (const seg of data.mainLine) {
        if (isFirst) {
          ctx.moveTo(seg.x1, seg.y1);
          isFirst = false;
        }
        ctx.lineTo(seg.x2, seg.y2);
      }
      ctx.stroke();
      ctx.restore();

      // Draw vertical line at historical end (forecast start)
      if (data.historicalEndX !== null) {
        ctx.save();
        ctx.strokeStyle = data.color.line;
        ctx.lineWidth = 1;
        ctx.setLineDash([2, 2]);
        ctx.globalAlpha = 0.5;

        // Get chart height from context
        const chartHeight = ctx.canvas.height;

        ctx.beginPath();
        ctx.moveTo(data.historicalEndX, 0);
        ctx.lineTo(data.historicalEndX, chartHeight);
        ctx.stroke();
        ctx.restore();
      }
    }
  }
}

// Pane View
class ProphetForecastPaneView implements IPrimitivePaneView {
  private _source: ProphetForecastPrimitive;
  private _renderer: ProphetForecastRenderer;

  constructor(source: ProphetForecastPrimitive) {
    this._source = source;
    this._renderer = new ProphetForecastRenderer();
  }

  update(): void {
    try {
      const lines = this._source.getLines();
      const backtestMarkers = this._source.getBacktestMarkers();
      this._renderer.update(lines, backtestMarkers);
    } catch {
      // Update error - silently ignore
    }
  }

  renderer(): IPrimitivePaneRenderer {
    this.update();
    return this._renderer;
  }

  zOrder(): PrimitivePaneViewZOrder {
    return 'top'; // Draw on top of candlesticks
  }
}

// Main Primitive
export class ProphetForecastPrimitive implements ISeriesPrimitive<Time> {
  private _series: SeriesAttachedParameter<Time>['series'] | null = null;
  private _chart: SeriesAttachedParameter<Time>['chart'] | null = null;
  private _requestUpdate: SeriesAttachedParameter<Time>['requestUpdate'] | null = null;

  private _paneView: ProphetForecastPaneView;

  // Forecast data
  private _forecasts: ProphetForecastSeries[] = [];
  private _historicalEndDate: string | null = null;

  // Toggle states
  private _toggles: ProphetHorizonToggles = {
    long_term: true,
    mid_term: true,
    short_term: true,
  };

  // Backtest mode state
  private _backtestMode: boolean = false;
  private _backtestCutoffDate: string | null = null;
  private _backtestTodayDate: string | null = null;

  constructor() {
    this._paneView = new ProphetForecastPaneView(this);
  }

  attached(param: SeriesAttachedParameter<Time>): void {
    this._series = param.series;
    this._chart = param.chart;
    this._requestUpdate = param.requestUpdate;
  }

  detached(): void {
    this._series = null;
    this._chart = null;
    this._requestUpdate = null;
  }

  paneViews(): readonly IPrimitivePaneView[] {
    return [this._paneView];
  }

  hitTest(): PrimitiveHoveredItem | null {
    return null;
  }

  // Data setters
  setForecasts(forecasts: ProphetForecastSeries[], historicalEndDate?: string): void {
    this._forecasts = forecasts;
    if (historicalEndDate) {
      this._historicalEndDate = historicalEndDate;
    }
    this._requestUpdate?.();
  }

  // Toggle setters
  setToggles(toggles: Partial<ProphetHorizonToggles>): void {
    if (toggles.long_term !== undefined) this._toggles.long_term = toggles.long_term;
    if (toggles.mid_term !== undefined) this._toggles.mid_term = toggles.mid_term;
    if (toggles.short_term !== undefined) this._toggles.short_term = toggles.short_term;
    this._requestUpdate?.();
  }

  // Clear data
  clear(): void {
    this._forecasts = [];
    this._historicalEndDate = null;
    this._backtestMode = false;
    this._backtestCutoffDate = null;
    this._backtestTodayDate = null;
    this._requestUpdate?.();
  }

  // Backtest mode setters
  setBacktestMode(enabled: boolean, cutoffDate?: string, todayDate?: string): void {
    this._backtestMode = enabled;
    this._backtestCutoffDate = cutoffDate ?? null;
    this._backtestTodayDate = todayDate ?? null;
    this._requestUpdate?.();
  }

  clearBacktestMode(): void {
    this._backtestMode = false;
    this._backtestCutoffDate = null;
    this._backtestTodayDate = null;
    this._requestUpdate?.();
  }

  // Get backtest markers for rendering
  getBacktestMarkers(): BacktestMarkers | null {
    if (!this._backtestMode || !this._chart) return null;

    const timeScale = this._chart.timeScale();

    let cutoffX: number | null = null;
    let todayX: number | null = null;

    if (this._backtestCutoffDate) {
      const cutoffTs = this._normalizeTimestamp(this._backtestCutoffDate);
      cutoffX = timeScale.timeToCoordinate(cutoffTs as Time);
    }

    if (this._backtestTodayDate) {
      const todayTs = this._normalizeTimestamp(this._backtestTodayDate);
      todayX = timeScale.timeToCoordinate(todayTs as Time);
    }

    return { cutoffX, todayX };
  }

  private _normalizeTimestamp(timestamp: string): number {
    // Normalize timestamp to UTC midnight for consistent comparison
    // Handles both "2026-03-02" (date only) and "2026-03-02T00:00:00-05:00" (with timezone)
    // Extract just the date part (YYYY-MM-DD) and treat as UTC midnight
    const dateOnly = timestamp.substring(0, 10); // "YYYY-MM-DD"
    return Math.floor(new Date(dateOnly + 'T00:00:00Z').getTime() / 1000);
  }

  private _convertToSegments(
    data: Array<{ timestamp: string; value: number }>
  ): LineSegment[] {
    if (!this._series || !this._chart || data.length < 2) return [];

    const timeScale = this._chart.timeScale();
    const segments: LineSegment[] = [];

    // Calculate pixels per second for extrapolating future coordinates
    // We need to find the bar spacing to properly extrapolate
    let pixelsPerSecond: number | null = null;
    let lastValidX: number | null = null;
    let lastValidTime: number | null = null;

    // First pass: find valid coordinates and calculate the time-to-pixel ratio
    // Use the last few historical points for better accuracy
    const validCoords: Array<{ time: number; x: number }> = [];

    for (let i = data.length - 1; i >= 0 && validCoords.length < 10; i--) {
      const t = this._normalizeTimestamp(data[i].timestamp);
      const x = timeScale.timeToCoordinate(t as Time);
      if (x !== null) {
        validCoords.unshift({ time: t, x });
      }
    }

    // Calculate pixels per second from valid coordinates
    if (validCoords.length >= 2) {
      const first = validCoords[0];
      const last = validCoords[validCoords.length - 1];
      const timeDiff = last.time - first.time;
      const xDiff = last.x - first.x;
      if (timeDiff > 0) {
        pixelsPerSecond = xDiff / timeDiff;
        lastValidX = last.x;
        lastValidTime = last.time;
      }
    }

    // Helper function to get x coordinate (with extrapolation for future dates)
    const getXCoordinate = (timestamp: number): number | null => {
      // First try the native method
      const x = timeScale.timeToCoordinate(timestamp as Time);
      if (x !== null) return x;

      // If null and we have reference points, extrapolate
      if (pixelsPerSecond !== null && lastValidX !== null && lastValidTime !== null) {
        const timeDiff = timestamp - lastValidTime;
        return lastValidX + (timeDiff * pixelsPerSecond);
      }

      return null;
    };

    for (let i = 0; i < data.length - 1; i++) {
      const p1 = data[i];
      const p2 = data[i + 1];

      const t1 = this._normalizeTimestamp(p1.timestamp);
      const t2 = this._normalizeTimestamp(p2.timestamp);

      const x1 = getXCoordinate(t1);
      const x2 = getXCoordinate(t2);
      const y1 = this._series.priceToCoordinate(p1.value);
      const y2 = this._series.priceToCoordinate(p2.value);

      // Only draw segments where we have valid coordinates
      if (x1 !== null && x2 !== null && y1 !== null && y2 !== null) {
        segments.push({ x1, y1, x2, y2 });
      }
    }

    return segments;
  }

  private _getHistoricalEndX(): number | null {
    if (!this._historicalEndDate || !this._chart) return null;

    const timeScale = this._chart.timeScale();
    // Use the same normalization as _normalizeTimestamp for consistency
    const timestamp = this._normalizeTimestamp(this._historicalEndDate);
    const x = timeScale.timeToCoordinate(timestamp as Time);

    // If native method returns a coordinate, use it
    if (x !== null) return x;

    // Otherwise, try to extrapolate based on available data
    // This handles the case where the historical end date might be at a gap
    return null;
  }

  getLines(): ForecastLineData[] {
    const lines: ForecastLineData[] = [];

    console.log('[ProphetPrimitive] getLines called', {
      forecastCount: this._forecasts.length,
      hasSeries: !!this._series,
      hasChart: !!this._chart,
    });

    for (const forecast of this._forecasts) {
      const horizon = forecast.horizon;

      // Skip if toggle is off (except for "combined" and "backtest" which are always shown)
      if (horizon !== 'combined' && horizon !== 'backtest') {
        const toggleKey = horizon as keyof ProphetHorizonToggles;
        if (!this._toggles[toggleKey]) continue;
      }

      // Get color scheme
      const colors = HORIZON_COLORS[horizon as keyof typeof HORIZON_COLORS];
      if (!colors) continue;

      // Use all data points (both historical fit and forecast)
      // Historical points will show the model fit, forecast points show predictions
      const forecastData = forecast.series;

      if (forecastData.length < 2) continue;

      // Convert to chart coordinates
      const mainLineData = forecastData.map(p => ({
        timestamp: p.timestamp,
        value: p.value,
      }));
      const upperData = forecastData.map(p => ({
        timestamp: p.timestamp,
        value: p.upper,
      }));
      const lowerData = forecastData.map(p => ({
        timestamp: p.timestamp,
        value: p.lower,
      }));

      const mainLine = this._convertToSegments(mainLineData);
      const upperBound = this._convertToSegments(upperData);
      const lowerBound = this._convertToSegments(lowerData);

      console.log('[ProphetPrimitive] Segments for', horizon, {
        dataPoints: forecastData.length,
        mainLineSegments: mainLine.length,
        upperSegments: upperBound.length,
        lowerSegments: lowerBound.length,
      });

      // Create fill polygon (upper line forward, lower line backward)
      const fillPolygon: Point[] = [];

      // Add upper bound points
      for (const seg of upperBound) {
        if (fillPolygon.length === 0) {
          fillPolygon.push({ x: seg.x1, y: seg.y1 });
        }
        fillPolygon.push({ x: seg.x2, y: seg.y2 });
      }

      // Add lower bound points in reverse
      for (let i = lowerBound.length - 1; i >= 0; i--) {
        const seg = lowerBound[i];
        fillPolygon.push({ x: seg.x2, y: seg.y2 });
        if (i === 0) {
          fillPolygon.push({ x: seg.x1, y: seg.y1 });
        }
      }

      // Determine line width based on horizon
      let lineWidth = 2;
      if (horizon === 'long_term') lineWidth = 2.5;
      if (horizon === 'short_term') lineWidth = 1.5;

      lines.push({
        horizon: forecast.horizon,
        mainLine,
        upperBound,
        lowerBound,
        fillPolygon,
        color: colors,
        lineWidth,
        historicalEndX: horizon === 'long_term' ? this._getHistoricalEndX() : null,
      });
    }

    return lines;
  }
}
