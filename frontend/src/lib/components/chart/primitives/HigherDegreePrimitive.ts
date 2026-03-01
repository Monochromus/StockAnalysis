import type {
  ISeriesPrimitive,
  SeriesAttachedParameter,
  Time,
  IPrimitivePaneView,
  IPrimitivePaneRenderer,
  PrimitiveHoveredItem,
  PrimitivePaneViewZOrder,
} from 'lightweight-charts';
import type { HigherDegreeAnalysis } from '$lib/types';
import { HIGHER_DEGREE_COLORS } from './utils/colors';

interface WaveILineData {
  startX: number;
  startY: number;
  endX: number;
  endY: number;
}

// Higher Degree Line Renderer (for Wave (I) line only)
class HigherDegreeLineRenderer implements IPrimitivePaneRenderer {
  private _lineData: WaveILineData | null = null;
  private _animationProgress: number = 1;

  update(lineData: WaveILineData | null, animationProgress: number): void {
    this._lineData = lineData;
    this._animationProgress = animationProgress;
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  draw(target: any): void {
    if (!this._lineData) return;

    target.useMediaCoordinateSpace((scope: any) => {
      const ctx = scope.context as CanvasRenderingContext2D;
      const d = this._lineData!;

      ctx.save();
      ctx.globalAlpha = this._animationProgress;

      // Draw glow effect
      ctx.beginPath();
      ctx.setLineDash([8, 6]);
      ctx.moveTo(d.startX, d.startY);
      ctx.lineTo(d.endX, d.endY);
      ctx.strokeStyle = HIGHER_DEGREE_COLORS.waveI.glow;
      ctx.lineWidth = 8;
      ctx.lineCap = 'round';
      ctx.stroke();

      // Draw main dashed line
      ctx.beginPath();
      ctx.setLineDash([8, 6]);
      ctx.moveTo(d.startX, d.startY);
      ctx.lineTo(d.endX, d.endY);

      const gradient = ctx.createLinearGradient(d.startX, d.startY, d.endX, d.endY);
      gradient.addColorStop(0, HIGHER_DEGREE_COLORS.waveI.gradient[0]);
      gradient.addColorStop(1, HIGHER_DEGREE_COLORS.waveI.gradient[1]);
      ctx.strokeStyle = gradient;
      ctx.lineWidth = 4;
      ctx.lineCap = 'round';
      ctx.stroke();
      ctx.setLineDash([]);

      // Draw (I) label at the end
      const labelText = '(I)';
      const fontSize = 14;
      ctx.font = `bold ${fontSize}px -apple-system, BlinkMacSystemFont, sans-serif`;
      const textWidth = ctx.measureText(labelText).width;
      const padding = 6;
      const boxWidth = textWidth + padding * 2;
      const boxHeight = fontSize + padding * 2;

      // Position label above or below end point
      const isUp = d.endY < d.startY;
      const labelX = d.endX + 10;
      const labelY = isUp ? d.endY - boxHeight - 5 : d.endY + 5;

      // Background
      ctx.shadowColor = 'rgba(0, 0, 0, 0.3)';
      ctx.shadowBlur = 8;
      ctx.fillStyle = 'rgba(28, 25, 23, 0.9)';
      ctx.beginPath();
      ctx.roundRect(labelX, labelY, boxWidth, boxHeight, 4);
      ctx.fill();
      ctx.shadowBlur = 0;

      // Border
      ctx.strokeStyle = HIGHER_DEGREE_COLORS.waveI.primary;
      ctx.lineWidth = 2;
      ctx.stroke();

      // Text
      ctx.fillStyle = HIGHER_DEGREE_COLORS.waveI.primary;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(labelText, labelX + boxWidth / 2, labelY + boxHeight / 2);

      ctx.restore();
    });
  }
}

// Higher Degree Line Pane View
class HigherDegreeLinePaneView implements IPrimitivePaneView {
  private _source: HigherDegreePrimitive;
  private _renderer: HigherDegreeLineRenderer;

  constructor(source: HigherDegreePrimitive) {
    this._source = source;
    this._renderer = new HigherDegreeLineRenderer();
  }

  update(): void {
    const lineData = this._source.getLineData();
    this._renderer.update(lineData, this._source.getAnimationProgress());
  }

  renderer(): IPrimitivePaneRenderer {
    this.update();
    return this._renderer;
  }

  zOrder(): PrimitivePaneViewZOrder {
    return 'top';
  }
}

// Main Higher Degree Primitive (only (I) wave line, zones handled by ProjectedZonePrimitive)
export class HigherDegreePrimitive implements ISeriesPrimitive<Time> {
  private _data: HigherDegreeAnalysis | null = null;
  private _series: SeriesAttachedParameter<Time>['series'] | null = null;
  private _chart: SeriesAttachedParameter<Time>['chart'] | null = null;
  private _requestUpdate: SeriesAttachedParameter<Time>['requestUpdate'] | null = null;

  private _lineView: HigherDegreeLinePaneView;

  private _animationProgress: number = 1;
  private _animationFrameId: number | null = null;
  private _animationStartTime: number = 0;
  private _animationDuration: number = 2000;

  constructor() {
    this._lineView = new HigherDegreeLinePaneView(this);
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
    return [this._lineView];
  }

  hitTest(): PrimitiveHoveredItem | null {
    return null;
  }

  setData(data: HigherDegreeAnalysis | null | undefined): void {
    this._data = data ?? null;
    if (this._data) {
      this._startAnimation();
    } else {
      this._requestUpdate?.();
    }
  }

  getAnimationProgress(): number {
    return this._animationProgress;
  }

  private _timeToX(timestamp: string): number | null {
    if (!this._chart) return null;
    const time = Math.floor(new Date(timestamp).getTime() / 1000);
    return this._chart.timeScale().timeToCoordinate(time as Time);
  }

  getLineData(): WaveILineData | null {
    if (!this._series || !this._chart || !this._data) return null;

    const wave = this._data.completed_wave;
    const startX = this._timeToX(wave.start_timestamp);
    const endX = this._timeToX(wave.end_timestamp);
    const startY = this._series.priceToCoordinate(wave.start_price);
    const endY = this._series.priceToCoordinate(wave.end_price);

    if (startX === null || endX === null || startY === null || endY === null) return null;

    return { startX, startY, endX, endY };
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
