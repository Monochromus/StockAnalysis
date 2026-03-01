/**
 * Enhanced Pivot Primitive for TradingView Lightweight Charts.
 *
 * Extends the basic pivot visualization with:
 * - Status indication (POTENTIAL, CONFIRMED, PROMOTED, INVALID)
 * - Confidence-based opacity
 * - Regime context display
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
import type { EnhancedPivot, PivotStatus, RegimeType } from '$lib/types/waveEngine';

// ============= Types =============

interface EnhancedPivotScreenPoint {
  x: number;
  y: number;
  pivot: EnhancedPivot;
  isHovered: boolean;
}

// ============= Colors =============

const STATUS_COLORS = {
  potential: {
    base: '#f59e0b',
    glow: 'rgba(245, 158, 11, 0.3)',
    pattern: 'dashed',
  },
  confirmed: {
    base: '#10b981',
    glow: 'rgba(16, 185, 129, 0.3)',
    pattern: 'solid',
  },
  promoted: {
    base: '#3b82f6',
    glow: 'rgba(59, 130, 246, 0.3)',
    pattern: 'solid',
  },
  invalid: {
    base: '#6b7280',
    glow: 'rgba(107, 114, 128, 0.2)',
    pattern: 'strikethrough',
  },
};

const TYPE_COLORS = {
  high: '#ef4444',
  low: '#10b981',
};

const REGIME_COLORS = {
  trending: '#10b981',
  mean_reverting: '#ef4444',
  random_walk: '#f59e0b',
};

// ============= Renderer =============

class EnhancedPivotPaneRenderer implements IPrimitivePaneRenderer {
  private _points: EnhancedPivotScreenPoint[] = [];

  update(points: EnhancedPivotScreenPoint[]): void {
    this._points = points;
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  draw(target: any): void {
    if (this._points.length === 0) return;

    try {
      target.useMediaCoordinateSpace((scope: { context: CanvasRenderingContext2D }) => {
        const ctx = scope.context;
        this._drawContent(ctx);
      });
    } catch {
      // Drawing error - silently ignore
    }
  }

  private _drawContent(ctx: CanvasRenderingContext2D): void {
    for (const point of this._points) {
      this._drawPivot(ctx, point);
    }
  }

  private _drawPivot(ctx: CanvasRenderingContext2D, point: EnhancedPivotScreenPoint): void {
    const { pivot, x, y, isHovered } = point;
    const statusColors = STATUS_COLORS[pivot.status];
    const typeColor = TYPE_COLORS[pivot.type];

    // Calculate opacity based on confidence (30% to 100%)
    const confidenceOpacity = 0.3 + (pivot.overall_confidence / 100) * 0.7;

    ctx.save();
    ctx.globalAlpha = confidenceOpacity;

    const baseRadius = isHovered ? 10 : 6;

    if (pivot.status === 'invalid') {
      // Draw strikethrough circle
      this._drawInvalidPivot(ctx, x, y, baseRadius, typeColor);
    } else if (pivot.status === 'potential') {
      // Draw dashed circle
      this._drawPotentialPivot(ctx, x, y, baseRadius, typeColor, statusColors.base);
    } else {
      // Draw solid circle with status ring
      this._drawConfirmedPivot(ctx, x, y, baseRadius, typeColor, statusColors.base, pivot.status === 'promoted');
    }

    // Draw hover tooltip
    if (isHovered) {
      ctx.globalAlpha = 1;
      this._drawTooltip(ctx, point);
    }

    ctx.restore();
  }

  private _drawInvalidPivot(ctx: CanvasRenderingContext2D, x: number, y: number, radius: number, color: string): void {
    // Draw circle
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.globalAlpha = 0.3;
    ctx.stroke();

    // Draw strikethrough
    ctx.beginPath();
    ctx.moveTo(x - radius - 2, y - radius - 2);
    ctx.lineTo(x + radius + 2, y + radius + 2);
    ctx.strokeStyle = '#ef4444';
    ctx.lineWidth = 2;
    ctx.globalAlpha = 0.8;
    ctx.stroke();
  }

  private _drawPotentialPivot(ctx: CanvasRenderingContext2D, x: number, y: number, radius: number, innerColor: string, outerColor: string): void {
    // Draw dashed outer ring
    ctx.beginPath();
    ctx.arc(x, y, radius + 3, 0, Math.PI * 2);
    ctx.strokeStyle = outerColor;
    ctx.lineWidth = 2;
    ctx.setLineDash([4, 3]);
    ctx.stroke();
    ctx.setLineDash([]);

    // Draw inner circle
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fillStyle = innerColor;
    ctx.fill();
  }

  private _drawConfirmedPivot(ctx: CanvasRenderingContext2D, x: number, y: number, radius: number, innerColor: string, outerColor: string, isPromoted: boolean): void {
    // Draw glow for promoted
    if (isPromoted) {
      ctx.beginPath();
      ctx.arc(x, y, radius + 6, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(59, 130, 246, 0.2)';
      ctx.fill();
    }

    // Draw outer status ring
    ctx.beginPath();
    ctx.arc(x, y, radius + 3, 0, Math.PI * 2);
    ctx.strokeStyle = outerColor;
    ctx.lineWidth = 2;
    ctx.stroke();

    // Draw inner circle
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fillStyle = innerColor;
    ctx.fill();

    // Draw checkmark for confirmed/promoted
    ctx.beginPath();
    ctx.strokeStyle = 'white';
    ctx.lineWidth = 1.5;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    const scale = radius / 6;
    ctx.moveTo(x - 2 * scale, y);
    ctx.lineTo(x - 0.5 * scale, y + 1.5 * scale);
    ctx.lineTo(x + 2 * scale, y - 1.5 * scale);
    ctx.stroke();
  }

  private _drawTooltip(ctx: CanvasRenderingContext2D, point: EnhancedPivotScreenPoint): void {
    const { pivot, x, y } = point;
    const isHigh = pivot.type === 'high';

    // Build tooltip text
    const lines = [
      `${isHigh ? 'HIGH' : 'LOW'}: $${pivot.price.toFixed(2)}`,
      `Status: ${pivot.status.toUpperCase()}`,
      `Confidence: ${pivot.overall_confidence.toFixed(0)}%`,
      `Regime: ${pivot.regime_at_creation}`,
      `α: ${pivot.alpha_at_creation.toFixed(3)}`,
    ];

    ctx.font = '11px system-ui, sans-serif';
    const maxWidth = Math.max(...lines.map(l => ctx.measureText(l).width));
    const padding = 8;
    const lineHeight = 16;
    const boxWidth = maxWidth + padding * 2;
    const boxHeight = lines.length * lineHeight + padding * 2;
    const offsetY = isHigh ? -boxHeight - 15 : 15;

    const boxX = x - boxWidth / 2;
    const boxY = y + offsetY;

    // Background
    ctx.fillStyle = 'rgba(15, 23, 42, 0.95)';
    ctx.beginPath();
    ctx.roundRect(boxX, boxY, boxWidth, boxHeight, 6);
    ctx.fill();

    // Border
    ctx.strokeStyle = STATUS_COLORS[pivot.status].base;
    ctx.lineWidth = 1;
    ctx.stroke();

    // Text
    ctx.fillStyle = '#e2e8f0';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';

    lines.forEach((line, i) => {
      const textY = boxY + padding + i * lineHeight;
      if (i === 0) {
        ctx.font = 'bold 11px system-ui, sans-serif';
        ctx.fillStyle = TYPE_COLORS[pivot.type];
      } else if (i === 2) {
        // Color confidence by value
        const confColor = pivot.overall_confidence >= 70 ? '#10b981' :
                         pivot.overall_confidence >= 40 ? '#f59e0b' : '#ef4444';
        ctx.fillStyle = confColor;
        ctx.font = '11px system-ui, sans-serif';
      } else if (i === 3) {
        ctx.fillStyle = REGIME_COLORS[pivot.regime_at_creation];
        ctx.font = '11px system-ui, sans-serif';
      } else {
        ctx.fillStyle = '#94a3b8';
        ctx.font = '11px system-ui, sans-serif';
      }
      ctx.fillText(line, boxX + padding, textY);
    });
  }
}

// ============= Pane View =============

class EnhancedPivotPaneView implements IPrimitivePaneView {
  private _source: EnhancedPivotPrimitive;
  private _renderer: EnhancedPivotPaneRenderer;

  constructor(source: EnhancedPivotPrimitive) {
    this._source = source;
    this._renderer = new EnhancedPivotPaneRenderer();
  }

  update(): void {
    const points = this._source.getScreenPoints();
    this._renderer.update(points);
  }

  renderer(): IPrimitivePaneRenderer {
    this.update();
    return this._renderer;
  }

  zOrder(): PrimitivePaneViewZOrder {
    return 'top';
  }
}

// ============= Primitive =============

export class EnhancedPivotPrimitive implements ISeriesPrimitive<Time> {
  private _pivots: EnhancedPivot[] = [];
  private _hoveredPivotId: string | null = null;
  private _showAllPivots: boolean = true;

  private _series: SeriesAttachedParameter<Time>['series'] | null = null;
  private _chart: SeriesAttachedParameter<Time>['chart'] | null = null;
  private _requestUpdate: SeriesAttachedParameter<Time>['requestUpdate'] | null = null;

  private _paneView: EnhancedPivotPaneView;

  constructor() {
    this._paneView = new EnhancedPivotPaneView(this);
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

  // ============= Public API =============

  setPivots(pivots: EnhancedPivot[]): void {
    this._pivots = pivots;
    this._requestUpdate?.();
  }

  setHoveredPivot(pivotId: string | null): void {
    if (this._hoveredPivotId !== pivotId) {
      this._hoveredPivotId = pivotId;
      this._requestUpdate?.();
    }
  }

  setShowAllPivots(show: boolean): void {
    this._showAllPivots = show;
    this._requestUpdate?.();
  }

  getScreenPoints(): EnhancedPivotScreenPoint[] {
    if (!this._series || !this._chart || this._pivots.length === 0) {
      return [];
    }

    const timeScale = this._chart.timeScale();
    const points: EnhancedPivotScreenPoint[] = [];

    // Filter pivots if not showing all
    const pivotsToShow = this._showAllPivots
      ? this._pivots
      : this._pivots.filter(p => p.status !== 'invalid');

    for (const pivot of pivotsToShow) {
      const time = Math.floor(new Date(pivot.timestamp).getTime() / 1000);
      const x = timeScale.timeToCoordinate(time as Time);
      const y = this._series.priceToCoordinate(pivot.price);

      if (x === null || y === null) continue;

      points.push({
        x,
        y,
        pivot,
        isHovered: this._hoveredPivotId === pivot.pivot_id,
      });
    }

    return points;
  }

  findNearestPivot(mouseX: number, mouseY: number, threshold: number = 20): EnhancedPivot | null {
    const points = this.getScreenPoints();
    let nearest: EnhancedPivot | null = null;
    let minDistance = Infinity;

    for (const point of points) {
      const distance = Math.hypot(mouseX - point.x, mouseY - point.y);
      if (distance < minDistance && distance < threshold) {
        minDistance = distance;
        nearest = point.pivot;
      }
    }

    return nearest;
  }
}
