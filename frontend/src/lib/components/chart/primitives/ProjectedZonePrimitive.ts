import type {
  ISeriesPrimitive,
  SeriesAttachedParameter,
  Time,
  IPrimitivePaneView,
  IPrimitivePaneRenderer,
  PrimitiveHoveredItem,
  PrimitivePaneViewZOrder,
  ISeriesPrimitiveAxisView,
} from 'lightweight-charts';
import type { ProjectedZone, FibonacciLevel } from '$lib/types';
import { PROJECTED_ZONE_COLORS, PIN_COLORS } from './utils/colors';

interface ZoneRectData {
  left: number;
  right: number;
  top: number;
  bottom: number;
  label: string;
  zoneStyle: 'validation' | 'target' | 'correction';
  zoneType: string;
  isPinned: boolean;
  id?: string;
}

interface FibLineData {
  startX: number;
  y: number;
  label: string;
  style: 'retracement' | 'extension';
  context: 'target' | 'correction' | 'default';
  chartWidth: number;
}

class ZoneTimeAxisView implements ISeriesPrimitiveAxisView {
  private _coordinate: number;
  private _text: string;
  private _textColor: string;
  private _backColor: string;

  constructor(coordinate: number, text: string, textColor: string, backColor: string) {
    this._coordinate = coordinate;
    this._text = text;
    this._textColor = textColor;
    this._backColor = backColor;
  }

  coordinate(): number { return this._coordinate; }
  text(): string { return this._text; }
  textColor(): string { return this._textColor; }
  backColor(): string { return this._backColor; }
  visible(): boolean { return true; }
  tickVisible(): boolean { return true; }
}

// Pin button dimensions
const PIN_BUTTON_SIZE = 14;
const PIN_BUTTON_MARGIN = 4;

class ProjectedZoneRenderer implements IPrimitivePaneRenderer {
  private _rects: ZoneRectData[] = [];
  private _fibLines: FibLineData[] = [];
  private _animationProgress: number = 1;
  private _direction: 'up' | 'down' = 'up';
  private _hoveredIndex: number = -1;
  private _hoveredPinButtonIndex: number = -1;

