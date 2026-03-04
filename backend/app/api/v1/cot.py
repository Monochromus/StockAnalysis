"""
COT (Commitments of Traders) API endpoints.
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.config import get_settings
from app.services.cot import COTClient, COTCache, COTMapping, COTAnalyzer
from app.schemas.cot import (
    COTAnalysis,
    COTPositionData,
    COTStatusResponse,
    COTMappingsResponse,
    COTMappingInfo,
    COTDashboardResponse,
    COTDashboardItem,
    COTRefreshResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize cache
settings = get_settings()
_cache = COTCache(
    db_path=getattr(settings, 'cot_cache_db_path', 'data/cot_cache.db'),
    ttl_seconds=getattr(settings, 'cot_cache_ttl_seconds', 86400)
)


def _create_position_data(record: dict) -> COTPositionData:
    """Convert raw COT record to COTPositionData."""
    return COTPositionData(
        date=record.get("report_date", ""),
        open_interest=record.get("open_interest", 0),
        commercial_long=record.get("commercial_long", 0),
        commercial_short=record.get("commercial_short", 0),
        commercial_net=record.get("commercial_net", 0),
        commercial_pct_oi=record.get("commercial_pct_oi", 0.0),
        noncommercial_long=record.get("noncommercial_long", 0),
        noncommercial_short=record.get("noncommercial_short", 0),
        noncommercial_net=record.get("noncommercial_net", 0),
        noncommercial_pct_oi=record.get("noncommercial_pct_oi", 0.0),
        nonreportable_long=record.get("nonreportable_long", 0),
        nonreportable_short=record.get("nonreportable_short", 0),
        nonreportable_net=record.get("nonreportable_net", 0),
    )


# =============================================================================
# STATIC ROUTES (must be defined BEFORE dynamic /{symbol} routes)
# =============================================================================

@router.get("/status", response_model=COTStatusResponse)
async def get_cot_status():
    """
    Get COT API status and supported symbols.
    """
    try:
        with COTClient() as client:
            last_update = client.get_latest_report_date()

        return COTStatusResponse(
            available=True,
            last_cftc_update=last_update,
            cache_enabled=True,
            supported_symbols=COTMapping.get_supported_symbols(),
            supported_groups=COTMapping.get_all_groups(),
        )
    except Exception as e:
        logger.error(f"Error checking COT status: {e}")
        return COTStatusResponse(
            available=False,
            last_cftc_update=None,
            cache_enabled=True,
            supported_symbols=COTMapping.get_supported_symbols(),
            supported_groups=COTMapping.get_all_groups(),
        )


@router.get("/mappings", response_model=COTMappingsResponse)
async def get_cot_mappings():
    """
    Get all available symbol to COT commodity mappings.
    """
    mappings = []
    for symbol in COTMapping.get_supported_symbols():
        info = COTMapping.get_cot_info(symbol)
        if info:
            mappings.append(COTMappingInfo(
                symbol=symbol,
                commodity_name=info["name"],
                group=info["group"],
                exchange=info["exchange"],
            ))

    return COTMappingsResponse(mappings=mappings, count=len(mappings))


@router.get("/dashboard", response_model=COTDashboardResponse)
async def get_cot_dashboard(
    symbols: List[str] = Query(
        default=None,
        description="List of symbols. If empty, uses default selection."
    ),
    force_refresh: bool = Query(default=False),
):
    """
    Get COT dashboard data for multiple symbols.
    """
    # Default symbols if none provided
    if not symbols:
        symbols = ["GC=F", "CL=F", "NG=F", "ZC=F", "ZW=F", "KC=F"]

    items = []
    errors = {}

    for symbol in symbols:
        if not COTMapping.is_supported(symbol):
            errors[symbol] = "Symbol not supported"
            continue

        try:
            # Use the main endpoint logic
            cot_info = COTMapping.get_cot_info(symbol)

            # Check cache
            if not force_refresh:
                cached = _cache.get(symbol)
                if cached:
                    items.append(COTDashboardItem(
                        symbol=symbol,
                        commodity_name=cot_info["name"] if cot_info else "",
                        group=cot_info["group"] if cot_info else "",
                        cot_index_commercial=cached.get("cot_index_commercial", 50.0),
                        cot_index_noncommercial=cached.get("cot_index_noncommercial", 50.0),
                        commercial_net=cached.get("current", {}).get("commercial_net", 0),
                        noncommercial_net=cached.get("current", {}).get("noncommercial_net", 0),
                        weekly_change_commercial=cached.get("weekly_change_commercial", 0),
                        weekly_change_noncommercial=cached.get("weekly_change_noncommercial", 0),
                        signal=cached.get("signal", "neutral"),
                        signal_strength=cached.get("signal_strength", "weak"),
                        last_update=cached.get("last_update", ""),
                    ))
                    continue

            # Fetch fresh
            with COTClient() as client:
                raw_data = client.get_legacy_futures(symbol, weeks=52)

            if not raw_data:
                errors[symbol] = "No data available"
                continue

            analysis = COTAnalyzer.analyze(raw_data, lookback_weeks=52)

            items.append(COTDashboardItem(
                symbol=symbol,
                commodity_name=cot_info["name"] if cot_info else "",
                group=cot_info["group"] if cot_info else "",
                cot_index_commercial=analysis["cot_index_commercial"],
                cot_index_noncommercial=analysis["cot_index_noncommercial"],
                commercial_net=raw_data[0].get("commercial_net", 0),
                noncommercial_net=raw_data[0].get("noncommercial_net", 0),
                weekly_change_commercial=analysis["weekly_change_commercial"],
                weekly_change_noncommercial=analysis["weekly_change_noncommercial"],
                signal=analysis["signal"],
                signal_strength=analysis["signal_strength"],
                last_update=raw_data[0].get("report_date", ""),
            ))

            # Cache the data
            cache_data = {
                "commodity_name": cot_info["name"] if cot_info else "",
                "exchange": cot_info["exchange"] if cot_info else "",
                "report_type": "legacy",
                "last_update": raw_data[0].get("report_date", ""),
                "current": raw_data[0] if raw_data else {},
                "history": raw_data,
                **analysis,
            }
            _cache.set(symbol, cache_data, raw_data[0].get("report_date", ""))

        except Exception as e:
            logger.error(f"Error fetching COT for {symbol}: {e}")
            errors[symbol] = str(e)

    return COTDashboardResponse(
        success=len(items) > 0,
        items=items,
        errors=errors,
        timestamp=datetime.utcnow().isoformat(),
    )


# =============================================================================
# DYNAMIC ROUTES (with {symbol} parameter)
# =============================================================================

@router.get("/{symbol}", response_model=COTAnalysis)
async def get_cot_data(
    symbol: str,
    weeks: int = Query(default=52, ge=4, le=260, description="Weeks of history"),
    lookback_weeks: int = Query(default=52, ge=4, le=260, description="COT Index lookback"),
    force_refresh: bool = Query(default=False, description="Force cache refresh"),
):
    """
    Get COT analysis for a symbol.

    Returns current positions, historical data, COT indices, and trading signals.
    """
    # Validate symbol
    if not COTMapping.is_supported(symbol):
        raise HTTPException(
            status_code=400,
            detail=f"Symbol {symbol} is not supported for COT analysis. "
                   f"Supported symbols: {COTMapping.get_supported_symbols()}"
        )

    # Check cache first
    if not force_refresh:
        cached = _cache.get(symbol)
        if cached:
            logger.debug(f"Returning cached COT data for {symbol}")
            # Rebuild response from cached data
            history = [_create_position_data(r) for r in cached.get("history", [])]
            return COTAnalysis(
                symbol=symbol,
                commodity_name=cached.get("commodity_name", ""),
                exchange=cached.get("exchange", ""),
                report_type=cached.get("report_type", "legacy"),
                last_update=cached.get("last_update", ""),
                current=_create_position_data(cached.get("current", {})),
                history=history[:weeks],
                cot_index_commercial=cached.get("cot_index_commercial", 50.0),
                cot_index_noncommercial=cached.get("cot_index_noncommercial", 50.0),
                lookback_weeks=lookback_weeks,
                weekly_change_commercial=cached.get("weekly_change_commercial", 0),
                weekly_change_noncommercial=cached.get("weekly_change_noncommercial", 0),
                monthly_change_commercial=cached.get("monthly_change_commercial", 0),
                monthly_change_noncommercial=cached.get("monthly_change_noncommercial", 0),
                signal=cached.get("signal", "neutral"),
                signal_strength=cached.get("signal_strength", "weak"),
                interpretation=cached.get("interpretation", ""),
                from_cache=True,
                cache_timestamp=cached.get("cache_timestamp"),
            )

    # Fetch fresh data
    try:
        with COTClient() as client:
            raw_data = client.get_legacy_futures(symbol, weeks=max(weeks, lookback_weeks))

        if not raw_data:
            raise HTTPException(
                status_code=404,
                detail=f"No COT data found for {symbol}"
            )

        # Analyze data
        analysis = COTAnalyzer.analyze(raw_data, lookback_weeks=lookback_weeks)

        # Get mapping info
        cot_info = COTMapping.get_cot_info(symbol)

        # Build position history
        history = [_create_position_data(r) for r in raw_data]

        # Build response
        response = COTAnalysis(
            symbol=symbol,
            commodity_name=cot_info["name"] if cot_info else "",
            exchange=cot_info["exchange"] if cot_info else "",
            report_type="legacy",
            last_update=raw_data[0].get("report_date", "") if raw_data else "",
            current=history[0] if history else _create_position_data({}),
            history=history[:weeks],
            cot_index_commercial=analysis["cot_index_commercial"],
            cot_index_noncommercial=analysis["cot_index_noncommercial"],
            lookback_weeks=lookback_weeks,
            weekly_change_commercial=analysis["weekly_change_commercial"],
            weekly_change_noncommercial=analysis["weekly_change_noncommercial"],
            monthly_change_commercial=analysis["monthly_change_commercial"],
            monthly_change_noncommercial=analysis["monthly_change_noncommercial"],
            signal=analysis["signal"],
            signal_strength=analysis["signal_strength"],
            interpretation=analysis["interpretation"],
            from_cache=False,
            cache_timestamp=None,
        )

        # Cache the response
        cache_data = {
            "commodity_name": response.commodity_name,
            "exchange": response.exchange,
            "report_type": response.report_type,
            "last_update": response.last_update,
            "current": raw_data[0] if raw_data else {},
            "history": raw_data,
            **analysis,
        }
        _cache.set(symbol, cache_data, response.last_update)

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching COT data for {symbol}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching COT data: {str(e)}"
        )


@router.get("/{symbol}/history")
async def get_cot_history(
    symbol: str,
    weeks: int = Query(default=52, ge=4, le=260),
):
    """
    Get historical COT positions for charting.

    Returns a simplified list of position data points.
    """
    if not COTMapping.is_supported(symbol):
        raise HTTPException(
            status_code=400,
            detail=f"Symbol {symbol} is not supported"
        )

    try:
        with COTClient() as client:
            raw_data = client.get_legacy_futures(symbol, weeks=weeks)

        if not raw_data:
            raise HTTPException(status_code=404, detail="No data found")

        return {
            "symbol": symbol,
            "weeks": len(raw_data),
            "data": [_create_position_data(r).model_dump() for r in raw_data]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching COT history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{symbol}/refresh", response_model=COTRefreshResponse)
async def refresh_cot_data(symbol: str):
    """
    Force refresh COT data for a symbol (invalidate cache).
    """
    if not COTMapping.is_supported(symbol):
        raise HTTPException(
            status_code=400,
            detail=f"Symbol {symbol} is not supported"
        )

    # Invalidate cache
    _cache.invalidate(symbol)

    # Fetch fresh data
    try:
        with COTClient() as client:
            raw_data = client.get_legacy_futures(symbol, weeks=52)

        if not raw_data:
            return COTRefreshResponse(
                success=False,
                symbol=symbol,
                message="No COT data available from CFTC",
                new_report_date=None,
            )

        report_date = raw_data[0].get("report_date", "")

        # Analyze and cache
        analysis = COTAnalyzer.analyze(raw_data, lookback_weeks=52)
        cot_info = COTMapping.get_cot_info(symbol)

        cache_data = {
            "commodity_name": cot_info["name"] if cot_info else "",
            "exchange": cot_info["exchange"] if cot_info else "",
            "report_type": "legacy",
            "last_update": report_date,
            "current": raw_data[0] if raw_data else {},
            "history": raw_data,
            **analysis,
        }
        _cache.set(symbol, cache_data, report_date)

        return COTRefreshResponse(
            success=True,
            symbol=symbol,
            message="Cache refreshed successfully",
            new_report_date=report_date,
        )

    except Exception as e:
        logger.error(f"Error refreshing COT data: {e}")
        return COTRefreshResponse(
            success=False,
            symbol=symbol,
            message=f"Error: {str(e)}",
            new_report_date=None,
        )
