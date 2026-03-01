from typing import Optional, List

from fastapi import APIRouter, Depends, Query

from app.services.providers import DataProviderManager, get_provider_manager
from app.schemas.market_data import (
    MarketDataResponse,
    ProviderMetadata,
    ProviderStatus,
    ProvidersStatusResponse,
)

router = APIRouter()


@router.get("/providers/status", response_model=ProvidersStatusResponse)
async def get_providers_status(
    provider_manager: DataProviderManager = Depends(get_provider_manager),
):
    """
    Get status of all available data providers.

    Returns information about each provider including:
    - Whether it's available (API key configured if required)
    - Supported capabilities
    - Rate limit status
    """
    status_list = provider_manager.get_providers_status()
    providers = [ProviderStatus(**s) for s in status_list]
    return ProvidersStatusResponse(providers=providers)


@router.get("/{symbol}", response_model=MarketDataResponse)
async def get_market_data(
    symbol: str,
    period: str = Query("1y", description="Data period (1mo, 3mo, 6mo, 1y, 2y)"),
    interval: str = Query("1d", description="Data interval (1m, 5m, 15m, 30m, 1h, 1d, 1wk)"),
    provider: Optional[str] = Query(
        None,
        description="Preferred data provider (yfinance, alpha_vantage, twelve_data). If not specified, auto-selects best provider.",
    ),
    provider_manager: DataProviderManager = Depends(get_provider_manager),
):
    """
    Get historical OHLCV data for a symbol.

    The provider parameter allows you to specify which data source to use:
    - **auto** (default): Automatically selects the best provider based on interval
    - **yfinance**: Yahoo Finance (free, no API key required)
    - **alpha_vantage**: Alpha Vantage (requires API key, best for intraday)
    - **twelve_data**: Twelve Data (requires API key)

    For intraday intervals (1m, 5m, 15m, 30m, 1h), Alpha Vantage or Twelve Data
    are preferred if API keys are configured.

    For daily/weekly intervals, yfinance is typically used.
    """
    data, metadata = await provider_manager.get_ohlcv(
        symbol,
        period=period,
        interval=interval,
        user_preference=provider,
    )

    return MarketDataResponse(
        symbol=symbol.upper(),
        data=data,
        provider=ProviderMetadata(
            provider_name=metadata.provider_name,
            provider_display_name=metadata.provider_display_name,
            from_cache=metadata.from_cache,
            fetch_time_ms=metadata.fetch_time_ms,
        ),
        warning=None,
    )
