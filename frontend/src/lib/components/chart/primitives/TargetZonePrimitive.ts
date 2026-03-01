import type {
  ISeriesPrimitive,
  SeriesAttachedParameter,
  Time,
  IPrimitivePaneView,
  IPrimitivePaneRenderer,
  PrimitiveHoveredItem,
  PrimitivePaneViewZOrder,
} from 'lightweight-charts';
import type { RiskReward } from '$lib/types';
import { ZONE_COLORS } from './utils/colors';

interface ZoneData {
  top: number;
  bottom: number;
  left: number;
  right: number;
  color: {
    fill: string;
    fillEdge?: string;
    border: string;
    text: string;
    glow?: string;
    labelBg?: string;
  };
  label: string;
}

// Zone Background Renderer
class ZoneBackgroundRenderer implements IPrimitivePaneRenderer {
  private _zones: ZoneData[] = [];
  private _entryPrice: number | null = null;
  private _chartWidth: number = 0;
  private _animationProgress: number = 1;
  private _isHovered: boolean = false;

  update(
    zones: ZoneData[],
    entryPrice: number | null,
    chartWidth: number,
    animationProgress: number,
    isHovered: boolean,
  ): void {
    this._zones = zones;
    this._entryPrice = entryPrice;
    this._chartWidth = chartWidth;
    this._animationProgress = animationProgress;
    this._isHovered = isHovered;
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  draw(target: any): void {
    if (this._zones.length === 0 && this._entryPrice === null) return;

    target.useMediaCoordinateSpace((scope: any) => {
      const ctx = scope.context as CanvasRenderingContext2D;

      ctx.save();
      ctx.globalAlpha = this._animationProgress;

      // Draw zones
      for (const zone of this._zones) {
        this._drawZone(ctx, zone, this._isHovered);
      }

      // Draw entry line
      if (this._entryPrice !== null) {
        this._drawEntryLine(ctx, this._entryPrice, this._isHovered);
      }

      ctx.restore();
    });
  }

  private _drawZone(ctx: CanvasRenderingContext2D, zone: ZoneData, isHovered: boolean): void {
    const height = Math.abs(zone.bottom - zone.top);
    const top = Math.min(zone.top, zone.bottom);
    const left = zone.left;
    const width = zone.right - zone.left;

    // Vertical gradient: solid fill with subtle fade at bottom edge
    const gradient = ctx.createLinearGradient(0, top, 0, top + height);
    gradient.addColorStop(0, zone.color.fill);
    gradient.addColorStop(0.8, zone.color.fill);
    gradient.addColorStop(1, zone.color.fillEdge || zone.color.fill);

    ctx.fillStyle = gradient;
    ctx.fillRect(left, top, width, height);

    // Horizontal shimmer overlay (glass effect)
    const shimmer = ctx.createLinearGradient(left, 0, left + width, 0);
    shimmer.addColorStop(0, 'rgba(250, 250, 249, 0.02)');
    shimmer.addColorStop(0.5, 'rgba(250, 250, 249, 0.04)');
    shimmer.addColorStop(1, 'rgba(250, 250, 249, 0.01)');
    ctx.fillStyle = shimmer;
    ctx.fillRect(left, top, width, height * 0.4);

    // Top border: solid 2px line with glow
    if (zone.color.glow) {
      ctx.save();
      ctx.shadowColor = zone.color.glow;
      ctx.shadowBlur = isHovered ? 8 : 4;
      ctx.beginPath();
      ctx.moveTo(left, top);
      ctx.lineTo(left + width, top);
      ctx.strokeStyle = zone.color.border;
      ctx.lineWidth = isHovered ? 2 : 1;
      ctx.stroke();
      ctx.restore();
    }

    // Side and bottom borders: dashed, 50% opacity
    ctx.save();
    ctx.globalAlpha = this._animationProgress * 0.5;
    ctx.beginPath();
    ctx.setLineDash([4, 4]);
    // Left side
    ctx.moveTo(left, top);
    ctx.lineTo(left, top + height);
    // Bottom
    ctx.lineTo(left + width, top + height);
    // Right side
    ctx.lineTo(left + width, top);
    ctx.strokeStyle = zone.color.border;
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.restore();

    if (isHovered) {
      // Full label on hover (top-right corner)
      this._drawZoneLabel(ctx, zone.label, left + width, top, zone.color.text, zone.color.labelBg || zone.color.fill);
    } else {
      // Subtle small label at top-left corner
      this._drawSubtleLabel(ctx, zone.label, left, top, zone.color.text);
    }
  }

  private _drawZoneLabel(
    ctx: CanvasRenderingContext2D,
    label: string,
    rightX: number,
    y: number,
    color: string,
    labelBg: string
  ): void {
    const padding = 10;
    const fontSize = 12;
    ctx.font = `600 ${fontSize}px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`;
    const textWidth = ctx.measureText(label).width;

    const accentWidth = 3;
    const labelX = rightX - textWidth - padding * 2 - accentWidth;
    const labelY = y + 6;
    const boxWidth = textWidth + padding * 2 + accentWidth;
    const boxHeight = fontSize + 10;

    // Glass background with shadow
    ctx.save();
    ctx.shadowColor = 'rgba(0, 0, 0, 0.4)';
    ctx.shadowBlur = 12;

    ctx.beginPath();
    this._roundRect(ctx, labelX, labelY, boxWidth, boxHeight, 8);
    ctx.fillStyle = 'rgba(28, 25, 23, 0.80)';
    ctx.fill();

    ctx.shadowBlur = 0;

    // Inner glow (top edge)
    ctx.beginPath();
    ctx.moveTo(labelX + 8, labelY);
    ctx.lineTo(labelX + boxWidth - 8, labelY);
    ctx.strokeStyle = 'rgba(250, 250, 249, 0.08)';
    ctx.lineWidth = 1;
    ctx.stroke();

    // Color accent stripe on left
    ctx.beginPath();
    this._roundRect(ctx, labelX, labelY, accentWidth, boxHeight, 2);
    ctx.fillStyle = color;
    ctx.fill();

    ctx.restore();

    // Text
    ctx.fillStyle = color;
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
    ctx.fillText(label, labelX + accentWidth + padding, labelY + 5);
  }

  private _drawSubtleLabel(
    ctx: CanvasRenderingContext2D,
    label: string,
    leftX: number,
    topY: number,
    color: string,
  ): void {
    const fontSize = 8;
    ctx.font = `${fontSize}px -apple-system, BlinkMacSystemFont, sans-serif`;
    const textWidth = ctx.measureText(label).width;
    const padding = 3;
    const boxWidth = textWidth + padding * 2;
    const boxHeight = fontSize + padding * 2;
    const labelX = leftX + 4;
    const labelY = topY + 4;

    ctx.fillStyle = 'rgba(12, 10, 9, 0.6)';
    ctx.beginPath();
    ctx.roundRect(labelX, labelY, boxWidth, boxHeight, 2);
    ctx.fill();

    const savedAlpha = ctx.globalAlpha;
    ctx.globalAlpha = savedAlpha * 0.5;
    ctx.fillStyle = color;
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    ctx.fillText(label, labelX + padding, labelY + boxHeight / 2);
    ctx.globalAlpha = savedAlpha;
  }

  private _drawEntryLine(ctx: CanvasRenderingContext2D, y: number, isHovered: boolean): void {
    // Glow line behind
    ctx.save();
    ctx.globalAlpha = this._animationProgress * (isHovered ? 0.25 : 0.12);
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(this._chartWidth, y);
    ctx.strokeStyle = ZONE_COLORS.entry.text;
    ctx.lineWidth = isHovered ? 6 : 3;
    ctx.stroke();
    ctx.restore();

    // Main line amber
    ctx.beginPath();
    ctx.setLineDash([8, 4]);
    ctx.moveTo(0, y);
    ctx.lineTo(this._chartWidth, y);
    ctx.strokeStyle = ZONE_COLORS.entry.line;
    ctx.lineWidth = isHovered ? 2 : 1;
    ctx.stroke();
    ctx.setLineDash([]);

    if (isHovered) {
      // Full glass label with "ENTRY" text
      const label = 'ENTRY';
      const padding = 10;
      const fontSize = 11;
      ctx.font = `bold ${fontSize}px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`;
      const textWidth = ctx.measureText(label).width;

      const boxWidth = textWidth + padding * 2;
      const boxHeight = fontSize + 10;
      const labelX = this._chartWidth - boxWidth - 8;
      const labelY = y - boxHeight / 2;

      ctx.save();
      ctx.shadowColor = 'rgba(0, 0, 0, 0.3)';
      ctx.shadowBlur = 10;

      ctx.beginPath();
      this._roundRect(ctx, labelX, labelY, boxWidth, boxHeight, 6);
      ctx.fillStyle = 'rgba(28, 25, 23, 0.85)';
      ctx.fill();

      ctx.shadowBlur = 0;

      ctx.strokeStyle = 'rgba(217, 119, 6, 0.5)';
      ctx.lineWidth = 1;
      ctx.stroke();

      ctx.restore();

      ctx.fillStyle = ZONE_COLORS.entry.text;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(label, labelX + boxWidth / 2, y);
    } else {
      // Subtle small label
      const label = 'Entry';
      const fontSize = 8;
      ctx.font = `${fontSize}px -apple-system, BlinkMacSystemFont, sans-serif`;
      const textWidth = ctx.measureText(label).width;
      const padding = 3;
      const boxWidth = textWidth + padding * 2;
      const boxHeight = fontSize + padding * 2;
      const labelX = this._chartWidth - boxWidth - 6;
      const labelY = y - boxHeight - 2;

      ctx.fillStyle = 'rgba(12, 10, 9, 0.6)';
      ctx.beginPath();
      ctx.roundRect(labelX, labelY, boxWidth, boxHeight, 2);
      ctx.fill();

      const savedAlpha = ctx.globalAlpha;
      ctx.globalAlpha = savedAlpha * 0.5;
      ctx.fillStyle = ZONE_COLORS.entry.text;
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      ctx.fillText(label, labelX + padding, labelY + boxHeight / 2);
      ctx.globalAlpha = savedAlpha;
    }
  }

  private _roundRect(
    ctx: CanvasRenderingContext2D,
    x: number,
    y: number,
    width: number,
    height: number,
    radius: number
  ): void {
    ctx.moveTo(x + radius, y);
    ctx.lineTo(x + width - radius, y);
    ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
    ctx.lineTo(x + width, y + height - radius);
    ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
    ctx.lineTo(x + radius, y + height);
    ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
    ctx.lineTo(x, y + radius);
    ctx.quadraticCurveTo(x, y, x + radius, y);
    ctx.closePath();
  }
}

// Zone Pane View
class ZonePaneView implements IPrimitivePaneView {
  private _source: TargetZonePrimitive;
  private _renderer: ZoneBackgroundRenderer;

