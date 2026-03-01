import type {
  ISeriesPrimitive,
  SeriesAttachedParameter,
  Time,
  IPrimitivePaneView,
  IPrimitivePaneRenderer,
  PrimitiveHoveredItem,
  PrimitivePaneViewZOrder,
} from 'lightweight-charts';
import type { Wave } from '$lib/types';
import { WAVE_COLORS, LABEL_COLORS, createGradient } from './utils/colors';

export interface WaveData extends Wave {
  color: string;
}

interface WavePoint {
  time: number;
  price: number;
  label: string;
  type: 'impulse' | 'corrective';
  isStart: boolean;
}

// Wave Line Pane Renderer
class WaveLinePaneRenderer implements IPrimitivePaneRenderer {
  private _points: WavePoint[] = [];
  private _animationProgress: number = 1;

  update(points: WavePoint[], animationProgress: number): void {
    this._points = points;
    this._animationProgress = animationProgress;
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  draw(target: any): void {
    if (this._points.length < 2) return;

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
    if (this._points.length < 2) return;

    // Group points by wave
    for (let i = 0; i < this._points.length - 1; i++) {
      const startPoint = this._points[i];
      const endPoint = this._points[i + 1];

      // Skip if not consecutive start/end pair
      if (!startPoint.isStart || endPoint.isStart) continue;

      // Calculate animation cutoff
      const waveIndex = Math.floor(i / 2);
      const totalWaves = Math.floor(this._points.length / 2);
      const waveAnimationStart = waveIndex / totalWaves;
      const waveAnimationEnd = (waveIndex + 1) / totalWaves;

      if (this._animationProgress < waveAnimationStart) continue;

      const localProgress = Math.min(
        1,
        (this._animationProgress - waveAnimationStart) / (waveAnimationEnd - waveAnimationStart)
      );

      this._drawWaveLine(ctx, startPoint, endPoint, localProgress);
    }
  }

  private _drawWaveLine(
    ctx: CanvasRenderingContext2D,
    start: WavePoint,
    end: WavePoint,
    progress: number
  ): void {
    const colors = WAVE_COLORS[start.type];

    // Calculate animated end point
    const animX = start.time + (end.time - start.time) * progress;
    const animY = start.price + (end.price - start.price) * progress;

    // Draw glow effect
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(start.time, start.price);
    ctx.lineTo(animX, animY);
    ctx.strokeStyle = colors.glow;
    ctx.lineWidth = 6;
    ctx.lineCap = 'round';
    ctx.stroke();
    ctx.restore();

    // Draw main gradient line
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(start.time, start.price);
    ctx.lineTo(animX, animY);

    const gradient = createGradient(
      ctx,
      start.time,
      start.price,
      animX,
      animY,
      colors.gradient
    );
    ctx.strokeStyle = gradient;
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    ctx.stroke();
    ctx.restore();

    // Draw arrow at 70% of line if animation is complete enough
    if (progress > 0.7) {
      this._drawArrow(ctx, start, end, colors.primary);
    }
  }

  private _drawArrow(
    ctx: CanvasRenderingContext2D,
    start: WavePoint,
    end: WavePoint,
    color: string
  ): void {
    // Calculate arrow position (70% along the line)
    const arrowX = start.time + (end.time - start.time) * 0.7;
    const arrowY = start.price + (end.price - start.price) * 0.7;

    // Calculate angle
    const angle = Math.atan2(end.price - start.price, end.time - start.time);

    // Draw arrow
    const arrowSize = 8;
    ctx.save();
    ctx.translate(arrowX, arrowY);
    ctx.rotate(angle);
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(-arrowSize, -arrowSize / 2);
    ctx.lineTo(-arrowSize, arrowSize / 2);
    ctx.closePath();
    ctx.fillStyle = color;
    ctx.fill();
    ctx.restore();
  }
}

// Wave Label Pane Renderer
class WaveLabelPaneRenderer implements IPrimitivePaneRenderer {
  private _points: WavePoint[] = [];
  private _animationProgress: number = 1;

