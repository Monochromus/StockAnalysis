import type {
  ISeriesPrimitive,
  SeriesAttachedParameter,
  Time,
  IPrimitivePaneView,
  IPrimitivePaneRenderer,
  PrimitiveHoveredItem,
  PrimitivePaneViewZOrder,
} from 'lightweight-charts';
import type { Trade } from '$lib/types';

interface TradeMarkerPoint {
  x: number;
  y: number;
  type: 'entry' | 'exit';
  trade: Trade;
  isHovered: boolean;
}

interface TradeConnection {
  entryX: number;
  entryY: number;
  exitX: number;
  exitY: number;
  trade: Trade;
  isProfit: boolean;
}

// Trade Marker Pane Renderer
class TradeMarkerPaneRenderer implements IPrimitivePaneRenderer {
  private _markers: TradeMarkerPoint[] = [];
  private _connections: TradeConnection[] = [];
  private _hoveredTrade: Trade | null = null;

  update(markers: TradeMarkerPoint[], connections: TradeConnection[], hoveredTrade: Trade | null): void {
    this._markers = markers;
    this._connections = connections;
    this._hoveredTrade = hoveredTrade;
  }

  draw(target: any): void {
    if (this._markers.length === 0) return;

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
    // First draw connections (lines between entry and exit)
    for (const conn of this._connections) {
      this._drawConnection(ctx, conn);
    }

    // Then draw markers on top
    for (const marker of this._markers) {
      this._drawMarker(ctx, marker);
    }

    // Draw tooltip for hovered trade
    const hoveredMarker = this._markers.find(m => m.isHovered);
    if (hoveredMarker) {
      this._drawTooltip(ctx, hoveredMarker);
    }
  }

  private _drawConnection(ctx: CanvasRenderingContext2D, conn: TradeConnection): void {
    ctx.save();

    const isHovered = this._hoveredTrade?.entry_date === conn.trade.entry_date;
    const color = conn.isProfit ? 'rgba(52, 211, 153, 0.4)' : 'rgba(248, 113, 113, 0.4)';
    const hoverColor = conn.isProfit ? 'rgba(52, 211, 153, 0.7)' : 'rgba(248, 113, 113, 0.7)';

    ctx.strokeStyle = isHovered ? hoverColor : color;
    ctx.lineWidth = isHovered ? 2 : 1;
    ctx.setLineDash([4, 4]);

    ctx.beginPath();
    ctx.moveTo(conn.entryX, conn.entryY);
    ctx.lineTo(conn.exitX, conn.exitY);
    ctx.stroke();

    ctx.restore();
  }

  private _drawMarker(ctx: CanvasRenderingContext2D, marker: TradeMarkerPoint): void {
    const isLong = marker.trade.direction === 'LONG';
    const isEntry = marker.type === 'entry';
    const isProfit = (marker.trade.pnl ?? 0) > 0;

    ctx.save();

    if (isEntry) {
      // Entry marker - arrow pointing in trade direction
      const size = marker.isHovered ? 14 : 10;
      const baseColor = isLong ? '#34D399' : '#F87171'; // Green for long, red for short
      const glowColor = isLong ? 'rgba(52, 211, 153, 0.5)' : 'rgba(248, 113, 113, 0.5)';

      if (marker.isHovered) {
        // Draw glow
        ctx.beginPath();
        ctx.arc(marker.x, marker.y, size + 4, 0, Math.PI * 2);
        ctx.fillStyle = glowColor;
        ctx.fill();
      }

      // Draw triangle arrow
      ctx.beginPath();
      if (isLong) {
        // Up arrow for LONG entry
        ctx.moveTo(marker.x, marker.y - size);
        ctx.lineTo(marker.x - size * 0.7, marker.y + size * 0.5);
        ctx.lineTo(marker.x + size * 0.7, marker.y + size * 0.5);
      } else {
        // Down arrow for SHORT entry
        ctx.moveTo(marker.x, marker.y + size);
        ctx.lineTo(marker.x - size * 0.7, marker.y - size * 0.5);
        ctx.lineTo(marker.x + size * 0.7, marker.y - size * 0.5);
      }
      ctx.closePath();

      ctx.fillStyle = baseColor;
      ctx.shadowColor = baseColor;
      ctx.shadowBlur = marker.isHovered ? 12 : 6;
      ctx.fill();

      // Draw "E" label
      ctx.shadowBlur = 0;
      ctx.fillStyle = '#1C1917';
      ctx.font = `bold ${marker.isHovered ? 9 : 7}px -apple-system, BlinkMacSystemFont, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      const labelY = isLong ? marker.y + 2 : marker.y - 2;
      ctx.fillText('E', marker.x, labelY);

    } else {
      // Exit marker - X or circle with profit/loss color
      const size = marker.isHovered ? 12 : 8;
      const baseColor = isProfit ? '#34D399' : '#F87171';
      const glowColor = isProfit ? 'rgba(52, 211, 153, 0.5)' : 'rgba(248, 113, 113, 0.5)';

      if (marker.isHovered) {
        // Draw glow
        ctx.beginPath();
        ctx.arc(marker.x, marker.y, size + 4, 0, Math.PI * 2);
        ctx.fillStyle = glowColor;
        ctx.fill();
      }

      // Draw square for exit
      ctx.beginPath();
      const halfSize = size / 2;
      ctx.rect(marker.x - halfSize, marker.y - halfSize, size, size);
      ctx.fillStyle = baseColor;
      ctx.shadowColor = baseColor;
      ctx.shadowBlur = marker.isHovered ? 12 : 6;
      ctx.fill();

      // Draw "X" label
      ctx.shadowBlur = 0;
      ctx.fillStyle = '#1C1917';
      ctx.font = `bold ${marker.isHovered ? 9 : 7}px -apple-system, BlinkMacSystemFont, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('X', marker.x, marker.y);
    }

    ctx.restore();
  }