  constructor(source: TargetZonePrimitive) {
    this._source = source;
    this._renderer = new ZoneBackgroundRenderer();
  }

  update(): void {
    const { zones, entryPrice, chartWidth, animationProgress } =
      this._source.getZoneData();
    this._renderer.update(zones, entryPrice, chartWidth, animationProgress, this._source.getIsHovered());
  }

  renderer(): IPrimitivePaneRenderer {
    this.update();
    return this._renderer;
  }

  zOrder(): PrimitivePaneViewZOrder {
    return 'bottom';
  }
}

// Main Target Zone Primitive
export class TargetZonePrimitive implements ISeriesPrimitive<Time> {
  private _riskReward: RiskReward | null = null;
  private _series: SeriesAttachedParameter<Time>['series'] | null = null;
  private _chart: SeriesAttachedParameter<Time>['chart'] | null = null;
  private _requestUpdate: SeriesAttachedParameter<Time>['requestUpdate'] | null = null;

  private _paneView: ZonePaneView;

  private _animationProgress: number = 1;
  private _animationFrameId: number | null = null;
  private _animationStartTime: number = 0;
  private _animationDuration: number = 1600; // 1.6 seconds
  private _isHovered: boolean = false;
  private _cachedZones: ZoneData[] = [];
  private _cachedEntryY: number | null = null;

