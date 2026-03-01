"""
Pydantic schemas for the Wave Engine API.

These schemas define the request/response format for the wave engine endpoints
and provide validation for all configurable parameters.
"""

from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


# ============= Enums =============

class PivotStatus(str, Enum):
    """Status of a pivot in its lifecycle."""

    POTENTIAL = "potential"
    CONFIRMED = "confirmed"
    PROMOTED = "promoted"
    INVALID = "invalid"


class RegimeType(str, Enum):
    """Market regime classification."""

    TRENDING = "trending"
    MEAN_REVERTING = "mean_reverting"
    RANDOM_WALK = "random_walk"


class TimeframeLevel(str, Enum):
    """Supported timeframe levels."""

    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1wk"


class PivotType(str, Enum):
    """Type of pivot point."""

    HIGH = "high"
    LOW = "low"


# ============= Configuration Schemas =============

class DFAConfigSchema(BaseModel):
    """DFA calculation parameters."""

    window_size: int = Field(
        150, ge=50, le=500,
        description="Rolling DFA window size (number of data points)"
    )
    polynomial_order: int = Field(
        2, ge=1, le=3,
        description="Polynomial order for detrending (1=linear, 2=quadratic, 3=cubic)"
    )
    min_segment_size: int = Field(
        4, ge=2, le=10,
        description="Minimum segment size for DFA calculation"
    )
    max_segment_ratio: float = Field(
        0.25, gt=0, le=0.5,
        description="Maximum segment size as ratio of data length"
    )


class ThresholdConfigSchema(BaseModel):
    """Adaptive threshold parameters."""

    atr_period: int = Field(
        14, ge=5, le=50,
        description="Period for ATR calculation"
    )
    beta_min: float = Field(
        0.5, ge=0.1, le=2.0,
        description="Minimum threshold multiplier (for mean-reverting markets)"
    )
    beta_max: float = Field(
        3.0, ge=1.0, le=5.0,
        description="Maximum threshold multiplier (for trending markets)"
    )
    sigmoid_k: float = Field(
        10.0, ge=1.0, le=50.0,
        description="Steepness of sigmoid transition"
    )
    alpha_mid: float = Field(
        0.5, ge=0.3, le=0.7,
        description="Midpoint of sigmoid (inflection point)"
    )


class RegimeConfigSchema(BaseModel):
    """Regime detection parameters."""

    ewma_lambda_slow: float = Field(
        0.05, ge=0.01, le=0.2,
        description="EWMA smoothing factor for stable conditions"
    )
    ewma_lambda_fast: float = Field(
        0.3, ge=0.1, le=0.5,
        description="EWMA smoothing factor for regime transitions"
    )
    regime_change_threshold: float = Field(
        0.1, ge=0.05, le=0.3,
        description="Alpha change threshold to detect regime change"
    )
    trending_threshold: float = Field(
        0.65, ge=0.55, le=0.8,
        description="Alpha above which market is classified as trending"
    )
    mean_reverting_threshold: float = Field(
        0.35, ge=0.2, le=0.45,
        description="Alpha below which market is classified as mean-reverting"
    )


class ConfidenceWeightsSchema(BaseModel):
    """Weights for confidence score components."""

    w1_threshold_distance: float = Field(
        0.30, ge=0, le=1,
        description="Weight for threshold distance component"
    )
    w2_timeframe_consistency: float = Field(
        0.35, ge=0, le=1,
        description="Weight for timeframe consistency component"
    )
    w3_dfa_stability: float = Field(
        0.15, ge=0, le=1,
        description="Weight for DFA stability component"
    )
    w4_structural_validity: float = Field(
        0.20, ge=0, le=1,
        description="Weight for structural validity component"
    )


class EngineConfigSchema(BaseModel):
    """Complete wave engine configuration."""

    dfa: DFAConfigSchema = Field(default_factory=DFAConfigSchema)
    threshold: ThresholdConfigSchema = Field(default_factory=ThresholdConfigSchema)
    regime: RegimeConfigSchema = Field(default_factory=RegimeConfigSchema)
    confidence_weights: ConfidenceWeightsSchema = Field(default_factory=ConfidenceWeightsSchema)
    fibonacci_tolerance: float = Field(
        0.05, ge=0.01, le=0.2,
        description="Tolerance for Fibonacci ratio matching (±5% by default)"
    )
    enabled_timeframes: List[TimeframeLevel] = Field(
        default=[TimeframeLevel.D1],
        description="Active timeframes for analysis"
    )


# ============= DFA Schemas =============

class DFAResultSchema(BaseModel):
    """Result of a DFA calculation."""

    alpha: float = Field(..., description="DFA exponent (Hurst exponent)")
    r_squared: float = Field(..., ge=0, le=1, description="Goodness of fit")
    segment_sizes: List[int] = Field(..., description="Segment sizes used")
    fluctuations: List[float] = Field(..., description="F(n) values")
    std_error: float = Field(..., description="Standard error of alpha estimate")
    data_points: int = Field(..., description="Number of data points analyzed")
    regime: str = Field(..., description="Inferred market regime")
    confidence_category: str = Field(..., description="Confidence in the estimate")


