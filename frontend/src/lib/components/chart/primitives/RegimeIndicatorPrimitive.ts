/**
 * Regime Indicator Primitive for TradingView Lightweight Charts.
 *
 * Displays the current market regime as a colored indicator in the chart.
 * - Green: Trending (α > trending_threshold)
 * - Yellow: Random Walk / Neutral
 * - Red: Mean-Reverting (α < mean_reverting_threshold)
 */

import type {
  ISeriesPrimitive,
  SeriesAttachedParameter,
  ISeriesPrimitivePaneView,
  ISeriesPrimitivePaneRenderer,
  PrimitiveHoveredItem,
  PaneRendererRenderContext,
} from 'lightweight-charts';

// ============= Types =============

export type RegimeType = 'trending' | 'mean_reverting' | 'random_walk';

export interface RegimeData {
  current_regime: RegimeType;
  current_alpha: number;
  ewma_alpha: number;
  regime_strength: string;
  stability_score: number;
}

// ============= Colors =============

const REGIME_COLORS = {
  trending: {
    background: 'rgba(16, 185, 129, 0.15)',
    border: 'rgba(16, 185, 129, 0.6)',
    text: '#10b981',
    label: 'Trending',
  },
  mean_reverting: {
    background: 'rgba(239, 68, 68, 0.15)',
    border: 'rgba(239, 68, 68, 0.6)',
    text: '#ef4444',
    label: 'Mean-Reverting',
  },
  random_walk: {
    background: 'rgba(245, 158, 11, 0.15)',
    border: 'rgba(245, 158, 11, 0.6)',
    text: '#f59e0b',
    label: 'Neutral',
  },
};

// ============= Renderer =============

class RegimeIndicatorRenderer implements ISeriesPrimitivePaneRenderer {
  private _data: RegimeData | null = null;
  private _width: number = 0;
  private _height: number = 0;

  update(data: RegimeData | null, width: number, height: number) {
    this._data = data;
    this._width = width;
    this._height = height;
  }

  draw(ctx: CanvasRenderingContext2D, _context?: PaneRendererRenderContext) {
    if (!this._data) return;

    const colors = REGIME_COLORS[this._data.current_regime];
    const padding = 12;
    const indicatorWidth = 140;
    const indicatorHeight = 60;
    const x = this._width - indicatorWidth - padding;
    const y = padding;
    const cornerRadius = 6;

    // Draw background
    ctx.beginPath();
    ctx.roundRect(x, y, indicatorWidth, indicatorHeight, cornerRadius);
    ctx.fillStyle = colors.background;
    ctx.fill();

    // Draw border
    ctx.strokeStyle = colors.border;
    ctx.lineWidth = 1;
    ctx.stroke();

    // Draw regime label
    ctx.font = 'bold 11px system-ui, sans-serif';
    ctx.fillStyle = colors.text;
    ctx.textAlign = 'left';
    ctx.fillText(colors.label, x + 10, y + 18);

    // Draw alpha value
    ctx.font = '600 16px system-ui, sans-serif';
    ctx.fillStyle = '#e2e8f0';
    ctx.fillText(`α = ${this._data.ewma_alpha.toFixed(3)}`, x + 10, y + 38);

    // Draw strength indicator
    ctx.font = '10px system-ui, sans-serif';
    ctx.fillStyle = '#94a3b8';
    ctx.fillText(
      `${this._data.regime_strength} (${(this._data.stability_score * 100).toFixed(0)}% stabil)`,
      x + 10,
      y + 52
    );

    // Draw small alpha bar
    const barWidth = indicatorWidth - 20;
    const barHeight = 3;
    const barX = x + 10;
    const barY = y + indicatorHeight - 8;

    // Bar background
    ctx.fillStyle = 'rgba(148, 163, 184, 0.3)';
    ctx.fillRect(barX, barY, barWidth, barHeight);

    // Alpha position marker
    const alphaPos = Math.min(1, Math.max(0, this._data.ewma_alpha));
    const markerX = barX + alphaPos * barWidth;

    ctx.beginPath();
    ctx.arc(markerX, barY + barHeight / 2, 4, 0, Math.PI * 2);
    ctx.fillStyle = colors.text;
    ctx.fill();
  }
}

// ============= Pane View =============

class RegimeIndicatorPaneView implements ISeriesPrimitivePaneView {
  private _renderer = new RegimeIndicatorRenderer();
  private _data: RegimeData | null = null;

  update(data: RegimeData | null) {
    this._data = data;
  }

  renderer() {
    return this._renderer;
  }

  zOrder(): 'top' | 'bottom' | 'normal' {
    return 'top';
  }

  updateRenderer(width: number, height: number) {
    this._renderer.update(this._data, width, height);
  }
}

// ============= Primitive =============

export class RegimeIndicatorPrimitive implements ISeriesPrimitive<'Custom'> {
  private _paneView = new RegimeIndicatorPaneView();
  private _data: RegimeData | null = null;
  private _series: SeriesAttachedParameter<'Custom'> | null = null;

  attached(param: SeriesAttachedParameter<'Custom'>) {
    this._series = param;
  }

  detached() {
    this._series = null;
  }

  paneViews() {
    return [this._paneView];
  }

  updateAllViews() {
    this._paneView.update(this._data);
    if (this._series) {
      const chart = this._series.chart;
      const width = chart.options().width || 800;
      const height = chart.options().height || 400;
      this._paneView.updateRenderer(width, height);
    }
  }

  hitTest(_x: number, _y: number): PrimitiveHoveredItem | null {
    return null;
  }

  setData(data: RegimeData | null) {
    this._data = data;
    this.updateAllViews();
    if (this._series) {
      this._series.requestUpdate();
    }
  }

  getData(): RegimeData | null {
    return this._data;
  }
}
