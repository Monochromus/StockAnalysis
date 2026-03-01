from typing import Optional, List
from pydantic import BaseModel, Field


class TickerInfo(BaseModel):
    symbol: str = Field(..., description="Ticker symbol (e.g., AAPL)")
    name: str = Field(..., description="Company name")
    exchange: Optional[str] = Field(None, description="Exchange (e.g., NASDAQ)")
    type: Optional[str] = Field(None, description="Instrument type (e.g., EQUITY)")
    currency: Optional[str] = Field(None, description="Currency (e.g., USD)")


class TickerSearchResult(BaseModel):
    symbol: str
    name: str
    exchange: Optional[str] = None
    score: float = Field(0.0, description="Relevance score")


class TickerSearchResponse(BaseModel):
    query: str
    results: List[TickerSearchResult]
    count: int


class TickerValidationResponse(BaseModel):
    valid: bool
    symbol: str
    info: Optional[TickerInfo] = None
    error: Optional[str] = None
