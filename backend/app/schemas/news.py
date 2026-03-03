"""
News Dashboard Schemas - Pydantic models for Gemini-powered market research.
"""

from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class MarketSentiment(str, Enum):
    """Market sentiment classification."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class ImpactLevel(str, Enum):
    """Impact level for upcoming events."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SourceLink(BaseModel):
    """A source reference with grounding score."""
    title: str
    url: str
    grounding_score: Optional[float] = None


class UpcomingEvent(BaseModel):
    """An upcoming market event with date and source."""
    date: str  # ISO date or human-readable
    description: str
    impact: ImpactLevel = ImpactLevel.MEDIUM
    source: Optional[str] = None
    grounding_score: Optional[float] = None


class MarketAssessment(BaseModel):
    """Current market assessment with confidence."""
    summary: str
    sentiment: MarketSentiment
    confidence: float = Field(ge=0.0, le=1.0)
    key_factors: List[str] = []


class SupplyDemandInfo(BaseModel):
    """Supply and demand information."""
    supply_summary: str
    demand_summary: str
    balance_outlook: str


class MacroFactors(BaseModel):
    """Macroeconomic factors affecting the commodity."""
    factors: List[str] = []
    summary: str = ""


class CommodityNewsAnalysis(BaseModel):
    """Complete news analysis for a commodity."""
    symbol: str
    commodity_name: str
    timestamp: str  # ISO timestamp

    # Market Assessment
    market_assessment: MarketAssessment

    # Recent News Summary
    news_summary: str
    news_highlights: List[str] = []

    # Supply & Demand
    supply_demand: Optional[SupplyDemandInfo] = None

    # Macro Factors
    macro_factors: Optional[MacroFactors] = None

    # Upcoming Events (filtered by grounding score)
    upcoming_events: List[UpcomingEvent] = []

    # Sources with grounding scores
    sources: List[SourceLink] = []

    # Google Search Suggestions HTML (for compliance)
    rendered_content: Optional[str] = None

    # Cache metadata
    from_cache: bool = False
    cache_timestamp: Optional[str] = None


# Request/Response Schemas

class CommodityNewsRequest(BaseModel):
    """Request for single commodity news analysis."""
    symbol: str
    force_refresh: bool = False


class NewsDashboardRequest(BaseModel):
    """Request for dashboard with multiple symbols."""
    symbols: List[str]
    force_refresh: bool = False


class NewsAnalysisResponse(BaseModel):
    """Response for single commodity analysis."""
    success: bool
    analysis: Optional[CommodityNewsAnalysis] = None
    error: Optional[str] = None


class NewsDashboardResponse(BaseModel):
    """Response for dashboard with multiple analyses."""
    success: bool
    analyses: List[CommodityNewsAnalysis] = []
    errors: dict = {}  # symbol -> error message
    timestamp: str


class NewsStatusResponse(BaseModel):
    """Status of the Gemini API connection."""
    available: bool
    api_key_configured: bool
    model_name: str
    cache_enabled: bool
    cache_ttl_seconds: int
    error: Optional[str] = None
