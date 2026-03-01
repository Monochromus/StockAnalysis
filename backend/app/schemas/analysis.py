from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class WaveType(str, Enum):
    IMPULSE = "impulse"
    CORRECTIVE = "corrective"


class WaveLabel(str, Enum):
    W1 = "1"
    W2 = "2"
    W3 = "3"
    W4 = "4"
    W5 = "5"
    WA = "A"
    WB = "B"
    WC = "C"


class Wave(BaseModel):
    label: WaveLabel
    type: WaveType
    start_timestamp: datetime
    end_timestamp: datetime
    start_price: float
    end_price: float
    start_index: int
    end_index: int


class ValidationResult(BaseModel):
    rule_name: str = Field(..., description="Name of the validation rule")
    rule_description: str = Field(..., description="Description of the rule")
    passed: bool
    details: Optional[str] = None


class FibonacciScore(BaseModel):
    wave_label: WaveLabel
    expected_ratio: float = Field(..., description="Expected Fibonacci ratio")
    actual_ratio: float = Field(..., description="Actual measured ratio")
    deviation: float = Field(..., description="Deviation from expected")
    score: float = Field(..., ge=0, le=100, description="Score 0-100")


class ProjectedZone(BaseModel):
    label: str
    price_top: float
    price_bottom: float
    time_start: datetime
    time_end: datetime
    start_bar_index: Optional[float] = None
    end_bar_index: Optional[float] = None
    zone_type: str  # "correction" | "target" | "validation"
    zone_style: str = "default"  # "validation" | "target" | "correction"


class FibonacciLevel(BaseModel):
    price: float
    ratio: float
    label: str
    style: str  # "retracement" | "extension"
    context: str = "default"  # "target" | "correction" – maps to zone color
    ref_timestamp: datetime
    ref_bar_index: Optional[float] = None


class WaveCount(BaseModel):
    waves: List[Wave]
    wave_type: WaveType
    is_complete: bool
    validation_results: List[ValidationResult]
    fibonacci_scores: List[FibonacciScore]
    overall_confidence: float = Field(..., ge=0, le=100)
    is_primary: bool = False
    projected_zones: List[ProjectedZone] = []
    fibonacci_levels: List[FibonacciLevel] = []


class RiskReward(BaseModel):
    entry_price: float
    stop_loss: float
    risk_reward_ratio: float
    time_start: Optional[datetime] = None
    stop_time_end: Optional[datetime] = None


class AnalysisRequest(BaseModel):
    symbol: str = Field(..., description="Ticker symbol")
    period: str = Field("1y", description="Data period")
    interval: str = Field("1d", description="Data interval")
    zigzag_threshold: float = Field(5.0, ge=1.0, le=20.0, description="ZigZag threshold percentage")
    start_pivot_index: Optional[int] = Field(None, description="Optional pivot index to start wave count from")


class HigherDegreeLabel(str, Enum):
    I = "(I)"
    II = "(II)"
    III = "(III)"


class HigherDegreeWave(BaseModel):
    label: HigherDegreeLabel
    start_timestamp: datetime
    end_timestamp: datetime
    start_price: float
    end_price: float
    start_index: int
    end_index: int


class HigherDegreeAnalysis(BaseModel):
    completed_wave: HigherDegreeWave
    projected_zones: List[ProjectedZone]
    direction: str  # "up" | "down"


class AnalysisResponse(BaseModel):
    symbol: str
    timestamp: datetime
    primary_count: Optional[WaveCount] = None
    alternative_counts: List[WaveCount] = []
    risk_reward: Optional[RiskReward] = None
    pivots: List[Dict[str, Any]] = Field(default_factory=list, description="Raw pivots for charting")
    explanation: Optional[str] = None
    warning: Optional[str] = None
    higher_degree: Optional[HigherDegreeAnalysis] = None
    projected_zones: List[ProjectedZone] = []
    fibonacci_levels: List[FibonacciLevel] = []


class PivotResponse(BaseModel):
    pivots: List[Dict[str, Any]]
    warning: Optional[str] = None


class ManualWaveRequest(BaseModel):
    """Request for manual Elliott Wave counting."""
    symbol: str = Field(..., description="Ticker symbol")
    period: str = Field("1y", description="Data period")
    interval: str = Field("1d", description="Data interval")
    pivot_indices: List[int] = Field(..., description="List of candle indices for wave pivots (min 2)")
    zigzag_threshold: float = Field(5.0, ge=1.0, le=20.0, description="ZigZag threshold percentage")
