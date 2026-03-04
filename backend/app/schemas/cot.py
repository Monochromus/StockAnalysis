"""
Pydantic schemas for COT (Commitments of Traders) data.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal


class COTPositionData(BaseModel):
    """Individual COT position record."""

    date: str = Field(..., description="Report date (YYYY-MM-DD)")
    open_interest: int = Field(..., description="Total open interest")

    # Commercials (Hedgers)
    commercial_long: int = Field(..., description="Commercial long positions")
    commercial_short: int = Field(..., description="Commercial short positions")
    commercial_net: int = Field(..., description="Commercial net position (long - short)")
    commercial_pct_oi: float = Field(..., description="Commercial % of open interest")

    # Non-Commercials (Speculators)
    noncommercial_long: int = Field(..., description="Non-commercial long positions")
    noncommercial_short: int = Field(..., description="Non-commercial short positions")
    noncommercial_net: int = Field(..., description="Non-commercial net position")
    noncommercial_pct_oi: float = Field(..., description="Non-commercial % of open interest")

    # Non-Reportable (Small Traders)
    nonreportable_long: int = Field(..., description="Non-reportable long positions")
    nonreportable_short: int = Field(..., description="Non-reportable short positions")
    nonreportable_net: int = Field(..., description="Non-reportable net position")


class COTAnalysis(BaseModel):
    """Complete COT analysis for a commodity."""

    symbol: str = Field(..., description="Yahoo Finance symbol")
    commodity_name: str = Field(..., description="CFTC commodity name")
    exchange: str = Field(..., description="Exchange name")
    report_type: str = Field(default="legacy", description="Report type (legacy/disaggregated)")
    last_update: str = Field(..., description="Date of last CFTC report")

    # Current position
    current: COTPositionData = Field(..., description="Current week's positions")

    # Historical data
    history: List[COTPositionData] = Field(
        default_factory=list,
        description="Historical positions (newest first)"
    )

    # Calculated indicators
    cot_index_commercial: float = Field(
        ...,
        ge=0,
        le=100,
        description="Commercial COT Index (0-100)"
    )
    cot_index_noncommercial: float = Field(
        ...,
        ge=0,
        le=100,
        description="Non-commercial COT Index (0-100)"
    )
    lookback_weeks: int = Field(
        default=52,
        description="Lookback period for COT Index calculation"
    )

    # Changes
    weekly_change_commercial: int = Field(..., description="Weekly change in commercial net")
    weekly_change_noncommercial: int = Field(..., description="Weekly change in non-commercial net")
    monthly_change_commercial: int = Field(..., description="4-week change in commercial net")
    monthly_change_noncommercial: int = Field(..., description="4-week change in non-commercial net")

    # Signal interpretation
    signal: Literal["bullish", "bearish", "neutral"] = Field(
        ...,
        description="Trading signal based on COT analysis"
    )
    signal_strength: Literal["strong", "moderate", "weak"] = Field(
        ...,
        description="Signal strength"
    )
    interpretation: str = Field(..., description="Textual interpretation of the signal")

    # Cache metadata
    from_cache: bool = Field(default=False, description="Whether data is from cache")
    cache_timestamp: Optional[str] = Field(default=None, description="Cache timestamp")


class COTDashboardItem(BaseModel):
    """Summary item for dashboard display."""

    symbol: str
    commodity_name: str
    group: str
    cot_index_commercial: float
    cot_index_noncommercial: float
    commercial_net: int
    noncommercial_net: int
    weekly_change_commercial: int
    weekly_change_noncommercial: int
    signal: str
    signal_strength: str
    last_update: str
    error: Optional[str] = None


class COTDashboardResponse(BaseModel):
    """Response for multi-symbol dashboard."""

    success: bool
    items: List[COTDashboardItem]
    errors: dict = Field(default_factory=dict)
    timestamp: str


class COTStatusResponse(BaseModel):
    """API status response."""

    available: bool = Field(..., description="Whether COT API is available")
    last_cftc_update: Optional[str] = Field(
        None,
        description="Date of last CFTC report update"
    )
    cache_enabled: bool = Field(default=True, description="Whether caching is enabled")
    supported_symbols: List[str] = Field(
        default_factory=list,
        description="List of supported Yahoo Finance symbols"
    )
    supported_groups: List[str] = Field(
        default_factory=list,
        description="List of supported commodity groups"
    )


class COTMappingInfo(BaseModel):
    """Symbol mapping information."""

    symbol: str
    commodity_name: str
    group: str
    exchange: str


class COTMappingsResponse(BaseModel):
    """Response with all available symbol mappings."""

    mappings: List[COTMappingInfo]
    count: int


class COTHistoryRequest(BaseModel):
    """Request for historical COT data."""

    weeks: int = Field(default=52, ge=1, le=260, description="Number of weeks of history")
    lookback_weeks: int = Field(
        default=52,
        ge=4,
        le=260,
        description="Lookback period for COT Index"
    )


class COTRefreshResponse(BaseModel):
    """Response after cache refresh."""

    success: bool
    symbol: str
    message: str
    new_report_date: Optional[str] = None