# ============= Regime Schemas =============

class RegimeEventSchema(BaseModel):
    """A regime change event."""

    timestamp: datetime
    from_regime: RegimeType
    to_regime: RegimeType
    from_alpha: float
    to_alpha: float
    confidence: float = Field(..., ge=0, le=1)


class RegimeStateSchema(BaseModel):
    """Current market regime state."""

    current_regime: RegimeType
    current_alpha: float
    ewma_alpha: float
    regime_duration_bars: int
    regime_start: Optional[datetime] = None
    stability_score: float = Field(..., ge=0, le=1)
    regime_strength: str


# ============= Pivot Schemas =============

class ConfidenceComponentsSchema(BaseModel):
    """Breakdown of confidence score components."""

    k1_threshold_distance: float = Field(..., ge=0, le=1)
    k2_timeframe_consistency: float = Field(..., ge=0, le=1)
    k3_dfa_stability: float = Field(..., ge=0, le=1)
    k4_structural_validity: float = Field(..., ge=0, le=1)


class EnhancedPivotSchema(BaseModel):
    """Enhanced pivot with all metadata."""

    timestamp: datetime
    price: float
    type: PivotType
    index: int
    amplitude: float
    significance: float
    status: PivotStatus
    overall_confidence: float = Field(..., ge=0, le=100)
    confidence_components: Optional[ConfidenceComponentsSchema] = None
    alpha_at_creation: float
    tau_at_creation: float
    regime_at_creation: RegimeType
    timeframe: str
    pivot_id: str
    parent_pivot_id: Optional[str] = None
    child_pivot_ids: List[str] = Field(default_factory=list)


# ============= Threshold Schemas =============

class ThresholdResultSchema(BaseModel):
    """Result of adaptive threshold calculation."""

    tau: float = Field(..., description="Adaptive threshold value (price units)")
    atr: float = Field(..., description="ATR value used")
    multiplier: float = Field(..., description="Sigmoid multiplier f(α)")
    alpha: float = Field(..., description="DFA alpha used")
    tau_percent: float = Field(..., description="Threshold as % of price")
    explanation: str = Field(..., description="Human-readable explanation")


# ============= Timeframe Schemas =============

class TimeframeResultSchema(BaseModel):
    """Analysis result for a single timeframe."""

    timeframe: TimeframeLevel
    pivots: List[EnhancedPivotSchema]
    current_alpha: float
    current_tau: float
    regime_state: RegimeStateSchema
    pivot_count: int
    confirmed_pivot_count: int


# ============= Request/Response Schemas =============

class WaveEngineRequest(BaseModel):
    """Request for wave engine analysis."""

    symbol: str = Field(..., description="Ticker symbol to analyze")
    period: str = Field("1y", description="Data period (1mo, 3mo, 6mo, 1y, 2y, 5y)")
    interval: str = Field("1d", description="Data interval (1h, 4h, 1d, 1wk)")
    config: Optional[EngineConfigSchema] = Field(
        None, description="Custom engine configuration (uses defaults if not provided)"
    )
    start_pivot_index: Optional[int] = Field(
        None, description="Start analysis from specific pivot index"
    )


class WaveEngineResponse(BaseModel):
    """Full wave engine analysis response."""

    symbol: str
    timestamp: datetime

    # DFA & Regime
    dfa_result: DFAResultSchema
    regime_state: RegimeStateSchema
    regime_events: List[RegimeEventSchema] = Field(default_factory=list)

    # Threshold
    threshold_result: ThresholdResultSchema

    # Pivots
    pivots: List[EnhancedPivotSchema]
    pivot_summary: Dict[str, Any] = Field(default_factory=dict)

    # Per-timeframe results (for multi-timeframe)
    timeframe_results: Dict[str, TimeframeResultSchema] = Field(default_factory=dict)

    # Backward compatible fields
    primary_count: Optional[Dict[str, Any]] = None
    alternative_counts: List[Dict[str, Any]] = Field(default_factory=list)
    risk_reward: Optional[Dict[str, Any]] = None
    explanation: Optional[str] = None

    # Metadata
    config_used: EngineConfigSchema
    warning: Optional[str] = None
    data_points: int = 0


class DFAOnlyResponse(BaseModel):
    """Response for DFA-only endpoint."""

    symbol: str
    timestamp: datetime
    dfa_result: DFAResultSchema
    regime_state: RegimeStateSchema


class RegimeOnlyResponse(BaseModel):
    """Response for regime-only endpoint."""

    symbol: str
    timestamp: datetime
    regime_state: RegimeStateSchema
    regime_events: List[RegimeEventSchema] = Field(default_factory=list)


class ThresholdOnlyResponse(BaseModel):
    """Response for threshold-only endpoint."""

    symbol: str
    timestamp: datetime
    threshold_result: ThresholdResultSchema
    dfa_alpha: float
    regime: RegimeType


class ConfigValidationResponse(BaseModel):
    """Response for config validation endpoint."""

    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    effective_config: Optional[EngineConfigSchema] = None
