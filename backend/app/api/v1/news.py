"""
News API Endpoints - Gemini-powered market research for commodities.
"""

import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, Query

from app.config import get_settings
from app.schemas.news import (
    NewsAnalysisResponse,
    NewsDashboardResponse,
    NewsStatusResponse,
)
from app.services.news import GeminiNewsClient

logger = logging.getLogger(__name__)
router = APIRouter()

# Singleton client instance
_client: GeminiNewsClient = None


def get_news_client() -> GeminiNewsClient:
    """Get or create the Gemini news client."""
    global _client
    if _client is None:
        _client = GeminiNewsClient()
    return _client


@router.get("/status", response_model=NewsStatusResponse)
async def get_news_status():
    """
    Get the status of the Gemini API connection.

    Returns configuration status and availability.
    """
    settings = get_settings()
    client = get_news_client()

    return NewsStatusResponse(
        available=client.is_available(),
        api_key_configured=bool(settings.gemini_api_key),
        model_name=client.get_active_model(),
        cache_enabled=True,
        cache_ttl_seconds=settings.news_cache_ttl_seconds,
    )


@router.get("/dashboard", response_model=NewsDashboardResponse)
async def get_news_dashboard(
    symbols: List[str] = Query(
        ...,
        description="List of commodity symbols to analyze",
        example=["GC=F", "CL=F", "SI=F"]
    ),
    force_refresh: bool = Query(
        False,
        description="Force refresh all analyses (bypass cache)"
    )
):
    """
    Get news analysis for multiple commodities.

    This endpoint analyzes all provided symbols and returns a dashboard
    with market research for each commodity.
    """
    settings = get_settings()

    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=503,
            detail="GEMINI_API_KEY nicht konfiguriert. Bitte in .env Datei setzen."
        )

    client = get_news_client()

    try:
        results, errors = await client.analyze_multiple(symbols, force_refresh)

        return NewsDashboardResponse(
            success=len(results) > 0,
            analyses=list(results.values()),
            errors=errors,
            timestamp=datetime.utcnow().isoformat(),
        )

    except Exception as e:
        logger.error(f"Dashboard analysis error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Analyse fehlgeschlagen: {str(e)}"
        )


@router.get("/{symbol}", response_model=NewsAnalysisResponse)
async def get_commodity_news(
    symbol: str,
    force_refresh: bool = Query(
        False,
        description="Force refresh analysis (bypass cache)"
    )
):
    """
    Get news analysis for a single commodity.

    Uses cached data if available and not expired (4 hour TTL).
    """
    settings = get_settings()

    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=503,
            detail="GEMINI_API_KEY nicht konfiguriert. Bitte in .env Datei setzen."
        )

    client = get_news_client()

    try:
        analysis = await client.analyze_commodity(symbol, force_refresh)

        return NewsAnalysisResponse(
            success=True,
            analysis=analysis,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=503,
            detail=str(e)
        )

    except Exception as e:
        logger.error(f"Analysis error for {symbol}: {e}")

        # Try to return cached data with error flag
        try:
            cached = client.cache.get(symbol)
            if cached:
                from app.schemas.news import CommodityNewsAnalysis
                analysis = CommodityNewsAnalysis(**cached)
                return NewsAnalysisResponse(
                    success=True,
                    analysis=analysis,
                    error=f"Verwendet gecachte Daten wegen API-Fehler: {str(e)}"
                )
        except Exception:
            pass

        raise HTTPException(
            status_code=500,
            detail=f"Analyse fehlgeschlagen: {str(e)}"
        )


@router.post("/{symbol}/refresh", response_model=NewsAnalysisResponse)
async def refresh_commodity_news(symbol: str):
    """
    Force refresh news analysis for a commodity.

    Invalidates cache and fetches fresh data from Gemini.
    """
    settings = get_settings()

    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=503,
            detail="GEMINI_API_KEY nicht konfiguriert. Bitte in .env Datei setzen."
        )

    client = get_news_client()

    # Invalidate cache first
    client.cache.invalidate(symbol)

    try:
        analysis = await client.analyze_commodity(symbol, force_refresh=True)

        return NewsAnalysisResponse(
            success=True,
            analysis=analysis,
        )

    except Exception as e:
        logger.error(f"Refresh error for {symbol}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Refresh fehlgeschlagen: {str(e)}"
        )
