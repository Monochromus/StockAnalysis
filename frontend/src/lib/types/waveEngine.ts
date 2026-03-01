/**
 * TypeScript types for the Wave Engine.
 * These mirror the backend Pydantic schemas.
 */

// ============= Enums =============

export type PivotStatus = 'potential' | 'confirmed' | 'promoted' | 'invalid';
export type RegimeType = 'trending' | 'mean_reverting' | 'random_walk';
export type TimeframeLevel = '5m' | '15m' | '1h' | '4h' | '1d' | '1wk';
export type PivotType = 'high' | 'low';

// ============= Configuration Types =============

export interface DFAConfig {
  window_size: number;
  polynomial_order: number;
  min_segment_size: number;
  max_segment_ratio: number;
}

export interface ThresholdConfig {
  atr_period: number;
  beta_min: number;
  beta_max: number;
  sigmoid_k: number;
  alpha_mid: number;
}

export interface RegimeConfig {
  ewma_lambda_slow: number;
  ewma_lambda_fast: number;
  regime_change_threshold: number;
  trending_threshold: number;
  mean_reverting_threshold: number;
}

export interface ConfidenceWeights {
  w1_threshold_distance: number;
  w2_timeframe_consistency: number;
  w3_dfa_stability: number;
  w4_structural_validity: number;
}

export interface EngineConfig {
  dfa: DFAConfig;
  threshold: ThresholdConfig;
  regime: RegimeConfig;
  confidence_weights: ConfidenceWeights;
  fibonacci_tolerance: number;
  enabled_timeframes: TimeframeLevel[];
}

// ============= Default Configurations =============

export const DEFAULT_DFA_CONFIG: DFAConfig = {
  window_size: 150,
  polynomial_order: 2,
  min_segment_size: 4,
  max_segment_ratio: 0.25,
};

export const DEFAULT_THRESHOLD_CONFIG: ThresholdConfig = {
  atr_period: 14,
  beta_min: 0.5,
  beta_max: 3.0,
  sigmoid_k: 10.0,
  alpha_mid: 0.5,
};

export const DEFAULT_REGIME_CONFIG: RegimeConfig = {
  ewma_lambda_slow: 0.05,
  ewma_lambda_fast: 0.3,
  regime_change_threshold: 0.1,
  trending_threshold: 0.65,
  mean_reverting_threshold: 0.35,
};

export const DEFAULT_CONFIDENCE_WEIGHTS: ConfidenceWeights = {
  w1_threshold_distance: 0.30,
  w2_timeframe_consistency: 0.35,
  w3_dfa_stability: 0.15,
  w4_structural_validity: 0.20,
};

export const DEFAULT_ENGINE_CONFIG: EngineConfig = {
  dfa: DEFAULT_DFA_CONFIG,
  threshold: DEFAULT_THRESHOLD_CONFIG,
  regime: DEFAULT_REGIME_CONFIG,
  confidence_weights: DEFAULT_CONFIDENCE_WEIGHTS,
  fibonacci_tolerance: 0.05,
  enabled_timeframes: ['1d'],
};

// ============= Preset Configurations =============

export const PRESET_CONFIGS: Record<string, Partial<EngineConfig>> = {
  default: {},
  sensitive: {
    dfa: { ...DEFAULT_DFA_CONFIG, window_size: 100 },
    threshold: { ...DEFAULT_THRESHOLD_CONFIG, beta_min: 0.3, beta_max: 2.0, alpha_mid: 0.45 },
  },
  conservative: {
    dfa: { ...DEFAULT_DFA_CONFIG, window_size: 200 },
    threshold: { ...DEFAULT_THRESHOLD_CONFIG, beta_min: 0.8, beta_max: 4.0, alpha_mid: 0.55 },
  },
  trending: {
    threshold: { ...DEFAULT_THRESHOLD_CONFIG, alpha_mid: 0.6, beta_max: 3.5 },
    regime: { ...DEFAULT_REGIME_CONFIG, trending_threshold: 0.60 },
  },
  mean_reverting: {
    threshold: { ...DEFAULT_THRESHOLD_CONFIG, alpha_mid: 0.4, beta_min: 0.4 },
    regime: { ...DEFAULT_REGIME_CONFIG, mean_reverting_threshold: 0.40 },
  },
};

// ============= DFA Types =============

export interface DFAResult {
  alpha: number;
  r_squared: number;
  segment_sizes: number[];
  fluctuations: number[];
  std_error: number;
  data_points: number;
  regime: string;
  confidence_category: string;
}

// ============= Regime Types =============

export interface RegimeEvent {
  timestamp: string;
  from_regime: RegimeType;
  to_regime: RegimeType;
  from_alpha: number;
  to_alpha: number;
  confidence: number;
}

export interface RegimeState {
  current_regime: RegimeType;
  current_alpha: number;
  ewma_alpha: number;
  regime_duration_bars: number;
  regime_start: string | null;
  stability_score: number;
  regime_strength: string;
}

// ============= Pivot Types =============

export interface ConfidenceComponents {
  k1_threshold_distance: number;
  k2_timeframe_consistency: number;
  k3_dfa_stability: number;
  k4_structural_validity: number;
}