  private _drawTooltip(ctx: CanvasRenderingContext2D, marker: TradeMarkerPoint): void {
    const trade = marker.trade;
    const isEntry = marker.type === 'entry';
    const isProfit = (trade.pnl ?? 0) > 0;

    // Build tooltip lines
    const lines: string[] = [];
    lines.push(`${trade.direction} ${isEntry ? 'Entry' : 'Exit'}`);

    if (isEntry) {
      lines.push(`Price: $${trade.entry_price.toFixed(2)}`);
      lines.push(`Regime: ${trade.regime_at_entry}`);
      if (trade.entry_date) {
        const date = new Date(trade.entry_date);
        lines.push(`Date: ${date.toLocaleDateString()}`);
      }
    } else {
      if (trade.exit_price) {
        lines.push(`Price: $${trade.exit_price.toFixed(2)}`);
      }
      if (trade.pnl !== null) {
        const pnlSign = trade.pnl >= 0 ? '+' : '';
        lines.push(`P&L: ${pnlSign}$${trade.pnl.toFixed(2)}`);
      }
      if (trade.pnl_pct !== null) {
        const pctSign = trade.pnl_pct >= 0 ? '+' : '';
        lines.push(`Return: ${pctSign}${trade.pnl_pct.toFixed(2)}%`);
      }
      if (trade.exit_date) {
        const date = new Date(trade.exit_date);
        lines.push(`Date: ${date.toLocaleDateString()}`);
      }
    }

    ctx.save();

    // Measure text
    ctx.font = '11px -apple-system, BlinkMacSystemFont, sans-serif';
    let maxWidth = 0;
    for (const line of lines) {
      maxWidth = Math.max(maxWidth, ctx.measureText(line).width);
    }

    const padding = 8;
    const lineHeight = 16;
    const boxWidth = maxWidth + padding * 2;
    const boxHeight = lines.length * lineHeight + padding * 2;

    // Position tooltip above or below marker
    let tooltipX = marker.x - boxWidth / 2;
    let tooltipY = marker.y - boxHeight - 20;

    // Keep tooltip in bounds
    if (tooltipY < 10) {
      tooltipY = marker.y + 20;
    }

    // Draw background
    ctx.fillStyle = 'rgba(28, 25, 23, 0.95)';
    ctx.beginPath();
    ctx.roundRect(tooltipX, tooltipY, boxWidth, boxHeight, 6);
    ctx.fill();

    // Draw border
    const borderColor = isEntry
      ? (trade.direction === 'LONG' ? '#34D399' : '#F87171')
      : (isProfit ? '#34D399' : '#F87171');
    ctx.strokeStyle = borderColor;
    ctx.lineWidth = 1;
    ctx.stroke();

    // Draw text
    ctx.fillStyle = '#FAFAF9';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';

    for (let i = 0; i < lines.length; i++) {
      const y = tooltipY + padding + i * lineHeight;
      // First line is bold
      if (i === 0) {
        ctx.font = 'bold 11px -apple-system, BlinkMacSystemFont, sans-serif';
        ctx.fillStyle = borderColor;
      } else {
        ctx.font = '11px -apple-system, BlinkMacSystemFont, sans-serif';
        ctx.fillStyle = '#FAFAF9';
      }
      ctx.fillText(lines[i], tooltipX + padding, y);
    }

    ctx.restore();
  }
}