  constructor() {
    this._paneView = new ZonePaneView(this);
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

  setRiskReward(riskReward: RiskReward | null): void {
    this._riskReward = riskReward;
    if (riskReward) {
      this._startAnimation();
    } else {
      this._requestUpdate?.();
    }
  }

  getIsHovered(): boolean {
    return this._isHovered;
  }

  setHoverPoint(x: number | null, y: number | null): void {
    const prev = this._isHovered;
    this._isHovered = false;

    if (x !== null && y !== null) {
      // Check if inside any stop-loss zone
      for (const zone of this._cachedZones) {
        const zTop = Math.min(zone.top, zone.bottom);
        const zBottom = Math.max(zone.top, zone.bottom);
        if (x >= zone.left && x <= zone.right && y >= zTop && y <= zBottom) {
          this._isHovered = true;
          break;
        }
      }
      // Also check near the entry line (within 12px)
      if (!this._isHovered && this._cachedEntryY !== null) {
        if (Math.abs(y - this._cachedEntryY) <= 12) {
          this._isHovered = true;
        }
      }
    }

    if (this._isHovered !== prev) {
      this._requestUpdate?.();
    }
  }

  private _timeToX(timestamp: string | null): number | null {
    if (!timestamp || !this._chart) return null;
    const time = Math.floor(new Date(timestamp).getTime() / 1000);
    return this._chart.timeScale().timeToCoordinate(time as Time);
  }

  getZoneData(): {
    zones: ZoneData[];
    entryPrice: number | null;
    chartWidth: number;
    animationProgress: number;
  } {
    if (!this._series || !this._chart || !this._riskReward) {
      this._cachedZones = [];
      this._cachedEntryY = null;
      return { zones: [], entryPrice: null, chartWidth: 0, animationProgress: 1 };
    }

    const chartWidth = this._chart.timeScale().width();
    const zones: ZoneData[] = [];

    const entryY = this._series.priceToCoordinate(this._riskReward.entry_price);
    const stopLossY = this._series.priceToCoordinate(this._riskReward.stop_loss);

    // Calculate time boundaries
    const timeStartX = this._timeToX(this._riskReward.time_start);
    const stopTimeEndX = this._timeToX(this._riskReward.stop_time_end);

    // Default: full chart width if no time data
    const defaultLeft = 0;
    const defaultRight = chartWidth;

    if (stopLossY !== null && entryY !== null) {
      // Stop Loss zone
      zones.push({
        top: entryY,
        bottom: stopLossY,
        left: timeStartX ?? defaultLeft,
        right: stopTimeEndX ?? defaultRight,
        color: ZONE_COLORS.stopLoss,
        label: 'Stop Loss',
      });
    }

    this._cachedZones = zones;
    this._cachedEntryY = entryY;

    return {
      zones,
      entryPrice: entryY,
      chartWidth,
      animationProgress: this._animationProgress,
    };
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

    // Ease out quad
    this._animationProgress = 1 - Math.pow(1 - this._animationProgress, 2);

    this._requestUpdate?.();

    if (elapsed < this._animationDuration) {
      this._animationFrameId = requestAnimationFrame(() => this._animate());
    } else {
      this._animationProgress = 1;
      this._animationFrameId = null;
    }
  }
}
