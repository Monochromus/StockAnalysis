from typing import List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class PivotType(str, Enum):
    HIGH = "high"
    LOW = "low"


class Pivot(BaseModel):
    timestamp: datetime
    price: float
    type: PivotType
    index: int = Field(..., description="Index in the original candle series")
    significance: float = Field(0.0, description="Significance score based on swing size")


class PivotSequence(BaseModel):
    pivots: List[Pivot]
    threshold_percent: float
    total_candles: int