  update(
    rects: ZoneRectData[],
    fibLines: FibLineData[],
    animationProgress: number,
    direction: 'up' | 'down',
    hoveredIndex: number,
    hoveredPinButtonIndex: number,
  ): void {
    this._rects = rects;
    this._fibLines = fibLines;
    this._animationProgress = animationProgress;
    this._direction = direction;
    this._hoveredIndex = hoveredIndex;
    this._hoveredPinButtonIndex = hoveredPinButtonIndex;
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  draw(target: any): void {
    if (this._rects.length === 0 && this._fibLines.length === 0) return;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    target.useMediaCoordinateSpace((scope: any) => {
      const ctx = scope.context as CanvasRenderingContext2D;

      ctx.save();
      ctx.globalAlpha = this._animationProgress;

      // Draw Fibonacci lines first (behind zones)
      for (const line of this._fibLines) {
        this._drawFibLine(ctx, line);
      }

      // Draw zone rectangles on top
      for (let i = 0; i < this._rects.length; i++) {
        this._drawRect(ctx, this._rects[i], i === this._hoveredIndex, i === this._hoveredPinButtonIndex);
      }

      ctx.restore();
    });
  }

  private _drawFibLine(ctx: CanvasRenderingContext2D, line: FibLineData): void {
    // Color by context: target → green, correction → amber, default → gray
    let lineColor: string;
    let textColor: string;
    if (line.context === 'target') {
      lineColor = 'rgba(52, 211, 153, 0.18)';
      textColor = 'rgba(52, 211, 153, 0.4)';
    } else if (line.context === 'correction') {
      lineColor = 'rgba(251, 191, 36, 0.18)';
      textColor = 'rgba(251, 191, 36, 0.4)';
    } else {
      const isExtension = line.style === 'extension';
      lineColor = isExtension
        ? 'rgba(168, 162, 158, 0.18)'
        : 'rgba(168, 162, 158, 0.15)';
      textColor = isExtension
        ? 'rgba(168, 162, 158, 0.4)'
        : 'rgba(168, 162, 158, 0.35)';
    }

    // Dashed horizontal line from startX to right edge
    ctx.beginPath();
    ctx.setLineDash([4, 6]);
    ctx.moveTo(line.startX, line.y);
    ctx.lineTo(line.chartWidth, line.y);
    ctx.strokeStyle = lineColor;
    ctx.lineWidth = 0.75;
    ctx.stroke();
    ctx.setLineDash([]);

    // Small label at start of line
    const fontSize = 9;
    ctx.font = `${fontSize}px -apple-system, BlinkMacSystemFont, sans-serif`;
    const labelText = line.label;
    const textWidth = ctx.measureText(labelText).width;
    const padding = 3;
    const labelBoxWidth = textWidth + padding * 2;
    const labelBoxHeight = fontSize + padding * 2;
    const labelX = line.startX + 4;
    const labelY = line.y - labelBoxHeight - 2;

    // Label background
    ctx.fillStyle = 'rgba(12, 10, 9, 0.75)';
    ctx.fillRect(labelX, labelY, labelBoxWidth, labelBoxHeight);

    // Label text
    ctx.fillStyle = textColor;
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    ctx.fillText(labelText, labelX + padding, labelY + labelBoxHeight / 2);
  }

  private _drawRect(ctx: CanvasRenderingContext2D, rect: ZoneRectData, isHovered: boolean, isPinButtonHovered: boolean): void {
    const colors = PROJECTED_ZONE_COLORS[rect.zoneStyle] ?? PROJECTED_ZONE_COLORS.target;

    const top = Math.min(rect.top, rect.bottom);
    const height = Math.abs(rect.bottom - rect.top);
    const width = rect.right - rect.left;

    // Fill
    ctx.fillStyle = colors.fill;
    ctx.fillRect(rect.left, top, width, height);

    // Border: dotted for pinned, dashed for normal
    ctx.beginPath();
    if (rect.isPinned) {
      ctx.setLineDash([2, 3]); // Dotted line for pinned zones
    } else {
      ctx.setLineDash([6, 4]); // Dashed line for normal zones
    }
    ctx.rect(rect.left, top, width, height);
    ctx.strokeStyle = colors.border;
    ctx.lineWidth = isHovered ? 1.5 : 1;
    ctx.stroke();
    ctx.setLineDash([]);

    if (isHovered) {
      // Full label on hover
      const fontSize = 11;
      ctx.font = `bold ${fontSize}px -apple-system, BlinkMacSystemFont, sans-serif`;
      const labelText = rect.label;
      const textWidth = ctx.measureText(labelText).width;
      const padding = 6;
      const labelBoxWidth = textWidth + padding * 2;
      const labelBoxHeight = fontSize + padding * 2;

      const labelX = rect.left + (width - labelBoxWidth) / 2;
      const labelY = top + (height - labelBoxHeight) / 2;

      // Label background
      ctx.fillStyle = 'rgba(28, 25, 23, 0.85)';
      ctx.beginPath();
      ctx.roundRect(labelX, labelY, labelBoxWidth, labelBoxHeight, 4);
      ctx.fill();

      // Label border
      ctx.strokeStyle = colors.border;
      ctx.lineWidth = 1;
      ctx.stroke();

      // Label text
      ctx.fillStyle = colors.text;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(labelText, labelX + labelBoxWidth / 2, labelY + labelBoxHeight / 2);

      // Direction arrow at right edge
      const arrowX = rect.right - 15;
      const arrowY = top + height / 2;
      const arrowSize = 8;
      const isUpArrow =
        (rect.zoneType === 'target' && this._direction === 'up') ||
        (rect.zoneType === 'correction' && this._direction === 'down') ||
        (rect.zoneType === 'validation' && this._direction === 'down');

      ctx.beginPath();
      if (isUpArrow) {
        ctx.moveTo(arrowX, arrowY + arrowSize);
        ctx.lineTo(arrowX + arrowSize / 2, arrowY - arrowSize);
        ctx.lineTo(arrowX - arrowSize / 2, arrowY - arrowSize);
      } else {
        ctx.moveTo(arrowX, arrowY - arrowSize);
        ctx.lineTo(arrowX + arrowSize / 2, arrowY + arrowSize);
        ctx.lineTo(arrowX - arrowSize / 2, arrowY + arrowSize);
      }
      ctx.closePath();
      ctx.fillStyle = colors.text;
      ctx.globalAlpha = this._animationProgress * 0.7;
      ctx.fill();
      ctx.globalAlpha = this._animationProgress;

      // Draw pin button (top-right corner, only on hover)
      this._drawPinButton(ctx, rect.right - PIN_BUTTON_SIZE - PIN_BUTTON_MARGIN, top + PIN_BUTTON_MARGIN, rect.isPinned, isPinButtonHovered);
    } else if (rect.isPinned) {
      // For pinned zones, always show the pin icon (even when not hovered)
      this._drawPinButton(ctx, rect.right - PIN_BUTTON_SIZE - PIN_BUTTON_MARGIN, top + PIN_BUTTON_MARGIN, true, false);

      // Subtle small label at top-left corner of zone (same as non-hovered)
      const fontSize = 8;
      ctx.font = `${fontSize}px -apple-system, BlinkMacSystemFont, sans-serif`;
      const labelText = rect.label;
      const textWidth = ctx.measureText(labelText).width;
      const padding = 3;
      const labelBoxWidth = textWidth + padding * 2;
      const labelBoxHeight = fontSize + padding * 2;

      const labelX = rect.left + 4;
      const labelY = top + 4;

      // Subtle background
      ctx.fillStyle = 'rgba(12, 10, 9, 0.6)';
      ctx.beginPath();
      ctx.roundRect(labelX, labelY, labelBoxWidth, labelBoxHeight, 2);
      ctx.fill();

      // Subtle text
      const savedAlpha = ctx.globalAlpha;
      ctx.globalAlpha = savedAlpha * 0.5;
      ctx.fillStyle = colors.text;
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      ctx.fillText(labelText, labelX + padding, labelY + labelBoxHeight / 2);
      ctx.globalAlpha = savedAlpha;
    } else {
      // Subtle small label at top-left corner of zone
      const fontSize = 8;
      ctx.font = `${fontSize}px -apple-system, BlinkMacSystemFont, sans-serif`;
      const labelText = rect.label;
      const textWidth = ctx.measureText(labelText).width;
      const padding = 3;
      const labelBoxWidth = textWidth + padding * 2;
      const labelBoxHeight = fontSize + padding * 2;

      const labelX = rect.left + 4;
      const labelY = top + 4;

      // Subtle background
      ctx.fillStyle = 'rgba(12, 10, 9, 0.6)';
      ctx.beginPath();
      ctx.roundRect(labelX, labelY, labelBoxWidth, labelBoxHeight, 2);
      ctx.fill();

      // Subtle text
      const savedAlpha = ctx.globalAlpha;
      ctx.globalAlpha = savedAlpha * 0.5;
      ctx.fillStyle = colors.text;
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      ctx.fillText(labelText, labelX + padding, labelY + labelBoxHeight / 2);
      ctx.globalAlpha = savedAlpha;
    }
  }

  private _drawPinButton(ctx: CanvasRenderingContext2D, x: number, y: number, isPinned: boolean, isHovered: boolean): void {
    const colors = isPinned ? PIN_COLORS.active : PIN_COLORS.inactive;
    const size = PIN_BUTTON_SIZE;

    // Draw button background (circle)
    ctx.beginPath();
    ctx.arc(x + size / 2, y + size / 2, size / 2, 0, Math.PI * 2);
    ctx.fillStyle = isHovered ? 'rgba(28, 25, 23, 0.95)' : 'rgba(28, 25, 23, 0.75)';
    ctx.fill();
    ctx.strokeStyle = colors.stroke;
    ctx.lineWidth = isHovered ? 1.5 : 1;
    ctx.stroke();

    // Draw pin icon (simplified pushpin)
    const cx = x + size / 2;
    const cy = y + size / 2;
    const iconScale = size / 14; // Scale to fit in button

    ctx.save();
    ctx.translate(cx, cy);
    ctx.scale(iconScale, iconScale);

    // Pin head (circle at top)
    ctx.beginPath();
    ctx.arc(0, -2, 2.5, 0, Math.PI * 2);
    ctx.fillStyle = colors.fill;
    ctx.fill();
    ctx.strokeStyle = colors.stroke;
    ctx.lineWidth = 1;
    ctx.stroke();

    // Pin body (line down)
    ctx.beginPath();
    ctx.moveTo(0, 0.5);
    ctx.lineTo(0, 4);
    ctx.strokeStyle = colors.stroke;
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Pin point (small triangle at bottom)
    ctx.beginPath();
    ctx.moveTo(0, 4);
    ctx.lineTo(0, 6);
    ctx.strokeStyle = colors.stroke;
    ctx.lineWidth = 1;
    ctx.stroke();

    ctx.restore();
  }
}

class ProjectedZonePaneView implements IPrimitivePaneView {
  private _source: ProjectedZonePrimitive;
  private _renderer: ProjectedZoneRenderer;

