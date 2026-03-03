/**
 * Volume Overlay Primitive for TradingView Lightweight Charts.
 *
 * Draws volume bars at the bottom of the main chart as an overlay.
 * Volume bars are colored based on price direction (green for up, red for down).
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
import type { Candle } from '$lib/types';

// Volume bar colors
const VOLUME_COLORS = {
  up: 'rgba(52, 211, 153, 0.5)',     // Green with transparency
  down: 'rgba(248, 113, 113, 0.5)',  // Red with transparency
  neutral: 'rgba(168, 162, 158, 0.5)', // Gray with transparency
};

interface VolumeBar {
  x: number;
  y: number;
  width: number;
  height: number;
  color: string;
}

// Renderer
class VolumeOverlayRenderer implements IPrimitivePaneRenderer {
  private _bars: VolumeBar[] = [];

  update(bars: VolumeBar[]): void {
    this._bars = bars;
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
    for (const bar of this._bars) {
      ctx.fillStyle = bar.color;
      ctx.fillRect(bar.x - bar.width / 2, bar.y, bar.width, bar.height);
    }
  }
}

// Pane View
class VolumeOverlayPaneView implements IPrimitivePaneView {
  private _source: VolumeOverlayPrimitive;
  private _renderer: VolumeOverlayRenderer;

  constructor(source: VolumeOverlayPrimitive) {
    this._source = source;
    this._renderer = new VolumeOverlayRenderer();
  }

  update(): void {
    try {
      const bars = this._source.getBars();
      this._renderer.update(bars);
    } catch {
      // Update error - silently ignore
    }
  }

  renderer(): IPrimitivePaneRenderer {
    this.update();
    return this._renderer;
  }

  zOrder(): PrimitivePaneViewZOrder {
    return 'bottom'; // Draw behind everything
  }
}

// Main Primitive
export class VolumeOverlayPrimitive implements ISeriesPrimitive<Time> {
  private _series: SeriesAttachedParameter<Time>['series'] | null = null;
  private _chart: SeriesAttachedParameter<Time>['chart'] | null = null;
  private _requestUpdate: SeriesAttachedParameter<Time>['requestUpdate'] | null = null;

  private _paneView: VolumeOverlayPaneView;

  // Volume data
  private _candles: Candle[] = [];
  private _visible: boolean = true;

  // Volume chart height ratio (percentage of chart height)
  private _heightRatio: number = 0.15;

  constructor() {
    this._paneView = new VolumeOverlayPaneView(this);
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

  // Set candle data (which includes volume)
  setCandles(candles: Candle[]): void {
    this._candles = candles;
    this._requestUpdate?.();
  }

  // Set visibility
  setVisible(visible: boolean): void {
    this._visible = visible;
    this._requestUpdate?.();
  }

  // Get visibility
  isVisible(): boolean {
    return this._visible;
  }

  getBars(): VolumeBar[] {
    if (!this._visible || !this._series || !this._chart || this._candles.length === 0) {
      return [];
    }

    const timeScale = this._chart.timeScale();
    const bars: VolumeBar[] = [];

    // Get chart dimensions
    const chartHeight = this._chart.paneSize(0)?.height;
    if (!chartHeight) return [];

    // Calculate max volume for scaling
    const maxVolume = Math.max(...this._candles.map(c => c.volume));
    if (maxVolume === 0) return [];

    // Calculate volume chart area
    const volumeAreaHeight = chartHeight * this._heightRatio;
    const volumeAreaTop = chartHeight - volumeAreaHeight;

    // Get bar spacing from time scale
    const barSpacing = timeScale.options().barSpacing;
    const barWidth = Math.max(1, (barSpacing as number) * 0.8);

    for (let i = 0; i < this._candles.length; i++) {
      const candle = this._candles[i];
      // Normalize timestamp to UTC midnight for consistency across timezones
      const dateOnly = candle.timestamp.substring(0, 10);
      const time = Math.floor(new Date(dateOnly + 'T00:00:00Z').getTime() / 1000);
      const x = timeScale.timeToCoordinate(time as Time);

      if (x === null) continue;

      // Calculate bar height based on volume
      const volumeRatio = candle.volume / maxVolume;
      const barHeight = volumeRatio * volumeAreaHeight;

      // Determine color based on price direction
      let color: string;
      if (candle.close > candle.open) {
        color = VOLUME_COLORS.up;
      } else if (candle.close < candle.open) {
        color = VOLUME_COLORS.down;
      } else {
        color = VOLUME_COLORS.neutral;
      }

      bars.push({
        x,
        y: volumeAreaTop + (volumeAreaHeight - barHeight),
        width: barWidth,
        height: barHeight,
        color,
      });
    }

    return bars;
  }
}
