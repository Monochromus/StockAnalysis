from fastapi import APIRouter, Depends, Query

from app.services.data_provider import DataProvider, get_data_provider
from app.schemas.ticker import TickerSearchResponse, TickerValidationResponse

router = APIRouter()


@router.get("/search", response_model=TickerSearchResponse)
async def search_tickers(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Max results"),
    data_provider: DataProvider = Depends(get_data_provider),
):
    """Search for tickers matching the query."""
    results = data_provider.search_tickers(q, limit=limit)
    return TickerSearchResponse(
        query=q,
        results=results,
        count=len(results),
    )


@router.get("/validate/{symbol}", response_model=TickerValidationResponse)
async def validate_ticker(
    symbol: str,
    data_provider: DataProvider = Depends(get_data_provider),
):
    """Validate if a ticker symbol exists and get its info."""
    try:
        info = data_provider.get_ticker_info(symbol)
        return TickerValidationResponse(
            valid=True,
            symbol=symbol.upper(),
            info=info,
        )
    except Exception as e:
        return TickerValidationResponse(
            valid=False,
            symbol=symbol.upper(),
            error=str(e),
        )