  constructor(source: ProjectedZonePrimitive) {
    this._source = source;
    this._renderer = new ProjectedZoneRenderer();
  }

  update(): void {
    const rects = this._source.getZoneRects();
    const fibLines = this._source.getFibLineData();
    this._renderer.update(
      rects,
      fibLines,
      this._source.getAnimationProgress(),
      this._source.getDirection(),
      this._source.getHoveredZoneIndex(),
      this._source.getHoveredPinButtonIndex(),
    );
  }

  renderer(): IPrimitivePaneRenderer {
    this.update();
    return this._renderer;
  }

  zOrder(): PrimitivePaneViewZOrder {
    return 'bottom';
  }
}

export class ProjectedZonePrimitive implements ISeriesPrimitive<Time> {
  private _zones: ProjectedZone[] = [];
  private _fibLevels: FibonacciLevel[] = [];
  private _direction: 'up' | 'down' = 'up';
  private _series: SeriesAttachedParameter<Time>['series'] | null = null;
  private _chart: SeriesAttachedParameter<Time>['chart'] | null = null;
  private _requestUpdate: SeriesAttachedParameter<Time>['requestUpdate'] | null = null;

  private _paneView: ProjectedZonePaneView;

  private _animationProgress: number = 1;
  private _animationFrameId: number | null = null;
  private _animationStartTime: number = 0;
  private _animationDuration: number = 2000;
  private _hoveredZoneIndex: number = -1;
  private _hoveredPinButtonIndex: number = -1;
  private _cachedRects: ZoneRectData[] = [];
  private _hoverX: number | null = null;
  private _hoverY: number | null = null;
  private _timeAxisViews: ISeriesPrimitiveAxisView[] = [];
  private _barIntervalSec: number = 0;
  private _lastBarTimeSec: number = 0;
  private _lastBarIndex: number = 0;
  private _onPinClickCallback: ((zone: ProjectedZone, isPinned: boolean) => void) | null = null;