export interface EnhancedPivot {
  timestamp: string;
  price: number;
  type: PivotType;
  index: number;
  amplitude: number;
  significance: number;
  status: PivotStatus;
  overall_confidence: number;
  confidence_components: ConfidenceComponents | null;
  alpha_at_creation: number;
  tau_at_creation: number;
  regime_at_creation: RegimeType;
  timeframe: string;
  pivot_id: string;
  parent_pivot_id: string | null;
  child_pivot_ids: string[];
}

// ============= Threshold Types =============

export interface ThresholdResult {
  tau: number;
  atr: number;
  multiplier: number;
  alpha: number;
  tau_percent: number;
  explanation: string;
}

// ============= API Request/Response Types =============

export interface WaveEngineRequest {
  symbol: string;
  period: string;
  interval: string;
  config?: EngineConfig;
  start_pivot_index?: number;
}

export interface WaveEngineResponse {
  symbol: string;
  timestamp: string;
  dfa_result: DFAResult;
  regime_state: RegimeState;
  regime_events: RegimeEvent[];
  threshold_result: ThresholdResult;
  pivots: EnhancedPivot[];
  pivot_summary: {
    total: number;
    confirmed: number;
    potential: number;
    high_confidence: number;
    average_confidence: number;
  };
  timeframe_results: Record<string, unknown>;
  primary_count: unknown | null;
  alternative_counts: unknown[];
  risk_reward: unknown | null;
  explanation: string | null;
  config_used: EngineConfig;
  warning: string | null;
  data_points: number;
}

export interface ConfigValidationResponse {
  valid: boolean;
  errors: string[];
  warnings: string[];
  effective_config: EngineConfig | null;
}

// ============= Parameter Metadata =============

export interface ParameterMeta {
  key: string;
  label: string;
  description: string;
  min: number;
  max: number;
  step: number;
  unit?: string;
}

export const DFA_PARAMETERS: ParameterMeta[] = [
  {
    key: 'window_size',
    label: 'Fenstergröße',
    description: 'Anzahl der Datenpunkte für die DFA-Berechnung',
    min: 50,
    max: 500,
    step: 10,
    unit: 'Kerzen',
  },
  {
    key: 'polynomial_order',
    label: 'Polynomordnung',
    description: 'Ordnung des Detrending-Polynoms (1=linear, 2=quadratisch, 3=kubisch)',
    min: 1,
    max: 3,
    step: 1,
  },
  {
    key: 'min_segment_size',
    label: 'Min. Segmentgröße',
    description: 'Minimale Größe der DFA-Segmente',
    min: 2,
    max: 10,
    step: 1,
  },
];

export const THRESHOLD_PARAMETERS: ParameterMeta[] = [
  {
    key: 'atr_period',
    label: 'ATR Periode',
    description: 'Periode für die ATR-Berechnung',
    min: 5,
    max: 50,
    step: 1,
    unit: 'Kerzen',
  },
  {
    key: 'beta_min',
    label: 'β min',
    description: 'Minimaler Threshold-Multiplikator (für mean-reverting Märkte)',
    min: 0.1,
    max: 2.0,
    step: 0.1,
  },
  {
    key: 'beta_max',
    label: 'β max',
    description: 'Maximaler Threshold-Multiplikator (für Trendmärkte)',
    min: 1.0,
    max: 5.0,
    step: 0.1,
  },
  {
    key: 'sigmoid_k',
    label: 'Sigmoid Steilheit (k)',
    description: 'Steilheit des Sigmoid-Übergangs',
    min: 1,
    max: 50,
    step: 1,
  },
  {
    key: 'alpha_mid',
    label: 'α Mittelpunkt',
    description: 'Wendepunkt der Sigmoid-Funktion',
    min: 0.3,
    max: 0.7,
    step: 0.05,
  },
];

export const REGIME_PARAMETERS: ParameterMeta[] = [
  {
    key: 'ewma_lambda_slow',
    label: 'λ langsam',
    description: 'EWMA-Glättungsfaktor für stabile Phasen',
    min: 0.01,
    max: 0.2,
    step: 0.01,
  },
  {
    key: 'ewma_lambda_fast',
    label: 'λ schnell',
    description: 'EWMA-Glättungsfaktor für Regime-Wechsel',
    min: 0.1,
    max: 0.5,
    step: 0.05,
  },
  {
    key: 'regime_change_threshold',
    label: 'Regime-Schwelle',
    description: 'α-Änderung zur Erkennung eines Regime-Wechsels',
    min: 0.05,
    max: 0.3,
    step: 0.01,
  },
];

export const CONFIDENCE_PARAMETERS: ParameterMeta[] = [
  {
    key: 'w1_threshold_distance',
    label: 'Gewicht: Threshold-Abstand',
    description: 'Gewichtung für Amplitude über Threshold',
    min: 0,
    max: 1,
    step: 0.05,
  },
  {
    key: 'w2_timeframe_consistency',
    label: 'Gewicht: Timeframe-Konsistenz',
    description: 'Gewichtung für Multi-Timeframe-Bestätigung',
    min: 0,
    max: 1,
    step: 0.05,
  },
  {
    key: 'w3_dfa_stability',
    label: 'Gewicht: DFA-Stabilität',
    description: 'Gewichtung für α-Stabilität',
    min: 0,
    max: 1,
    step: 0.05,
  },
  {
    key: 'w4_structural_validity',
    label: 'Gewicht: Struktur-Validität',
    description: 'Gewichtung für strukturelle Konsistenz',
    min: 0,
    max: 1,
    step: 0.05,
  },
];
