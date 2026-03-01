import type {
  ISeriesPrimitive,
  SeriesAttachedParameter,
  Time,
  IPrimitivePaneView,
  IPrimitivePaneRenderer,
  PrimitiveHoveredItem,
  PrimitivePaneViewZOrder,
} from 'lightweight-charts';

interface RefitLine {
  x: number;
  timestamp: string;
  isHovered: boolean;
}

// Refit Marker Pane Renderer
class RefitMarkerPaneRenderer implements IPrimitivePaneRenderer {
  private _lines: RefitLine[] = [];
  private _chartHeight: number = 0;

  update(lines: RefitLine[], chartHeight: number): void {
    this._lines = lines;
    this._chartHeight = chartHeight;
  }

  draw(target: any): void {
    if (this._lines.length === 0) return;

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
    for (const line of this._lines) {
      this._drawRefitLine(ctx, line);
    }
  }

  private _drawRefitLine(ctx: CanvasRenderingContext2D, line: RefitLine): void {
    ctx.save();

    // Amber color with transparency
    const normalColor = 'rgba(251, 191, 36, 0.3)'; // amber-400 with low opacity
    const hoverColor = 'rgba(251, 191, 36, 0.6)';
    const labelColor = 'rgba(251, 191, 36, 0.8)';

    // Draw vertical dashed line
    ctx.strokeStyle = line.isHovered ? hoverColor : normalColor;
    ctx.lineWidth = line.isHovered ? 2 : 1;
    ctx.setLineDash([6, 4]);

    ctx.beginPath();
    ctx.moveTo(line.x, 0);
    ctx.lineTo(line.x, this._chartHeight);
    ctx.stroke();

    // Draw small marker at top
    ctx.setLineDash([]);
    ctx.fillStyle = labelColor;
    ctx.beginPath();
    ctx.arc(line.x, 8, line.isHovered ? 5 : 3, 0, Math.PI * 2);
    ctx.fill();

    // Draw "R" label if hovered
    if (line.isHovered) {
      ctx.fillStyle = '#1C1917';
      ctx.font = 'bold 7px -apple-system, BlinkMacSystemFont, sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('R', line.x, 8);

      // Draw tooltip with date
      this._drawTooltip(ctx, line);
    }

    ctx.restore();
  }

  private _drawTooltip(ctx: CanvasRenderingContext2D, line: RefitLine): void {
    const date = new Date(line.timestamp);
    const dateStr = date.toLocaleDateString('de-DE', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
    const text = `Refit: ${dateStr}`;

    ctx.font = '11px -apple-system, BlinkMacSystemFont, sans-serif';
    const textWidth = ctx.measureText(text).width;

    const padding = 6;
    const boxWidth = textWidth + padding * 2;
    const boxHeight = 20;
    const boxX = line.x - boxWidth / 2;
    const boxY = 20;

    // Background
    ctx.fillStyle = 'rgba(28, 25, 23, 0.95)';
    ctx.beginPath();
    ctx.roundRect(boxX, boxY, boxWidth, boxHeight, 4);
    ctx.fill();

    // Border
    ctx.strokeStyle = 'rgba(251, 191, 36, 0.6)';
    ctx.lineWidth = 1;
    ctx.stroke();

    // Text
    ctx.fillStyle = '#FBBF24';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, line.x, boxY + boxHeight / 2);
  }
}

// Refit Marker Pane View
class RefitMarkerPaneView implements IPrimitivePaneView {
  private _source: RefitMarkerPrimitive;
  private _renderer: RefitMarkerPaneRenderer;

  constructor(source: RefitMarkerPrimitive) {
    this._source = source;
    this._renderer = new RefitMarkerPaneRenderer();
  }

  update(): void {
    const { lines, chartHeight } = this._source.getScreenData();
    this._renderer.update(lines, chartHeight);
  }

  renderer(): IPrimitivePaneRenderer {
    this.update();
    return this._renderer;
  }

  zOrder(): PrimitivePaneViewZOrder {
    return 'bottom'; // Draw behind candles
  }
}

// Main Refit Marker Primitive
export class RefitMarkerPrimitive implements ISeriesPrimitive<Time> {
  private _timestamps: string[] = [];
  private _hoveredTimestamp: string | null = null;
  private _visible: boolean = true;

  private _series: SeriesAttachedParameter<Time>['series'] | null = null;
  private _chart: SeriesAttachedParameter<Time>['chart'] | null = null;
  private _requestUpdate: SeriesAttachedParameter<Time>['requestUpdate'] | null = null;

  private _paneView: RefitMarkerPaneView;

  constructor() {
    this._paneView = new RefitMarkerPaneView(this);
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

  // Public API
  setTimestamps(timestamps: string[]): void {
    this._timestamps = timestamps;
    this._requestUpdate?.();
  }

  setVisible(visible: boolean): void {
    this._visible = visible;
    this._requestUpdate?.();
  }

  setHoveredTimestamp(timestamp: string | null): void {
    if (this._hoveredTimestamp !== timestamp) {
      this._hoveredTimestamp = timestamp;
      this._requestUpdate?.();
    }
  }

  getScreenData(): { lines: RefitLine[]; chartHeight: number } {
    if (!this._series || !this._chart || !this._visible || this._timestamps.length === 0) {
      return { lines: [], chartHeight: 0 };
    }

    const timeScale = this._chart.timeScale();
    const chartHeight = this._chart.priceScale('right')?.height() ?? 600;
    const lines: RefitLine[] = [];

    for (const timestamp of this._timestamps) {
      const time = Math.floor(new Date(timestamp).getTime() / 1000);
      const x = timeScale.timeToCoordinate(time as Time);

      if (x !== null) {
        lines.push({
          x,
          timestamp,
          isHovered: this._hoveredTimestamp === timestamp,
        });
      }
    }

    return { lines, chartHeight };
  }

  // Find refit line near mouse X coordinate
  findNearestRefit(mouseX: number, threshold: number = 10): string | null {
    const { lines } = this.getScreenData();
    let nearest: string | null = null;
    let minDistance = Infinity;

    for (const line of lines) {
      const distance = Math.abs(mouseX - line.x);
      if (distance < minDistance && distance < threshold) {
        minDistance = distance;
        nearest = line.timestamp;
      }
    }

    return nearest;
  }
}