  constructor() {
    this._paneView = new ProjectedZonePaneView(this);
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
    this._stopAnimation();
  }

  paneViews(): readonly IPrimitivePaneView[] {
    return [this._paneView];
  }

  hitTest(): PrimitiveHoveredItem | null {
    return null;
  }

  setZones(zones: ProjectedZone[], direction: 'up' | 'down', fibLevels?: FibonacciLevel[], barIntervalSec?: number, lastBarTimeSec?: number, lastBarIndex?: number): void {
    this._zones = zones;
    this._direction = direction;
    this._fibLevels = fibLevels ?? [];
    this._barIntervalSec = barIntervalSec ?? 0;
    this._lastBarTimeSec = lastBarTimeSec ?? 0;
    this._lastBarIndex = lastBarIndex ?? 0;
    if (zones.length > 0 || this._fibLevels.length > 0) {
      this._startAnimation();
    } else {
      this._requestUpdate?.();
    }
  }

  getAnimationProgress(): number {
    return this._animationProgress;
  }

  getDirection(): 'up' | 'down' {
    return this._direction;
  }

  getHoveredZoneIndex(): number {
    return this._hoveredZoneIndex;
  }

  getHoveredPinButtonIndex(): number {
    return this._hoveredPinButtonIndex;
  }

  setOnPinClick(callback: ((zone: ProjectedZone, isPinned: boolean) => void) | null): void {
    this._onPinClickCallback = callback;
  }

