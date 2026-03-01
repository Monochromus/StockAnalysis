from datetime import datetime

from fastapi import APIRouter, Depends

from app.services.data_provider import DataProvider, get_data_provider
from app.services.analysis import WaveCounter, WaveExplainer
from app.schemas import AnalysisRequest, AnalysisResponse, PivotResponse, ManualWaveRequest

router = APIRouter()


@router.post("", response_model=AnalysisResponse)
async def analyze_waves(
    request: AnalysisRequest,
    data_provider: DataProvider = Depends(get_data_provider),
):
    """
    Perform full Elliott Wave analysis on a symbol.

    Returns primary wave count, alternatives, validation results,
    Fibonacci scores, and risk/reward levels.
    """
    # Fetch market data
    ohlcv_data, warning = data_provider.get_ohlcv(
        request.symbol,
        period=request.period,
        interval=request.interval,
    )

    # Initialize analysis components
    wave_counter = WaveCounter(zigzag_threshold=request.zigzag_threshold)
    explainer = WaveExplainer()

    # Run analysis - use specific start pivot if provided
    if request.start_pivot_index is not None:
        wave_counts, pivot_sequence = wave_counter.analyze_from_pivot(
            ohlcv_data.candles, request.start_pivot_index
        )
    else:
        wave_counts, pivot_sequence = wave_counter.analyze(ohlcv_data.candles)

    # Get primary and alternatives
    primary_count = wave_counts[0] if wave_counts else None
    alternative_counts = wave_counts[1:4] if len(wave_counts) > 1 else []  # Top 3 alternatives

    # Calculate projected zones and fibonacci levels for each wave count
    def enrich_wave_count(wc):
        """Attach projected_zones and fibonacci_levels to a WaveCount."""
        if not wc or not ohlcv_data.candles:
            return
        zones = wave_counter.calculate_projected_zones(wc, ohlcv_data.candles)
        levels = wave_counter.calculate_fibonacci_levels(wc, ohlcv_data.candles)
        # Merge higher-degree zones for complete patterns
        hd = wave_counter._build_higher_degree(wc, ohlcv_data.candles)
        if hd and hd.projected_zones:
            for zone in hd.projected_zones:
                if not hasattr(zone, 'zone_style') or zone.zone_style == "default":
                    zone.zone_style = zone.zone_type
                zones.append(zone)
        wc.projected_zones = zones
        wc.fibonacci_levels = levels

    enrich_wave_count(primary_count)
    for alt in alternative_counts:
        enrich_wave_count(alt)

    # Top-level zones/levels from primary (for backwards compatibility)
    projected_zones = primary_count.projected_zones if primary_count else []
    fibonacci_levels = primary_count.fibonacci_levels if primary_count else []

    # Calculate risk/reward for primary count
    risk_reward = None
    if primary_count and ohlcv_data.candles:
        current_price = ohlcv_data.candles[-1].close
        risk_reward = wave_counter.calculate_risk_reward(
            primary_count, current_price, ohlcv_data.candles, projected_zones
        )

    # Build higher-degree wave structure (for top-level response field)
    higher_degree = None
    if primary_count:
        higher_degree = wave_counter._build_higher_degree(
            primary_count, ohlcv_data.candles
        )

    # Generate explanation
    explanation = explainer.explain(primary_count, alternative_counts, risk_reward)

    # Convert pivots to dict for charting
    pivots_for_chart = [
        {
            "timestamp": p.timestamp.isoformat(),
            "price": p.price,
            "type": p.type.value,
            "index": p.index,
        }
        for p in pivot_sequence.pivots
    ]

    return AnalysisResponse(
        symbol=request.symbol.upper(),
        timestamp=datetime.utcnow(),
        primary_count=primary_count,
        alternative_counts=alternative_counts,
        risk_reward=risk_reward,
        pivots=pivots_for_chart,
        explanation=explanation,
        warning=warning,
        higher_degree=higher_degree,
        projected_zones=projected_zones,
        fibonacci_levels=fibonacci_levels,
    )


@router.post("/pivots", response_model=PivotResponse)
async def get_pivots(
    request: AnalysisRequest,
    data_provider: DataProvider = Depends(get_data_provider),
):
    """
    Return only pivot points for a symbol (no wave counting).
    Used when initially loading a ticker before manual wave selection.
    """
    ohlcv_data, warning = data_provider.get_ohlcv(
        request.symbol,
        period=request.period,
        interval=request.interval,
    )

    wave_counter = WaveCounter(zigzag_threshold=request.zigzag_threshold)
    pivot_sequence = wave_counter.zigzag.detect_pivots(ohlcv_data.candles)

    pivots_for_chart = [
        {
            "timestamp": p.timestamp.isoformat(),
            "price": p.price,
            "type": p.type.value,
            "index": p.index,
        }
        for p in pivot_sequence.pivots
    ]

    return PivotResponse(
        pivots=pivots_for_chart,
        warning=warning,
    )


