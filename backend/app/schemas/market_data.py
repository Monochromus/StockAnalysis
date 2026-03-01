from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class Candle(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class OHLCVData(BaseModel):
    symbol: str
    candles: List[Candle]
    start_date: datetime
    end_date: datetime
    interval: str
    count: int


class ProviderMetadata(BaseModel):
    """Metadata about the data provider that served the request."""
    provider_name: str = Field(..., description="Internal provider name")
    provider_display_name: str = Field(..., description="Human-readable provider name")
    from_cache: bool = Field(False, description="Whether data was served from cache")
    fetch_time_ms: Optional[float] = Field(None, description="Time taken to fetch data in milliseconds")


class ProviderStatus(BaseModel):
    """Status information for a data provider."""
    name: str
    display_name: str
    available: bool
    requires_api_key: bool
    capabilities: List[str]
    priority: int
    rate_limits: dict


class ProvidersStatusResponse(BaseModel):
    """Response containing status of all providers."""
    providers: List[ProviderStatus]


class MarketDataRequest(BaseModel):
    symbol: str = Field(..., description="Ticker symbol")
    period: str = Field("1y", description="Data period (e.g., 1mo, 3mo, 6mo, 1y, 2y)")
    interval: str = Field("1d", description="Data interval (e.g., 1h, 1d, 1wk)")


class MarketDataResponse(BaseModel):
    symbol: str
    data: OHLCVData
    provider: Optional[ProviderMetadata] = None
    warning: Optional[str] = None
