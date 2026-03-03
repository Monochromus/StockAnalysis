/**
 * Indicator Overlay Primitive for TradingView Lightweight Charts.
 *
 * Draws moving averages and Bollinger Bands on the main chart.
 * Each indicator can be toggled independently.
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
import type { IndicatorDataPoint } from '$lib/types';

// Indicator colors
const INDICATOR_COLORS = {
  sma_20: '#FFFF00',   // Yellow
  sma_50: '#FF9800',   // Orange
  sma_200: '#E91E63',  // Pink
  ema_12: '#00BCD4',   // Cyan
  ema_26: '#9C27B0',   // Purple
  bb_upper: '#2196F3', // Blue
  bb_middle: '#2196F3',
  bb_lower: '#2196F3',
  bb_fill: 'rgba(33, 150, 243, 0.1)',
};

interface LineSegment {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

interface IndicatorLine {
  segments: LineSegment[];
  color: string;
  lineWidth: number;
  isDashed?: boolean;
}

interface BollingerBandData {
  upper: LineSegment[];
  middle: LineSegment[];
  lower: LineSegment[];
  fillPolygon: Array<{ x: number; y: number }>;
}

// Renderer
class IndicatorOverlayRenderer implements IPrimitivePaneRenderer {
  private _lines: IndicatorLine[] = [];
  private _bollingerData: BollingerBandData | null = null;

  update(lines: IndicatorLine[], bollingerData: BollingerBandData | null): void {
    this._lines = lines;
    this._bollingerData = bollingerData;
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
    // Draw Bollinger Bands fill first (behind lines)
    if (this._bollingerData && this._bollingerData.fillPolygon.length > 0) {
      ctx.save();
      ctx.beginPath();
      const poly = this._bollingerData.fillPolygon;
      ctx.moveTo(poly[0].x, poly[0].y);
      for (let i = 1; i < poly.length; i++) {
        ctx.lineTo(poly[i].x, poly[i].y);
      }
      ctx.closePath();
      ctx.fillStyle = INDICATOR_COLORS.bb_fill;
      ctx.fill();
      ctx.restore();
    }

    // Draw all lines
    for (const line of this._lines) {
      if (line.segments.length === 0) continue;

      ctx.save();
      ctx.strokeStyle = line.color;
      ctx.lineWidth = line.lineWidth;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';

      if (line.isDashed) {
        ctx.setLineDash([4, 4]);
      }

      ctx.beginPath();
      let isFirst = true;
      for (const seg of line.segments) {
        if (isFirst) {
          ctx.moveTo(seg.x1, seg.y1);
          isFirst = false;
        }
        ctx.lineTo(seg.x2, seg.y2);
      }
      ctx.stroke();
      ctx.restore();
    }
  }
}

// Pane View
class IndicatorOverlayPaneView implements IPrimitivePaneView {
  private _source: IndicatorOverlayPrimitive;
  private _renderer: IndicatorOverlayRenderer;

  constructor(source: IndicatorOverlayPrimitive) {
    this._source = source;
    this._renderer = new IndicatorOverlayRenderer();
  }

  update(): void {
    try {
      const lines = this._source.getLines();
      const bollingerData = this._source.getBollingerData();
      this._renderer.update(lines, bollingerData);
    } catch {
      // Update error - silently ignore
    }
  }

  renderer(): IPrimitivePaneRenderer {
    this.update();
    return this._renderer;
  }

  zOrder(): PrimitivePaneViewZOrder {
    return 'bottom'; // Draw behind candlesticks but above regime background
  }
}

// Main Primitive
export class IndicatorOverlayPrimitive implements ISeriesPrimitive<Time> {
  private _series: SeriesAttachedParameter<Time>['series'] | null = null;
  private _chart: SeriesAttachedParameter<Time>['chart'] | null = null;
  private _requestUpdate: SeriesAttachedParameter<Time>['requestUpdate'] | null = null;

  private _paneView: IndicatorOverlayPaneView;

  // Indicator data
  private _sma20: IndicatorDataPoint[] = [];
  private _sma50: IndicatorDataPoint[] = [];
  private _sma200: IndicatorDataPoint[] = [];
  private _ema12: IndicatorDataPoint[] = [];
  private _ema26: IndicatorDataPoint[] = [];
  private _bbUpper: IndicatorDataPoint[] = [];
  private _bbMiddle: IndicatorDataPoint[] = [];
  private _bbLower: IndicatorDataPoint[] = [];

  // Toggle states
  private _showSma20: boolean = false;
  private _showSma50: boolean = true;
  private _showSma200: boolean = true;
  private _showEma12: boolean = false;
  private _showEma26: boolean = false;
  private _showBollinger: boolean = false;

  constructor() {
    this._paneView = new IndicatorOverlayPaneView(this);
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
  setIndicatorData(data: {
    sma_20?: IndicatorDataPoint[];
    sma_50?: IndicatorDataPoint[];
    sma_200?: IndicatorDataPoint[];
    ema_12?: IndicatorDataPoint[];
    ema_26?: IndicatorDataPoint[];
    bb_upper?: IndicatorDataPoint[];
    bb_middle?: IndicatorDataPoint[];
    bb_lower?: IndicatorDataPoint[];
  }): void {
    if (data.sma_20) this._sma20 = data.sma_20;
    if (data.sma_50) this._sma50 = data.sma_50;
    if (data.sma_200) this._sma200 = data.sma_200;
    if (data.ema_12) this._ema12 = data.ema_12;
    if (data.ema_26) this._ema26 = data.ema_26;
    if (data.bb_upper) this._bbUpper = data.bb_upper;
    if (data.bb_middle) this._bbMiddle = data.bb_middle;
    if (data.bb_lower) this._bbLower = data.bb_lower;
    this._requestUpdate?.();
  }

  // Toggle setters
  setToggles(toggles: {
    sma_20?: boolean;
    sma_50?: boolean;
    sma_200?: boolean;
    ema_12?: boolean;
    ema_26?: boolean;
    bollinger?: boolean;
  }): void {
    if (toggles.sma_20 !== undefined) this._showSma20 = toggles.sma_20;
    if (toggles.sma_50 !== undefined) this._showSma50 = toggles.sma_50;
    if (toggles.sma_200 !== undefined) this._showSma200 = toggles.sma_200;
    if (toggles.ema_12 !== undefined) this._showEma12 = toggles.ema_12;
    if (toggles.ema_26 !== undefined) this._showEma26 = toggles.ema_26;
    if (toggles.bollinger !== undefined) this._showBollinger = toggles.bollinger;
    this._requestUpdate?.();
  }

  private _convertToSegments(data: IndicatorDataPoint[]): LineSegment[] {
    if (!this._series || !this._chart || data.length < 2) return [];

    const timeScale = this._chart.timeScale();
    const segments: LineSegment[] = [];

    for (let i = 0; i < data.length - 1; i++) {
      const p1 = data[i];
      const p2 = data[i + 1];

      // Normalize timestamps to UTC midnight for consistency across timezones
      const t1 = Math.floor(new Date(p1.timestamp.substring(0, 10) + 'T00:00:00Z').getTime() / 1000);
      const t2 = Math.floor(new Date(p2.timestamp.substring(0, 10) + 'T00:00:00Z').getTime() / 1000);

      const x1 = timeScale.timeToCoordinate(t1 as Time);
      const x2 = timeScale.timeToCoordinate(t2 as Time);
      const y1 = this._series.priceToCoordinate(p1.value);
      const y2 = this._series.priceToCoordinate(p2.value);

      if (x1 !== null && x2 !== null && y1 !== null && y2 !== null) {
        segments.push({ x1, y1, x2, y2 });
      }
    }

    return segments;
  }

  getLines(): IndicatorLine[] {
    const lines: IndicatorLine[] = [];

    if (this._showSma20 && this._sma20.length > 0) {
      lines.push({
        segments: this._convertToSegments(this._sma20),
        color: INDICATOR_COLORS.sma_20,
        lineWidth: 1,
      });
    }

    if (this._showSma50 && this._sma50.length > 0) {
      lines.push({
        segments: this._convertToSegments(this._sma50),
        color: INDICATOR_COLORS.sma_50,
        lineWidth: 1,
      });
    }

    if (this._showSma200 && this._sma200.length > 0) {
      lines.push({
        segments: this._convertToSegments(this._sma200),
        color: INDICATOR_COLORS.sma_200,
        lineWidth: 1.5,
      });
    }

    if (this._showEma12 && this._ema12.length > 0) {
      lines.push({
        segments: this._convertToSegments(this._ema12),
        color: INDICATOR_COLORS.ema_12,
        lineWidth: 1,
      });
    }

    if (this._showEma26 && this._ema26.length > 0) {
      lines.push({
        segments: this._convertToSegments(this._ema26),
        color: INDICATOR_COLORS.ema_26,
        lineWidth: 1,
      });
    }

    // Bollinger Bands lines (middle is dashed)
    if (this._showBollinger) {
      if (this._bbUpper.length > 0) {
        lines.push({
          segments: this._convertToSegments(this._bbUpper),
          color: INDICATOR_COLORS.bb_upper,
          lineWidth: 1,
        });
      }
      if (this._bbMiddle.length > 0) {
        lines.push({
          segments: this._convertToSegments(this._bbMiddle),
          color: INDICATOR_COLORS.bb_middle,
          lineWidth: 1,
          isDashed: true,
        });
      }
      if (this._bbLower.length > 0) {
        lines.push({
          segments: this._convertToSegments(this._bbLower),
          color: INDICATOR_COLORS.bb_lower,
          lineWidth: 1,
        });
      }
    }

    return lines;
  }

  getBollingerData(): BollingerBandData | null {
    if (!this._showBollinger || this._bbUpper.length === 0 || this._bbLower.length === 0) {
      return null;
    }

    const upper = this._convertToSegments(this._bbUpper);
    const middle = this._convertToSegments(this._bbMiddle);
    const lower = this._convertToSegments(this._bbLower);

    // Create fill polygon (upper line forward, lower line backward)
    const fillPolygon: Array<{ x: number; y: number }> = [];

    // Add upper band points
    for (const seg of upper) {
      if (fillPolygon.length === 0) {
        fillPolygon.push({ x: seg.x1, y: seg.y1 });
      }
      fillPolygon.push({ x: seg.x2, y: seg.y2 });
    }

    // Add lower band points in reverse
    for (let i = lower.length - 1; i >= 0; i--) {
      const seg = lower[i];
      fillPolygon.push({ x: seg.x2, y: seg.y2 });
      if (i === 0) {
        fillPolygon.push({ x: seg.x1, y: seg.y1 });
      }
    }

    return { upper, middle, lower, fillPolygon };
  }
}