  update(points: WavePoint[], animationProgress: number): void {
    this._points = points;
    this._animationProgress = animationProgress;
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  draw(target: any): void {
    const labelPoints = this._points.filter((p) => !p.isStart);
    if (labelPoints.length === 0) return;

    target.useMediaCoordinateSpace((scope: any) => {
      const ctx = scope.context as CanvasRenderingContext2D;

      for (let i = 0; i < labelPoints.length; i++) {
        const point = labelPoints[i];

        // Calculate animation progress for this label
        const labelAnimStart = (i / labelPoints.length) * 0.8; // Labels start earlier
        const labelAnimEnd = ((i + 1) / labelPoints.length) * 0.8 + 0.2;

        if (this._animationProgress < labelAnimStart) continue;

        const localProgress = Math.min(
          1,
          (this._animationProgress - labelAnimStart) / (labelAnimEnd - labelAnimStart)
        );

        // Fade in effect
        const alpha = Math.min(1, localProgress * 1.5);

        this._drawLabel(ctx, point, alpha);
      }
    });
  }

  private _drawLabel(
    ctx: CanvasRenderingContext2D,
    point: WavePoint,
    alpha: number
  ): void {
    const colors = WAVE_COLORS[point.type];
    const labelText = point.label;
    const isImpulse = point.type === 'impulse';

    // Label positioning
    const labelOffset = isImpulse ? -30 : 30;
    const labelX = point.time;
    const labelY = point.price + labelOffset;

    // Label dimensions
    const padding = 6;
    const fontSize = 11;
    ctx.font = `bold ${fontSize}px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`;
    const textWidth = ctx.measureText(labelText).width;
    const boxWidth = textWidth + padding * 2;
    const boxHeight = fontSize + padding * 2;

    ctx.save();
    ctx.globalAlpha = alpha;

    // Draw connection line (dashed)
    ctx.beginPath();
    ctx.setLineDash([2, 2]);
    ctx.moveTo(point.time, point.price);
    ctx.lineTo(labelX, labelY + (isImpulse ? boxHeight / 2 : -boxHeight / 2));
    ctx.strokeStyle = colors.primary;
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.setLineDash([]);

    // Draw small circle at price point
    ctx.beginPath();
    ctx.arc(point.time, point.price, 4, 0, Math.PI * 2);
    ctx.fillStyle = colors.primary;
    ctx.fill();

    // Draw glassmorphism background
    const boxX = labelX - boxWidth / 2;
    const boxY = labelY - boxHeight / 2;

    // Shadow
    ctx.shadowColor = LABEL_COLORS.shadow;
    ctx.shadowBlur = 8;
    ctx.shadowOffsetY = 2;

    // Background
    ctx.beginPath();
    this._roundRect(ctx, boxX, boxY, boxWidth, boxHeight, 6);
    ctx.fillStyle = LABEL_COLORS.background;
    ctx.fill();

    // Reset shadow
    ctx.shadowColor = 'transparent';
    ctx.shadowBlur = 0;
    ctx.shadowOffsetY = 0;

    // Border
    ctx.strokeStyle = LABEL_COLORS.border;
    ctx.lineWidth = 1;
    ctx.stroke();

    // Top accent border
    ctx.beginPath();
    ctx.moveTo(boxX + 4, boxY);
    ctx.lineTo(boxX + boxWidth - 4, boxY);
    ctx.strokeStyle = colors.primary;
    ctx.lineWidth = 2;
    ctx.stroke();

    // Label text
    ctx.fillStyle = LABEL_COLORS.text;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(labelText, labelX, labelY);

    ctx.restore();
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

// Wave Line Pane View
class WaveLinePaneView implements IPrimitivePaneView {
  private _source: ElliottWavePrimitive;
  private _renderer: WaveLinePaneRenderer;

  constructor(source: ElliottWavePrimitive) {
    this._source = source;
    this._renderer = new WaveLinePaneRenderer();
  }

  update(): void {
    try {
      const points = this._source.getScreenPoints();
      this._renderer.update(points, this._source.getAnimationProgress());
    } catch {
      // Update error - silently ignore
    }
  }

  renderer(): IPrimitivePaneRenderer {
    this.update();
    return this._renderer;
  }

  zOrder(): PrimitivePaneViewZOrder {
    return 'top';
  }
}

// Wave Label Pane View
class WaveLabelPaneView implements IPrimitivePaneView {
  private _source: ElliottWavePrimitive;
  private _renderer: WaveLabelPaneRenderer;

  constructor(source: ElliottWavePrimitive) {
    this._source = source;
    this._renderer = new WaveLabelPaneRenderer();
  }

  update(): void {
    const points = this._source.getScreenPoints();
    this._renderer.update(points, this._source.getAnimationProgress());
  }

  renderer(): IPrimitivePaneRenderer {
    this.update();
    return this._renderer;
  }

  zOrder(): PrimitivePaneViewZOrder {
    return 'top';
  }
}

// Main Elliott Wave Primitive
export class ElliottWavePrimitive implements ISeriesPrimitive<Time> {
  private _waves: WaveData[] = [];
  private _series: SeriesAttachedParameter<Time>['series'] | null = null;
  private _chart: SeriesAttachedParameter<Time>['chart'] | null = null;
  private _requestUpdate: SeriesAttachedParameter<Time>['requestUpdate'] | null = null;

  private _lineView: WaveLinePaneView;
  private _labelView: WaveLabelPaneView;

  private _animationProgress: number = 1;
  private _animationFrameId: number | null = null;
  private _animationStartTime: number = 0;
  private _animationDuration: number = 3000; // 3 seconds

  constructor() {
    this._lineView = new WaveLinePaneView(this);
    this._labelView = new WaveLabelPaneView(this);
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
    return [this._lineView, this._labelView];
  }

  hitTest(): PrimitiveHoveredItem | null {
    return null;
  }

  setWaves(waves: WaveData[]): void {
    this._waves = waves;
    this._startAnimation();
  }

  getAnimationProgress(): number {
    return this._animationProgress;
  }

  getScreenPoints(): WavePoint[] {
    if (!this._series || !this._chart || this._waves.length === 0) {
      return [];
    }

    const timeScale = this._chart.timeScale();
    const points: WavePoint[] = [];

    for (const wave of this._waves) {
      const startTime = Math.floor(new Date(wave.start_timestamp).getTime() / 1000);
      const endTime = Math.floor(new Date(wave.end_timestamp).getTime() / 1000);

      const startX = timeScale.timeToCoordinate(startTime as Time);
      const endX = timeScale.timeToCoordinate(endTime as Time);
      const startY = this._series.priceToCoordinate(wave.start_price);
      const endY = this._series.priceToCoordinate(wave.end_price);

      if (startX === null || endX === null || startY === null || endY === null) {
        continue;
      }

      points.push({
        time: startX,
        price: startY,
        label: wave.label,
        type: wave.type,
        isStart: true,
      });

      points.push({
        time: endX,
        price: endY,
        label: wave.label,
        type: wave.type,
        isStart: false,
      });
    }

    return points;
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
