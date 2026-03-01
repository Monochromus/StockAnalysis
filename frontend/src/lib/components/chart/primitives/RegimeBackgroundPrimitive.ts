/**
 * Regime Background Primitive for TradingView Lightweight Charts.
 *
 * Draws colored background rectangles for HMM regime periods.
 * Colors represent different market regimes with confidence-based transparency.
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
import type { RegimeDataPoint } from '$lib/types';

// Regime colors with base opacity
const REGIME_COLORS: Record<string, { r: number; g: number; b: number }> = {
  'Crash': { r: 255, g: 0, b: 0 },
  'Bear': { r: 255, g: 107, b: 107 },
  'Neutral Down': { r: 255, g: 180, b: 180 },
  'Chop': { r: 128, g: 128, b: 128 },
  'Neutral Up': { r: 180, g: 255, b: 180 },
  'Bull': { r: 107, g: 255, b: 107 },
  'Bull Run': { r: 0, g: 255, b: 0 },
};

interface RegimeBlock {
  startX: number;
  endX: number;
  color: { r: number; g: number; b: number };
  confidence: number;
  regimeName: string;
}

// Renderer
class RegimeBackgroundRenderer implements IPrimitivePaneRenderer {
  private _blocks: RegimeBlock[] = [];
  private _height: number = 0;

  update(blocks: RegimeBlock[], height: number): void {
    this._blocks = blocks;
    this._height = height;
  }

  draw(target: any): void {
    if (this._blocks.length === 0) return;

    try {
      target.useMediaCoordinateSpace((scope: any) => {
        const ctx = scope.context as CanvasRenderingContext2D;
        this._drawBlocks(ctx);
      });
    } catch {
      // Drawing error - silently ignore
    }
  }

  private _drawBlocks(ctx: CanvasRenderingContext2D): void {
    for (const block of this._blocks) {
      // Calculate opacity based on confidence
      // High confidence (>90%) = 15% opacity
      // Medium confidence (50-90%) = 10-15% opacity
      // Low confidence (<30%) = 5% opacity
      let opacity: number;
      if (block.confidence >= 0.9) {
        opacity = 0.15;
      } else if (block.confidence >= 0.5) {
        opacity = 0.05 + (block.confidence - 0.5) * 0.25; // 0.05 to 0.15
      } else if (block.confidence >= 0.3) {
        opacity = 0.05;
      } else {
        opacity = 0.02;
      }

      const { r, g, b } = block.color;

      ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${opacity})`;
      ctx.fillRect(
        block.startX,
        0,
        block.endX - block.startX,
        this._height
      );
    }
  }
}

// Pane View
class RegimeBackgroundPaneView implements IPrimitivePaneView {
  private _source: RegimeBackgroundPrimitive;
  private _renderer: RegimeBackgroundRenderer;

  constructor(source: RegimeBackgroundPrimitive) {
    this._source = source;
    this._renderer = new RegimeBackgroundRenderer();
  }

  update(): void {
    try {
      const blocks = this._source.getScreenBlocks();
      const height = this._source.getChartHeight();
      this._renderer.update(blocks, height);
    } catch {
      // Update error - silently ignore
    }
  }

  renderer(): IPrimitivePaneRenderer {
    this.update();
    return this._renderer;
  }

  zOrder(): PrimitivePaneViewZOrder {
    return 'bottom'; // Draw behind candlesticks
  }
}

// Main Primitive
export class RegimeBackgroundPrimitive implements ISeriesPrimitive<Time> {
  private _regimeData: RegimeDataPoint[] = [];
  private _series: SeriesAttachedParameter<Time>['series'] | null = null;
  private _chart: SeriesAttachedParameter<Time>['chart'] | null = null;
  private _requestUpdate: SeriesAttachedParameter<Time>['requestUpdate'] | null = null;
  private _visible: boolean = true;

  private _paneView: RegimeBackgroundPaneView;

  constructor() {
    this._paneView = new RegimeBackgroundPaneView(this);
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
    if (!this._visible) return [];
    return [this._paneView];
  }

  hitTest(): PrimitiveHoveredItem | null {
    return null;
  }

  setRegimeData(data: RegimeDataPoint[]): void {
    this._regimeData = data;
    this._requestUpdate?.();
  }

  setVisible(visible: boolean): void {
    this._visible = visible;
    this._requestUpdate?.();
  }

  getChartHeight(): number {
    if (!this._chart) return 0;
    return this._chart.options().height || 400;
  }

  getScreenBlocks(): RegimeBlock[] {
    if (!this._series || !this._chart || this._regimeData.length === 0) {
      return [];
    }

    const timeScale = this._chart.timeScale();
    const blocks: RegimeBlock[] = [];

    // Group consecutive regime data points into blocks
    let currentBlock: {
      startTime: number;
      endTime: number;
      regimeName: string;
      confidence: number;
    } | null = null;

    for (let i = 0; i < this._regimeData.length; i++) {
      const point = this._regimeData[i];
      const time = Math.floor(new Date(point.timestamp).getTime() / 1000);

      if (!currentBlock || currentBlock.regimeName !== point.regime_name) {
        // Start a new block
        if (currentBlock) {
          // Finish previous block
          const startX = timeScale.timeToCoordinate(currentBlock.startTime as Time);
          const endX = timeScale.timeToCoordinate(currentBlock.endTime as Time);

          if (startX !== null && endX !== null) {
            const color = REGIME_COLORS[currentBlock.regimeName] || REGIME_COLORS['Chop'];
            blocks.push({
              startX,
              endX,
              color,
              confidence: currentBlock.confidence,
              regimeName: currentBlock.regimeName,
            });
          }
        }

        currentBlock = {
          startTime: time,
          endTime: time,
          regimeName: point.regime_name,
          confidence: point.confidence,
        };
      } else {
        // Extend current block
        currentBlock.endTime = time;
        currentBlock.confidence = point.confidence;
      }
    }

    // Add the last block
    if (currentBlock) {
      const startX = timeScale.timeToCoordinate(currentBlock.startTime as Time);
      // Extend the last block a bit to cover the last candle
      const endTime = this._regimeData[this._regimeData.length - 1];
      const lastTime = Math.floor(new Date(endTime.timestamp).getTime() / 1000);
      const endX = timeScale.timeToCoordinate(lastTime as Time);

      if (startX !== null && endX !== null) {
        const color = REGIME_COLORS[currentBlock.regimeName] || REGIME_COLORS['Chop'];
        blocks.push({
          startX,
          endX: endX + 10, // Extend a bit to cover last candle
          color,
          confidence: currentBlock.confidence,
          regimeName: currentBlock.regimeName,
        });
      }
    }

    return blocks;
  }
}