@router.post("/manual", response_model=AnalysisResponse)
async def analyze_manual_waves(
    request: ManualWaveRequest,
    data_provider: DataProvider = Depends(get_data_provider),
):
    """
    Perform manual Elliott Wave analysis based on user-selected pivots.

    The user clicks on pivots in chronological order to define their own
    wave structure. This endpoint creates waves from those pivots and
    calculates zones and Fibonacci levels.
    """
    # Fetch market data
    ohlcv_data, warning = data_provider.get_ohlcv(
        request.symbol,
        period=request.period,
        interval=request.interval,
    )

    if len(request.pivot_indices) < 2:
        return AnalysisResponse(
            symbol=request.symbol.upper(),
            timestamp=datetime.utcnow(),
            primary_count=None,
            alternative_counts=[],
            risk_reward=None,
            pivots=[],
            explanation="Mindestens 2 Pivots erforderlich für Wave-Count.",
            warning="Nicht genug Pivots ausgewählt.",
            higher_degree=None,
            projected_zones=[],
            fibonacci_levels=[],
        )

    # Initialize analysis components
    wave_counter = WaveCounter(zigzag_threshold=request.zigzag_threshold)
    explainer = WaveExplainer()

    # Build manual wave count
    primary_count = wave_counter.build_manual_wave_count(
        request.pivot_indices, ohlcv_data.candles
    )

    # Get pivots for chart display
    pivot_sequence = wave_counter.zigzag.detect_pivots(ohlcv_data.candles)

    if not primary_count:
        pivots_for_chart = [
            {
                "timestamp": p.timestamp.isoformat(),
                "price": p.price,
                "type": p.type.value,
                "index": p.index,
            }
            for p in pivot_sequence.pivots
        ]
        return AnalysisResponse(
            symbol=request.symbol.upper(),
            timestamp=datetime.utcnow(),
            primary_count=None,
            alternative_counts=[],
            risk_reward=None,
            pivots=pivots_for_chart,
            explanation="Konnte keinen gültigen Wave-Count erstellen.",
            warning="Ungültige Pivot-Auswahl.",
            higher_degree=None,
            projected_zones=[],
            fibonacci_levels=[],
        )

    # Mark as primary
    primary_count.is_primary = True

    # Calculate projected zones and fibonacci levels
    zones = wave_counter.calculate_projected_zones(primary_count, ohlcv_data.candles)
    levels = wave_counter.calculate_fibonacci_levels(primary_count, ohlcv_data.candles)

    # Merge higher-degree zones for complete patterns
    hd = wave_counter._build_higher_degree(primary_count, ohlcv_data.candles)
    if hd and hd.projected_zones:
        for zone in hd.projected_zones:
            if not hasattr(zone, 'zone_style') or zone.zone_style == "default":
                zone.zone_style = zone.zone_type
            zones.append(zone)

    primary_count.projected_zones = zones
    primary_count.fibonacci_levels = levels

    # Calculate risk/reward
    risk_reward = None
    if ohlcv_data.candles:
        current_price = ohlcv_data.candles[-1].close
        risk_reward = wave_counter.calculate_risk_reward(
            primary_count, current_price, ohlcv_data.candles, zones
        )

    # Build higher-degree wave structure
    higher_degree = wave_counter._build_higher_degree(primary_count, ohlcv_data.candles)

    # Generate explanation
    explanation = explainer.explain(primary_count, [], risk_reward)

    # Convert pivots to dict for charting
    pivots_for_chart = [
        {
            "timestamp": p.timestamp.isoformat(),
            "price": p.price,
            "type": p.type.value,
            "index": p.index,
        }
        for p in pivot_sequence.pivots
    ]

    return AnalysisResponse(
        symbol=request.symbol.upper(),
        timestamp=datetime.utcnow(),
        primary_count=primary_count,
        alternative_counts=[],
        risk_reward=risk_reward,
        pivots=pivots_for_chart,
        explanation=explanation,
        warning=warning,
        higher_degree=higher_degree,
        projected_zones=zones,
        fibonacci_levels=levels,
    )
