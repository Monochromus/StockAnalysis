<script lang="ts">
  /**
   * COT Chart Component
   * Displays historical net positions chart
   */

  import { onMount, onDestroy } from 'svelte';
  import type { COTPositionData } from '$lib/types';

  export let history: COTPositionData[];
  export let height: number = 200;

  let canvas: HTMLCanvasElement;
  let ctx: CanvasRenderingContext2D | null = null;

  // Colors
  const COLORS = {
    commercial: '#3B82F6',
    noncommercial: '#F59E0B',
    grid: '#374151',
    text: '#9CA3AF',
    zero: '#6B7280',
  };

  $: if (ctx && history.length > 0) {
    drawChart();
  }

  onMount(() => {
    ctx = canvas.getContext('2d');
    if (ctx) {
      drawChart();
    }

    const resizeObserver = new ResizeObserver(() => {
      if (ctx) drawChart();
    });
    resizeObserver.observe(canvas.parentElement!);

    return () => resizeObserver.disconnect();
  });

  function drawChart() {
    if (!ctx || history.length === 0) return;

    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = rect.width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);

    const width = rect.width;
    const padding = { top: 20, right: 60, bottom: 30, left: 10 };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;

    // Clear
    ctx.clearRect(0, 0, width, height);

    // Get data range
    const sortedHistory = [...history].reverse(); // oldest first for chart
    const commercialNets = sortedHistory.map(d => d.commercial_net);
    const noncommercialNets = sortedHistory.map(d => d.noncommercial_net);
    const allNets = [...commercialNets, ...noncommercialNets];

    const minNet = Math.min(...allNets);
    const maxNet = Math.max(...allNets);
    const range = maxNet - minNet || 1;
    const yBuffer = range * 0.1;

    // Scales
    const xScale = (i: number) => padding.left + (i / (sortedHistory.length - 1)) * chartWidth;
    const yScale = (v: number) => {
      const normalized = (v - (minNet - yBuffer)) / (range + 2 * yBuffer);
      return padding.top + chartHeight * (1 - normalized);
    };

    // Draw grid
    ctx.strokeStyle = COLORS.grid;
    ctx.lineWidth = 0.5;

    // Horizontal grid lines
    const yTicks = 5;
    for (let i = 0; i <= yTicks; i++) {
      const y = padding.top + (chartHeight / yTicks) * i;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(width - padding.right, y);
      ctx.stroke();
    }

    // Zero line
    if (minNet < 0 && maxNet > 0) {
      const zeroY = yScale(0);
      ctx.strokeStyle = COLORS.zero;
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(padding.left, zeroY);
      ctx.lineTo(width - padding.right, zeroY);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // Draw commercial line
    ctx.strokeStyle = COLORS.commercial;
    ctx.lineWidth = 2;
    ctx.beginPath();
    sortedHistory.forEach((d, i) => {
      const x = xScale(i);
      const y = yScale(d.commercial_net);
      if (i === 0) {
        ctx!.moveTo(x, y);
      } else {
        ctx!.lineTo(x, y);
      }
    });
    ctx.stroke();

    // Draw non-commercial line
    ctx.strokeStyle = COLORS.noncommercial;
    ctx.lineWidth = 2;
    ctx.beginPath();
    sortedHistory.forEach((d, i) => {
      const x = xScale(i);
      const y = yScale(d.noncommercial_net);
      if (i === 0) {
        ctx!.moveTo(x, y);
      } else {
        ctx!.lineTo(x, y);
      }
    });
    ctx.stroke();

    // Draw Y-axis labels
    ctx.fillStyle = COLORS.text;
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'right';

    for (let i = 0; i <= yTicks; i++) {
      const value = maxNet + yBuffer - ((range + 2 * yBuffer) / yTicks) * i;
      const y = padding.top + (chartHeight / yTicks) * i;
      ctx.fillText(formatNumber(value), width - padding.right + 55, y + 3);
    }

    // Draw X-axis labels (dates)
    ctx.textAlign = 'center';
    const xLabels = [0, Math.floor(sortedHistory.length / 2), sortedHistory.length - 1];
    xLabels.forEach(i => {
      if (sortedHistory[i]) {
        const date = new Date(sortedHistory[i].date);
        const label = date.toLocaleDateString('de-DE', { month: 'short', year: '2-digit' });
        ctx!.fillText(label, xScale(i), height - 8);
      }
    });

    // Draw legend
    const legendY = 12;
    const legendX = padding.left + 10;

    // Commercial
    ctx.fillStyle = COLORS.commercial;
    ctx.fillRect(legendX, legendY - 8, 12, 3);
    ctx.fillStyle = COLORS.text;
    ctx.textAlign = 'left';
    ctx.fillText('Commercial', legendX + 16, legendY);

    // Non-commercial
    ctx.fillStyle = COLORS.noncommercial;
    ctx.fillRect(legendX + 100, legendY - 8, 12, 3);
    ctx.fillStyle = COLORS.text;
    ctx.fillText('Non-Commercial', legendX + 116, legendY);
  }

  function formatNumber(n: number): string {
    if (Math.abs(n) >= 1000000) {
      return (n / 1000000).toFixed(1) + 'M';
    }
    if (Math.abs(n) >= 1000) {
      return (n / 1000).toFixed(0) + 'K';
    }
    return n.toFixed(0);
  }
</script>

<div class="cot-chart">
  <canvas
    bind:this={canvas}
    style="width: 100%; height: {height}px"
  />
</div>

<style>
  .cot-chart {
    width: 100%;
    background: #111827;
    border-radius: 0.5rem;
    overflow: hidden;
  }

  canvas {
    display: block;
  }
</style>