  setHoverPoint(x: number | null, y: number | null): void {
    const prevIndex = this._hoveredZoneIndex;
    const prevPinIndex = this._hoveredPinButtonIndex;
    const prevHoverX = this._hoverX;
    this._hoverX = x;
    this._hoverY = y;
    this._hoveredZoneIndex = -1;
    this._hoveredPinButtonIndex = -1;

    if (x !== null && y !== null) {
      for (let i = 0; i < this._cachedRects.length; i++) {
        const rect = this._cachedRects[i];
        const rTop = Math.min(rect.top, rect.bottom);
        const rBottom = Math.max(rect.top, rect.bottom);
        if (x >= rect.left && x <= rect.right && y >= rTop && y <= rBottom) {
          this._hoveredZoneIndex = i;

          // Check if hovering over pin button (top-right corner)
          const pinBtnX = rect.right - PIN_BUTTON_SIZE - PIN_BUTTON_MARGIN;
          const pinBtnY = rTop + PIN_BUTTON_MARGIN;
          const pinBtnCenterX = pinBtnX + PIN_BUTTON_SIZE / 2;
          const pinBtnCenterY = pinBtnY + PIN_BUTTON_SIZE / 2;
          const distToPin = Math.sqrt(
            Math.pow(x - pinBtnCenterX, 2) + Math.pow(y - pinBtnCenterY, 2)
          );
          if (distToPin <= PIN_BUTTON_SIZE / 2 + 2) { // Small tolerance
            this._hoveredPinButtonIndex = i;
          }
          break;
        }
      }
    }

    if (this._hoveredZoneIndex !== prevIndex || this._hoverX !== prevHoverX || this._hoveredPinButtonIndex !== prevPinIndex) {
      this._requestUpdate?.();
    }
  }

  /**
   * Check if a click at (x, y) hits a pin button and trigger callback if so.
   * Returns true if a pin button was clicked.
   */
  checkPinButtonClick(x: number, y: number): boolean {
    for (let i = 0; i < this._cachedRects.length; i++) {
      const rect = this._cachedRects[i];
      const rTop = Math.min(rect.top, rect.bottom);
      const rBottom = Math.max(rect.top, rect.bottom);

      // Only check if inside the zone
      if (x >= rect.left && x <= rect.right && y >= rTop && y <= rBottom) {
        // Check if clicking pin button
        const pinBtnX = rect.right - PIN_BUTTON_SIZE - PIN_BUTTON_MARGIN;
        const pinBtnY = rTop + PIN_BUTTON_MARGIN;
        const pinBtnCenterX = pinBtnX + PIN_BUTTON_SIZE / 2;
        const pinBtnCenterY = pinBtnY + PIN_BUTTON_SIZE / 2;
        const distToPin = Math.sqrt(
          Math.pow(x - pinBtnCenterX, 2) + Math.pow(y - pinBtnCenterY, 2)
        );

        if (distToPin <= PIN_BUTTON_SIZE / 2 + 2) {
          // Pin button clicked!
          const zone = this._zones[i];
          if (zone && this._onPinClickCallback) {
            this._onPinClickCallback(zone, !!zone.isPinned);
          }
          return true;
        }
        break;
      }
    }
    return false;
  }

  /**
   * Convert a timestamp to x-coordinate.
   * Works reliably for timestamps that exist in the chart data.
   */
  private _timeToX(timestamp: string): number | null {
    if (!this._chart) return null;
    const time = Math.floor(new Date(timestamp).getTime() / 1000);
    return this._chart.timeScale().timeToCoordinate(time as Time);
  }

  /**
   * Convert a bar index to x-coordinate with manual extrapolation fallback.
   * Used for future positions beyond the chart data range.
   */
  private _barIndexToX(barIndex: number | null | undefined): number | null {
    if (barIndex == null || !this._chart) return null;
    const timeScale = this._chart.timeScale();

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const visibleRange = timeScale.getVisibleLogicalRange() as any;
    if (!visibleRange) return null;

    const chartWidth = timeScale.width();
    const barsVisible = visibleRange.to - visibleRange.from;
    if (barsVisible <= 0) return null;

    const pixelsPerBar = chartWidth / barsVisible;
    return (barIndex - visibleRange.from) * pixelsPerBar;
  }

  /**
   * Get the x-coordinate for a zone edge.
   * Priority: timeToCoordinate (reliable for data range) → timestamp-based extrapolation (for future).
   */
  private _zoneEdgeX(timestamp: string, barIndex: number | null | undefined): number | null {
    // Try timestamp first — works reliably for points within the data
    const timeX = this._timeToX(timestamp);
    if (timeX !== null) return timeX;

    // Fallback to timestamp-based extrapolation — for future positions
    // This is more reliable than bar_index when Elliott Waves uses different period than chart
    return this._timestampToFutureX(timestamp);
  }

