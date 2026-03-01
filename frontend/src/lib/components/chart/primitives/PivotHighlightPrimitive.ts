import type {
  ISeriesPrimitive,
  SeriesAttachedParameter,
  Time,
  IPrimitivePaneView,
  IPrimitivePaneRenderer,
  PrimitiveHoveredItem,
  PrimitivePaneViewZOrder,
} from 'lightweight-charts';
import type { Pivot } from '$lib/types';
import { PIVOT_COLORS } from './utils/colors';

interface PivotScreenPoint {
  x: number;
  y: number;
  pivot: Pivot;
  isHovered: boolean;
  isSelected: boolean;
  isPreSelected: boolean;
  /** Manual mode: index in manual selection (0-based), -1 if not selected */
  manualIndex: number;
}

// Pivot Highlight Pane Renderer
class PivotHighlightPaneRenderer implements IPrimitivePaneRenderer {
  private _points: PivotScreenPoint[] = [];
  private _pulseProgress: number = 0;

  update(points: PivotScreenPoint[], pulseProgress: number): void {
    this._points = points;
    this._pulseProgress = pulseProgress;
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  draw(target: any): void {
    if (this._points.length === 0) return;

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
    // Draw all pivots
    for (const point of this._points) {
      this._drawPivot(ctx, point);
    }
  }

  private _drawPivot(ctx: CanvasRenderingContext2D, point: PivotScreenPoint): void {
    const colors = point.pivot.type === 'high' ? PIVOT_COLORS.high : PIVOT_COLORS.low;

    ctx.save();

    // Check if this is a manually selected pivot
    if (point.manualIndex >= 0) {
      // Draw manual selection style with wave label
      const manualColor = '#F59E0B'; // Amber-500
      const manualGlow = 'rgba(245, 158, 11, 0.4)';

      // Glow ring
      ctx.beginPath();
      ctx.arc(point.x, point.y, 14, 0, Math.PI * 2);
      ctx.fillStyle = manualGlow;
      ctx.fill();

      // Main circle
      ctx.beginPath();
      ctx.arc(point.x, point.y, 10, 0, Math.PI * 2);
      ctx.fillStyle = manualColor;
      ctx.shadowColor = manualColor;
      ctx.shadowBlur = 10;
      ctx.fill();

      // Draw wave label inside the circle
      ctx.shadowBlur = 0;
      ctx.fillStyle = '#1C1917'; // Stone-900
      ctx.font = 'bold 10px -apple-system, BlinkMacSystemFont, sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      const label = point.manualIndex === 0 ? 'S' : point.manualIndex.toString();
      ctx.fillText(label, point.x, point.y);
    } else if (point.isSelected) {
      // Draw pulse animation for selected pivot
      const pulseRadius = 10 + this._pulseProgress * 15;
      const pulseAlpha = 0.6 * (1 - this._pulseProgress);

      ctx.beginPath();
      ctx.arc(point.x, point.y, pulseRadius, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(139, 92, 246, ${pulseAlpha})`;
      ctx.fill();

      // Draw solid selected indicator
      ctx.beginPath();
      ctx.arc(point.x, point.y, 8, 0, Math.PI * 2);
      ctx.fillStyle = PIVOT_COLORS.selected.base;
      ctx.shadowColor = PIVOT_COLORS.selected.glow;
      ctx.shadowBlur = 12;
      ctx.fill();
    } else if (point.isPreSelected) {
      // Draw pre-selected style (larger, full opacity, glow ring)
      // Glow ring
      ctx.beginPath();
      ctx.arc(point.x, point.y, 10, 0, Math.PI * 2);
      ctx.fillStyle = colors.glow;
      ctx.fill();

      // Main circle (larger)
      ctx.beginPath();
      ctx.arc(point.x, point.y, 6, 0, Math.PI * 2);
      ctx.fillStyle = colors.hover;
      ctx.shadowColor = colors.glow;
      ctx.shadowBlur = 8;
      ctx.globalAlpha = 1.0;
      ctx.fill();
    } else if (point.isHovered) {
      // Draw glow effect for hovered pivot
      ctx.beginPath();
      ctx.arc(point.x, point.y, 14, 0, Math.PI * 2);
      ctx.fillStyle = colors.glow;
      ctx.fill();

      // Draw larger circle
      ctx.beginPath();
      ctx.arc(point.x, point.y, 8, 0, Math.PI * 2);
      ctx.fillStyle = colors.hover;
      ctx.shadowColor = colors.glow;
      ctx.shadowBlur = 10;
      ctx.fill();

      // Draw label tooltip
      this._drawTooltip(ctx, point);
    } else {
      // Draw normal small pivot marker
      ctx.beginPath();
      ctx.arc(point.x, point.y, 4, 0, Math.PI * 2);
      ctx.fillStyle = colors.base;
      ctx.globalAlpha = 0.6;
      ctx.fill();
    }

    ctx.restore();
  }

  private _drawTooltip(ctx: CanvasRenderingContext2D, point: PivotScreenPoint): void {
    const isHigh = point.pivot.type === 'high';
    const text = `${isHigh ? 'High' : 'Low'}: $${point.pivot.price.toFixed(2)}`;

    ctx.font = 'bold 11px -apple-system, BlinkMacSystemFont, sans-serif';
    const textWidth = ctx.measureText(text).width;
    const padding = 6;
    const boxWidth = textWidth + padding * 2;
    const boxHeight = 20;
    const offsetY = isHigh ? -25 : 25;

    const boxX = point.x - boxWidth / 2;
    const boxY = point.y + offsetY - boxHeight / 2;

    // Background
    ctx.fillStyle = 'rgba(28, 25, 23, 0.9)';
    ctx.beginPath();
    ctx.roundRect(boxX, boxY, boxWidth, boxHeight, 4);
    ctx.fill();

    // Border
    ctx.strokeStyle = isHigh ? PIVOT_COLORS.high.base : PIVOT_COLORS.low.base;
    ctx.lineWidth = 1;
    ctx.stroke();

    // Text
    ctx.fillStyle = '#FAFAF9';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, point.x, point.y + offsetY);
  }
}

// Pivot Highlight Pane View
class PivotHighlightPaneView implements IPrimitivePaneView {
  private _source: PivotHighlightPrimitive;
  private _renderer: PivotHighlightPaneRenderer;

  constructor(source: PivotHighlightPrimitive) {
    this._source = source;
    this._renderer = new PivotHighlightPaneRenderer();
  }

  update(): void {
    const points = this._source.getScreenPoints();
    this._renderer.update(
      points,
      this._source.getPulseProgress()
    );
  }

  renderer(): IPrimitivePaneRenderer {
    this.update();
    return this._renderer;
  }

  zOrder(): PrimitivePaneViewZOrder {
    return 'top';
  }
}

// Main Pivot Highlight Primitive
export class PivotHighlightPrimitive implements ISeriesPrimitive<Time> {
  private _pivots: Pivot[] = [];
  private _hoveredPivot: Pivot | null = null;
  private _selectedPivot: Pivot | null = null;
  private _preSelectedPivots: Pivot[] = [];
  /** Candle indices of manually selected pivots (in order of selection) */
  private _manualPivotIndices: number[] = [];

  private _series: SeriesAttachedParameter<Time>['series'] | null = null;
  private _chart: SeriesAttachedParameter<Time>['chart'] | null = null;
  private _requestUpdate: SeriesAttachedParameter<Time>['requestUpdate'] | null = null;

  private _paneView: PivotHighlightPaneView;

  // Pulse animation for selected pivot
  private _pulseProgress: number = 0;
  private _pulseAnimationId: number | null = null;

  constructor() {
    this._paneView = new PivotHighlightPaneView(this);
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
    this._stopPulseAnimation();
  }

  paneViews(): readonly IPrimitivePaneView[] {
    return [this._paneView];
  }

  hitTest(): PrimitiveHoveredItem | null {
    return null;
  }

  // Public API
  setPivots(pivots: Pivot[]): void {
    this._pivots = pivots;
    this._requestUpdate?.();
  }

  setHoveredPivot(pivot: Pivot | null): void {
    if (this._hoveredPivot?.index !== pivot?.index) {
      this._hoveredPivot = pivot;
      this._requestUpdate?.();
    }
  }

  setSelectedPivot(pivot: Pivot | null): void {
    this._selectedPivot = pivot;
    if (pivot) {
      this._startPulseAnimation();
    } else {
      this._stopPulseAnimation();
    }
    this._requestUpdate?.();
  }

  setPreSelectedPivot(pivot: Pivot | null): void {
    this.setPreSelectedPivots(pivot ? [pivot] : []);
  }

  setPreSelectedPivots(pivots: Pivot[]): void {
    const oldIndices = this._preSelectedPivots.map(p => p.index).sort().join(',');
    const newIndices = pivots.map(p => p.index).sort().join(',');
    if (oldIndices !== newIndices) {
      this._preSelectedPivots = pivots;
      this._requestUpdate?.();
    }
  }

  /** Set manually selected pivot indices (for manual wave counting mode) */
  setManualPivotIndices(indices: number[]): void {
    const oldIndices = this._manualPivotIndices.join(',');
    const newIndices = indices.join(',');
    if (oldIndices !== newIndices) {
      this._manualPivotIndices = indices;
      this._requestUpdate?.();
    }
  }

  getPulseProgress(): number {
    return this._pulseProgress;
  }

  getScreenPoints(): PivotScreenPoint[] {
    if (!this._series || !this._chart || this._pivots.length === 0) {
      return [];
    }

    const timeScale = this._chart.timeScale();
    const points: PivotScreenPoint[] = [];

    for (const pivot of this._pivots) {
      const time = Math.floor(new Date(pivot.timestamp).getTime() / 1000);
      const x = timeScale.timeToCoordinate(time as Time);
      const y = this._series.priceToCoordinate(pivot.price);

      if (x === null || y === null) continue;

      // Check if this pivot is in the manual selection
      const manualIndex = this._manualPivotIndices.indexOf(pivot.index);

      points.push({
        x,
        y,
        pivot,
        isHovered: this._hoveredPivot?.index === pivot.index,
        isSelected: this._selectedPivot?.index === pivot.index,
        isPreSelected: this._preSelectedPivots.some(p => p.index === pivot.index),
        manualIndex,
      });
    }

    return points;
  }

  // Find nearest LOW pivot to mouse coordinates (only LOWs are clickable)
  findNearestLowPivot(mouseX: number, mouseY: number, threshold: number = 20): Pivot | null {
    const points = this.getScreenPoints();
    let nearest: Pivot | null = null;
    let minDistance = Infinity;

    for (const point of points) {
      if (point.pivot.type !== 'low') continue;
      const distance = Math.hypot(mouseX - point.x, mouseY - point.y);
      if (distance < minDistance && distance < threshold) {
        minDistance = distance;
        nearest = point.pivot;
      }
    }

    return nearest;
  }

  // Find nearest pivot of any type for hover effects
  findNearestPivot(mouseX: number, mouseY: number, threshold: number = 20): Pivot | null {
    const points = this.getScreenPoints();
    let nearest: Pivot | null = null;
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

  private _startPulseAnimation(): void {
    this._stopPulseAnimation();
    this._animatePulse();
  }

  private _stopPulseAnimation(): void {
    if (this._pulseAnimationId !== null) {
      cancelAnimationFrame(this._pulseAnimationId);
      this._pulseAnimationId = null;
    }
    this._pulseProgress = 0;
  }

  private _animatePulse(): void {
    this._pulseProgress += 0.02;
    if (this._pulseProgress >= 1) {
      this._pulseProgress = 0;
    }

    this._requestUpdate?.();
    this._pulseAnimationId = requestAnimationFrame(() => this._animatePulse());
  }
}