// Trade Marker Pane View
class TradeMarkerPaneView implements IPrimitivePaneView {
  private _source: TradeMarkerPrimitive;
  private _renderer: TradeMarkerPaneRenderer;

  constructor(source: TradeMarkerPrimitive) {
    this._source = source;
    this._renderer = new TradeMarkerPaneRenderer();
  }

  update(): void {
    const { markers, connections } = this._source.getScreenData();
    this._renderer.update(markers, connections, this._source.getHoveredTrade());
  }

  renderer(): IPrimitivePaneRenderer {
    this.update();
    return this._renderer;
  }

  zOrder(): PrimitivePaneViewZOrder {
    return 'top';
  }
}

// Main Trade Marker Primitive
export class TradeMarkerPrimitive implements ISeriesPrimitive<Time> {
  private _trades: Trade[] = [];
  private _hoveredTrade: Trade | null = null;
  private _visible: boolean = true;

  private _series: SeriesAttachedParameter<Time>['series'] | null = null;
  private _chart: SeriesAttachedParameter<Time>['chart'] | null = null;
  private _requestUpdate: SeriesAttachedParameter<Time>['requestUpdate'] | null = null;

  private _paneView: TradeMarkerPaneView;

  constructor() {
    this._paneView = new TradeMarkerPaneView(this);
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
  setTrades(trades: Trade[]): void {
    this._trades = trades;
    this._requestUpdate?.();
  }

  setVisible(visible: boolean): void {
    this._visible = visible;
    this._requestUpdate?.();
  }

  setHoveredTrade(trade: Trade | null): void {
    if (this._hoveredTrade?.entry_date !== trade?.entry_date) {
      this._hoveredTrade = trade;
      this._requestUpdate?.();
    }
  }

  getHoveredTrade(): Trade | null {
    return this._hoveredTrade;
  }

  getScreenData(): { markers: TradeMarkerPoint[]; connections: TradeConnection[] } {
    if (!this._series || !this._chart || !this._visible || this._trades.length === 0) {
      return { markers: [], connections: [] };
    }

    const timeScale = this._chart.timeScale();
    const markers: TradeMarkerPoint[] = [];
    const connections: TradeConnection[] = [];

    for (const trade of this._trades) {
      // Entry marker
      if (trade.entry_date) {
        const entryTime = Math.floor(new Date(trade.entry_date).getTime() / 1000);
        const entryX = timeScale.timeToCoordinate(entryTime as Time);
        const entryY = this._series.priceToCoordinate(trade.entry_price);

        if (entryX !== null && entryY !== null) {
          const isHovered = this._hoveredTrade?.entry_date === trade.entry_date;
          markers.push({
            x: entryX,
            y: entryY,
            type: 'entry',
            trade,
            isHovered,
          });

          // Exit marker and connection
          if (trade.exit_date && trade.exit_price) {
            const exitTime = Math.floor(new Date(trade.exit_date).getTime() / 1000);
            const exitX = timeScale.timeToCoordinate(exitTime as Time);
            const exitY = this._series.priceToCoordinate(trade.exit_price);

            if (exitX !== null && exitY !== null) {
              markers.push({
                x: exitX,
                y: exitY,
                type: 'exit',
                trade,
                isHovered,
              });

              connections.push({
                entryX,
                entryY,
                exitX,
                exitY,
                trade,
                isProfit: (trade.pnl ?? 0) > 0,
              });
            }
          }
        }
      }
    }

    return { markers, connections };
  }

  // Find trade near mouse coordinates
  findNearestTrade(mouseX: number, mouseY: number, threshold: number = 20): { trade: Trade; type: 'entry' | 'exit' } | null {
    const { markers } = this.getScreenData();
    let nearest: { trade: Trade; type: 'entry' | 'exit' } | null = null;
    let minDistance = Infinity;

    for (const marker of markers) {
      const distance = Math.hypot(mouseX - marker.x, mouseY - marker.y);
      if (distance < minDistance && distance < threshold) {
        minDistance = distance;
        nearest = { trade: marker.trade, type: marker.type };
      }
    }

    return nearest;
  }
}