  /**
   * Extrapolate x-coordinate for a timestamp beyond the chart data.
   * Uses the last bar time and bar interval to calculate future position.
   */
  private _timestampToFutureX(timestamp: string): number | null {
    if (!this._chart || this._barIntervalSec <= 0 || this._lastBarTimeSec <= 0) return null;

    const timeScale = this._chart.timeScale();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const visibleRange = timeScale.getVisibleLogicalRange() as any;
    if (!visibleRange) return null;

    const chartWidth = timeScale.width();
    const barsVisible = visibleRange.to - visibleRange.from;
    if (barsVisible <= 0) return null;

    const pixelsPerBar = chartWidth / barsVisible;
    const targetTimeSec = Math.floor(new Date(timestamp).getTime() / 1000);

    // Calculate how many bars ahead of the last chart bar
    const secondsAhead = targetTimeSec - this._lastBarTimeSec;
    const barsAhead = secondsAhead / this._barIntervalSec;

    // Position relative to the last bar index in the chart
    const targetBarIndex = this._lastBarIndex + barsAhead;
    return (targetBarIndex - visibleRange.from) * pixelsPerBar;
  }

  /**
   * Convert price to y-coordinate with extrapolation fallback.
   * priceToCoordinate can return null for prices outside visible range.
   */
  private _priceToY(price: number, refPrices?: { price: number; y: number }[]): number | null {
    if (!this._series) return null;
    const y = this._series.priceToCoordinate(price);
    if (y !== null) return y;

    // Extrapolate from reference prices that DID resolve
    if (refPrices && refPrices.length >= 2) {
      const [a, b] = refPrices;
      if (b.price !== a.price) {
        const pixelsPerDollar = (b.y - a.y) / (b.price - a.price);
        return a.y + (price - a.price) * pixelsPerDollar;
      }
    }
    if (refPrices && refPrices.length === 1) {
      const ref = refPrices[0];
      return ref.y + (price - ref.price) * -2;
    }

    return null;
  }

  /**
   * Build reference price→y mappings for extrapolation.
   */
  private _buildRefPrices(): { price: number; y: number }[] {
    if (!this._series) return [];
    const refPrices: { price: number; y: number }[] = [];
    const seen = new Set<number>();

    for (const zone of this._zones) {
      for (const price of [zone.price_top, zone.price_bottom]) {
        if (seen.has(price)) continue;
        seen.add(price);
        const y = this._series.priceToCoordinate(price);
        if (y !== null) refPrices.push({ price, y });
      }
    }
    for (const level of this._fibLevels) {
      if (seen.has(level.price)) continue;
      seen.add(level.price);
      const y = this._series.priceToCoordinate(level.price);
      if (y !== null) refPrices.push({ price: level.price, y });
    }

    return refPrices;
  }

  getZoneRects(): ZoneRectData[] {
    if (!this._series || !this._chart || this._zones.length === 0) {
      this._cachedRects = [];
      return [];
    }

    const rects: ZoneRectData[] = [];
    const refPrices = this._buildRefPrices();

    for (const zone of this._zones) {
      const left = this._zoneEdgeX(zone.time_start, zone.start_bar_index);
      const right = this._zoneEdgeX(zone.time_end, zone.end_bar_index);
      const top = this._priceToY(zone.price_top, refPrices);
      const bottom = this._priceToY(zone.price_bottom, refPrices);

      if (left === null || right === null || top === null || bottom === null) continue;

      // Ensure minimum width for visibility
      const minWidth = 40;
      const adjustedRight = Math.max(right, left + minWidth);

      rects.push({
        left,
        right: adjustedRight,
        top,
        bottom,
        label: zone.label,
        zoneStyle: zone.zone_style ?? (zone.zone_type as 'validation' | 'target' | 'correction'),
        zoneType: zone.zone_type,
        isPinned: !!zone.isPinned,
        id: zone.id,
      });
    }

    this._cachedRects = rects;
    return rects;
  }

