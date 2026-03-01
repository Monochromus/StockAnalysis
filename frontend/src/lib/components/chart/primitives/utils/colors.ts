// Elliott Wave Visualization Color Palette

export const WAVE_COLORS = {
  impulse: {
    primary: '#34D399',    // Emerald-400
    secondary: '#10b981',   // Emerald-500
    glow: 'rgba(52, 211, 153, 0.3)',
    gradient: ['#34D399', '#10b981'],
  },
  corrective: {
    primary: '#FBBF24',    // Amber-400
    secondary: '#F59E0B',   // Amber-500
    glow: 'rgba(251, 191, 36, 0.3)',
    gradient: ['#FBBF24', '#F59E0B'],
  },
} as const;

export const ZONE_COLORS = {
  stopLoss: {
    fill: 'rgba(248, 113, 113, 0.18)',
    fillEdge: 'rgba(248, 113, 113, 0.06)',
    border: 'rgba(248, 113, 113, 0.5)',
    text: '#F87171',
    glow: 'rgba(248, 113, 113, 0.3)',
    labelBg: 'rgba(248, 113, 113, 0.12)',
  },
  target1: {
    fill: 'rgba(52, 211, 153, 0.16)',
    fillEdge: 'rgba(52, 211, 153, 0.04)',
    border: 'rgba(52, 211, 153, 0.4)',
    text: '#34D399',
    glow: 'rgba(52, 211, 153, 0.25)',
    labelBg: 'rgba(52, 211, 153, 0.12)',
  },
  target2: {
    fill: 'rgba(45, 212, 191, 0.18)',
    fillEdge: 'rgba(45, 212, 191, 0.05)',
    border: 'rgba(45, 212, 191, 0.45)',
    text: '#2DD4BF',
    glow: 'rgba(45, 212, 191, 0.25)',
    labelBg: 'rgba(45, 212, 191, 0.12)',
  },
  target3: {
    fill: 'rgba(34, 211, 238, 0.20)',
    fillEdge: 'rgba(34, 211, 238, 0.06)',
    border: 'rgba(34, 211, 238, 0.5)',
    text: '#22D3EE',
    glow: 'rgba(34, 211, 238, 0.3)',
    labelBg: 'rgba(34, 211, 238, 0.12)',
  },
  entry: {
    line: 'rgba(217, 119, 6, 0.7)',
    text: '#D97706',
    glow: 'rgba(217, 119, 6, 0.25)',
  },
} as const;

export const LABEL_COLORS = {
  background: 'rgba(28, 25, 23, 0.85)',
  border: 'rgba(120, 113, 108, 0.4)',
  text: '#FAFAF9',
  shadow: 'rgba(0, 0, 0, 0.4)',
} as const;

export const PIVOT_COLORS = {
  high: {
    base: '#F87171',
    glow: 'rgba(248, 113, 113, 0.5)',
    hover: '#FCA5A5',
  },
  low: {
    base: '#34D399',
    glow: 'rgba(52, 211, 153, 0.5)',
    hover: '#6EE7B7',
  },
  selected: {
    base: '#A78BFA',
    glow: 'rgba(167, 139, 250, 0.6)',
    pulse: 'rgba(167, 139, 250, 0.3)',
  },
} as const;

export const HIGHER_DEGREE_COLORS = {
  waveI: {
    primary: '#C4B5FD',      // Violet-300
    glow: 'rgba(196, 181, 253, 0.3)',
    gradient: ['#C4B5FD', '#A78BFA'],
  },
  projectionII: {
    fill: 'rgba(251, 191, 36, 0.12)',
    border: 'rgba(251, 191, 36, 0.45)',
    text: '#FBBF24',
    label: '(II) Zone',
  },
  projectionIII: {
    fill: 'rgba(52, 211, 153, 0.12)',
    border: 'rgba(52, 211, 153, 0.45)',
    text: '#34D399',
    label: '(III) Ziel',
  },
} as const;

export const PROJECTED_ZONE_COLORS = {
  validation: {
    fill: 'rgba(167, 139, 250, 0.12)',
    border: 'rgba(167, 139, 250, 0.45)',
    text: '#A78BFA',
  },
  target: {
    fill: 'rgba(52, 211, 153, 0.12)',
    border: 'rgba(52, 211, 153, 0.45)',
    text: '#34D399',
  },
  correction: {
    fill: 'rgba(251, 191, 36, 0.12)',
    border: 'rgba(251, 191, 36, 0.45)',
    text: '#FBBF24',
  },
} as const;

export const PIN_COLORS = {
  inactive: {
    stroke: 'rgba(168, 162, 158, 0.6)',
    fill: 'rgba(168, 162, 158, 0.3)',
  },
  active: {
    stroke: '#FBBF24',
    fill: 'rgba(251, 191, 36, 0.4)',
  },
} as const;

// Colors for multiple wave counts (primary + alternatives)
export const COUNT_COLORS = [
  { impulse: '#34D399', corrective: '#FBBF24' }, // Primary: Emerald-400/Amber-400
  { impulse: '#60A5FA', corrective: '#F472B6' }, // Alt 1: Blue-400/Pink-400
  { impulse: '#A78BFA', corrective: '#FB923C' }, // Alt 2: Purple-400/Orange-400
  { impulse: '#22D3EE', corrective: '#F87171' }, // Alt 3: Cyan-400/Red-400
  { impulse: '#A3E635', corrective: '#C084FC' }, // Alt 4: Lime-400/Violet-400
] as const;

export function getCountColor(countIndex: number, waveType: 'impulse' | 'corrective'): string {
  const colorSet = COUNT_COLORS[countIndex % COUNT_COLORS.length];
  return colorSet[waveType];
}

// Helper to get wave color based on type
export function getWaveColor(type: 'impulse' | 'corrective') {
  return WAVE_COLORS[type];
}

// Helper to create gradient
export function createGradient(
  ctx: CanvasRenderingContext2D,
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  colors: readonly string[]
): CanvasGradient {
  const gradient = ctx.createLinearGradient(x1, y1, x2, y2);
  gradient.addColorStop(0, colors[0]);
  gradient.addColorStop(1, colors[1]);
  return gradient;
}