  getFibLineData(): FibLineData[] {
    if (!this._series || !this._chart || this._fibLevels.length === 0) return [];

    const lines: FibLineData[] = [];
    const refPrices = this._buildRefPrices();
    const chartWidth = this._chart.timeScale().width();

    for (const level of this._fibLevels) {
      const y = this._priceToY(level.price, refPrices);
      const startX = this._zoneEdgeX(level.ref_timestamp, level.ref_bar_index);

      if (y === null || startX === null) continue;

      lines.push({
        startX,
        y,
        label: level.label,
        style: level.style as 'retracement' | 'extension',
        context: (level.context ?? 'default') as 'target' | 'correction' | 'default',
        chartWidth,
      });
    }

    return lines;
  }

  timeAxisViews(): readonly ISeriesPrimitiveAxisView[] {
    this._updateTimeAxisViews();
    return this._timeAxisViews;
  }

  private _updateTimeAxisViews(): void {
    const views: ISeriesPrimitiveAxisView[] = [];
    if (!this._chart) {
      this._timeAxisViews = views;
      return;
    }

    // A) Zone boundary labels (start and end of each zone)
    for (const zone of this._zones) {
      const style = zone.zone_style ?? (zone.zone_type as 'validation' | 'target' | 'correction');
      const colors = PROJECTED_ZONE_COLORS[style] ?? PROJECTED_ZONE_COLORS.target;
      const backColor = colors.border.replace(/[\d.]+\)$/, '0.8)');

      const startX = this._zoneEdgeX(zone.time_start, zone.start_bar_index);
      const endX = this._zoneEdgeX(zone.time_end, zone.end_bar_index);

      if (startX !== null) {
        views.push(new ZoneTimeAxisView(startX, this._formatTime(zone.time_start), '#FAFAF9', backColor));
      }
      if (endX !== null) {
        views.push(new ZoneTimeAxisView(endX, this._formatTime(zone.time_end), '#FAFAF9', backColor));
      }
    }

    // B) Future cursor time label (extrapolated time when hovering beyond last candle)
    if (this._hoverX !== null && this._barIntervalSec > 0) {
      const futureTime = this._xToTime(this._hoverX);
      if (futureTime) {
        views.push(new ZoneTimeAxisView(this._hoverX, futureTime, '#FAFAF9', 'rgba(120, 113, 108, 0.8)'));
      }
    }

    this._timeAxisViews = views;
  }

  private _xToTime(x: number): string | null {
    if (!this._chart || this._barIntervalSec <= 0 || this._lastBarTimeSec <= 0) return null;

    const timeScale = this._chart.timeScale();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const visibleRange = timeScale.getVisibleLogicalRange() as any;
    if (!visibleRange) return null;

    const chartWidth = timeScale.width();
    const barsVisible = visibleRange.to - visibleRange.from;
    if (barsVisible <= 0) return null;

    const pixelsPerBar = chartWidth / barsVisible;
    const barIndex = visibleRange.from + x / pixelsPerBar;

    // Only show for future bars (beyond last data bar)
    if (barIndex <= this._lastBarIndex) return null;

    const barsAhead = barIndex - this._lastBarIndex;
    const futureTimeSec = this._lastBarTimeSec + barsAhead * this._barIntervalSec;

    return this._formatTime(new Date(futureTimeSec * 1000).toISOString());
  }

  private _formatTime(isoString: string): string {
    const date = new Date(isoString);
    const day = date.getUTCDate();
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const month = months[date.getUTCMonth()];
    const hours = date.getUTCHours();
    const minutes = date.getUTCMinutes();

    if (hours === 0 && minutes === 0) {
      return `${day} ${month}`;
    }
    return `${day} ${month} ${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
  }

  private _startAnimation(): void {
    this._stopAnimation();
    this._animationProgress = 0;
    this._animationStartTime = performance.now();
    this._animate();
  }

  private _stopAnimation(): void {
    if (this._animationFrameId !== null) {
      cancelAnimationFrame(this._animationFrameId);
      this._animationFrameId = null;
    }
  }

  private _animate(): void {
    const elapsed = performance.now() - this._animationStartTime;
    this._animationProgress = Math.min(1, elapsed / this._animationDuration);

    // Ease out cubic
    this._animationProgress = 1 - Math.pow(1 - this._animationProgress, 3);

    this._requestUpdate?.();

    if (elapsed < this._animationDuration) {
      this._animationFrameId = requestAnimationFrame(() => this._animate());
    } else {
      this._animationProgress = 1;
      this._animationFrameId = null;
    }
  }
}
