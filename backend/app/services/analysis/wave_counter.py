from __future__ import annotations
from datetime import datetime, timedelta

from app.schemas import (
    Candle,
    Pivot,
    PivotType,
    PivotSequence,
    Wave,
    WaveType,
    WaveLabel,
    WaveCount,
    RiskReward,
    HigherDegreeLabel,
    HigherDegreeWave,
    ProjectedZone,
    FibonacciLevel,
    HigherDegreeAnalysis,
)
from app.services.analysis.zigzag import ZigZagDetector
from app.services.analysis.wave_validator import WaveValidator
from app.services.analysis.fibonacci import FibonacciAnalyzer


class WaveCounter:
    """
    Main orchestrator for Elliott Wave counting.
    Identifies wave patterns from pivot sequences.
    """

    def __init__(
        self,
        zigzag_threshold: float = 5.0,
        validator: WaveValidator | None = None,
        fib_analyzer: FibonacciAnalyzer | None = None,
        min_wave_candles: int = 3,
    ):
        self.zigzag = ZigZagDetector(threshold_percent=zigzag_threshold)
        self.validator = validator or WaveValidator()
        self.fib_analyzer = fib_analyzer or FibonacciAnalyzer()
        self.min_wave_candles = min_wave_candles

    def analyze(self, candles: list[Candle]) -> tuple[list[WaveCount], PivotSequence]:
        """
        Perform full wave analysis on candle data.

        Args:
            candles: List of OHLCV candles

        Returns:
            Tuple of (list of wave counts, pivot sequence)
        """
        # Detect pivots
        pivot_sequence = self.zigzag.detect_pivots(candles)

        if len(pivot_sequence.pivots) < 5:
            return [], pivot_sequence

        # Find impulse patterns
        wave_counts = []

        # Try to find impulse waves starting from different pivots
        for start_idx in range(len(pivot_sequence.pivots) - 4):
            waves = self._try_impulse_pattern(pivot_sequence.pivots, start_idx)
            if waves:
                # Validate the pattern
                validation_results = self.validator.validate_all(waves)
                fib_scores = self.fib_analyzer.analyze_all(waves)

                # Calculate confidence
                validation_score = sum(1 for v in validation_results if v.passed) / len(validation_results) * 50
                fib_score = self.fib_analyzer.calculate_overall_score(fib_scores) * 0.5

                confidence = round(validation_score + fib_score, 2)

                wave_count = WaveCount(
                    waves=waves,
                    wave_type=WaveType.IMPULSE,
                    is_complete=len(waves) == 5,
                    validation_results=validation_results,
                    fibonacci_scores=fib_scores,
                    overall_confidence=confidence,
                    is_primary=False,
                )
                wave_counts.append(wave_count)

        # Sort by confidence and mark primary
        wave_counts.sort(key=lambda x: x.overall_confidence, reverse=True)
        if wave_counts:
            wave_counts[0].is_primary = True

        return wave_counts, pivot_sequence

    def analyze_from_pivot(
        self, candles: list[Candle], start_pivot_index: int
    ) -> tuple[list[WaveCount], PivotSequence]:
        """
        Perform wave analysis starting from a specific pivot.

        Tries multiple zigzag thresholds (from default up to 5x) to find
        both small local and large-degree patterns. Higher thresholds produce
        fewer pivots, yielding larger wave structures.

        Args:
            candles: List of OHLCV candles
            start_pivot_index: The candle index of the pivot to start from

        Returns:
            Tuple of (list of wave counts, pivot sequence at default threshold)
        """
        # Detect pivots at default threshold (always used for chart display)
        display_pivot_sequence = self.zigzag.detect_pivots(candles)

        if len(candles) < 10:
            return [], display_pivot_sequence

        # Try multiple thresholds: default, then progressively higher
        # Higher thresholds → fewer pivots → larger-degree patterns
        base_threshold = self.zigzag.threshold_percent
        thresholds = [base_threshold]
        for mult in [2.0, 3.0, 4.0, 5.0]:
            thresholds.append(base_threshold * mult)

        all_counts: list[WaveCount] = []

        for threshold in thresholds:
            if threshold == base_threshold:
                pivot_seq = display_pivot_sequence
            else:
                detector = ZigZagDetector(threshold_percent=threshold)
                pivot_seq = detector.detect_pivots(candles)

            if len(pivot_seq.pivots) < 2:
                continue

            # Find the clicked pivot (or nearest) in this pivot set
            pivot_list_index = None
            min_dist = float("inf")
            for i, pivot in enumerate(pivot_seq.pivots):
                dist = abs(pivot.index - start_pivot_index)
                if dist < min_dist:
                    min_dist = dist
                    pivot_list_index = i

            if pivot_list_index is None or min_dist > 10:
                continue

            # Scan forward from clicked pivot
            max_scan = min(pivot_list_index + 10, len(pivot_seq.pivots) - 1)
            for start_idx in range(pivot_list_index, max_scan):
                # Try complete pattern first
                waves = self._try_impulse_pattern(pivot_seq.pivots, start_idx)
                if not waves:
                    # Try partial pattern
                    waves = self._try_impulse_pattern(
                        pivot_seq.pivots, start_idx, allow_partial=True
                    )
                if waves:
                    waves = self._synthesize_wave2(waves, candles)
                    wc = self._score_waves(
                        waves,
                        is_exact=(start_idx == pivot_list_index and min_dist == 0),
                    )
                    all_counts.append(wc)

            # Also try a few pivots before (clicked pivot might be mid-pattern)
            lookback = max(0, pivot_list_index - 3)
            for start_idx in range(lookback, pivot_list_index):
                waves = self._try_impulse_pattern(pivot_seq.pivots, start_idx)
                if not waves:
                    waves = self._try_impulse_pattern(
                        pivot_seq.pivots, start_idx, allow_partial=True
                    )
                if waves:
                    waves = self._synthesize_wave2(waves, candles)
                    # Only include if clicked pivot is part of this pattern
                    wave_indices = set()
                    for w in waves:
                        wave_indices.add(w.start_index)
                        wave_indices.add(w.end_index)
                    if start_pivot_index not in wave_indices:
                        continue
                    wc = self._score_waves(waves, is_exact=False)
                    all_counts.append(wc)

        # Sort by confidence, then by completeness and wave count for tie-breaking
        all_counts.sort(
            key=lambda x: (x.overall_confidence, x.is_complete, len(x.waves)),
            reverse=True,
        )
        if all_counts:
            all_counts[0].is_primary = True

        return all_counts, display_pivot_sequence

    def _score_waves(self, waves: list[Wave], is_exact: bool = False) -> WaveCount:
        """Score a set of waves and return a WaveCount."""
        validation_results = self.validator.validate_all(waves)
        fib_scores = self.fib_analyzer.analyze_all(waves)

        validation_score = (
            sum(1 for v in validation_results if v.passed)
            / max(len(validation_results), 1)
            * 50
        )
        fib_score = self.fib_analyzer.calculate_overall_score(fib_scores) * 0.5

        # Strong bonus for starting exactly at the clicked pivot
        proximity_bonus = 40.0 if is_exact else 0.0

        # Bonus for more waves (complete patterns strongly preferred)
        wave_bonus = len(waves) * 2.0

        # Strong bonus for complete 5-wave patterns
        completeness_bonus = 15.0 if len(waves) == 5 else 0.0

        # Modest bonus for patterns that cover more price range
        all_prices = []
        for w in waves:
            all_prices.extend([w.start_price, w.end_price])
        price_range = max(all_prices) - min(all_prices)
        avg_price = sum(all_prices) / len(all_prices) if all_prices else 1
        range_pct = (price_range / avg_price * 100) if avg_price > 0 else 0
        range_bonus = min(range_pct, 10.0)

        confidence = round(min(
            validation_score + fib_score + proximity_bonus + wave_bonus + completeness_bonus + range_bonus,
            100.0,
        ), 2)

        return WaveCount(
            waves=waves,
            wave_type=WaveType.IMPULSE,
            is_complete=len(waves) == 5,
            validation_results=validation_results,
            fibonacci_scores=fib_scores,
            overall_confidence=confidence,
            is_primary=False,
        )

    def build_manual_wave_count(
        self, pivot_indices: list[int], candles: list[Candle]
    ) -> WaveCount | None:
        """
        Build a wave count from manually selected pivot indices.

        Users click on pivots in order to define their own wave structure.
        This method creates waves from those pivots and validates them.

        Args:
            pivot_indices: List of candle indices where pivots are located.
                           Must be in chronological order. Minimum 2 pivots.
            candles: List of OHLCV candles.

        Returns:
            WaveCount if valid pattern created, None if insufficient pivots.
        """
        if len(pivot_indices) < 2 or not candles:
            return None

        # Build pivots from the provided indices
        pivots: list[Pivot] = []
        for i, idx in enumerate(pivot_indices):
            if idx < 0 or idx >= len(candles):
                continue
            candle = candles[idx]
            # Determine if this is a high or low pivot
            # For odd positions (0, 2, 4): depends on trend direction
            # First, determine trend from first two points
            if len(pivots) == 0:
                # First pivot - determine type based on second point
                if len(pivot_indices) > 1:
                    next_idx = pivot_indices[1]
                    if next_idx < len(candles):
                        next_candle = candles[next_idx]
                        # If next is higher, first is low; if lower, first is high
                        if next_candle.close > candle.close:
                            pivot_type = PivotType.LOW
                            price = candle.low
                        else:
                            pivot_type = PivotType.HIGH
                            price = candle.high
                    else:
                        pivot_type = PivotType.LOW
                        price = candle.low
                else:
                    pivot_type = PivotType.LOW
                    price = candle.low
            else:
                # Alternate pivot types
                prev_type = pivots[-1].type
                if prev_type == PivotType.LOW:
                    pivot_type = PivotType.HIGH
                    price = candle.high
                else:
                    pivot_type = PivotType.LOW
                    price = candle.low

            pivots.append(Pivot(
                timestamp=candle.timestamp,
                price=price,
                type=pivot_type,
                index=idx,
                significance=0.0,
            ))

        if len(pivots) < 2:
            return None

        # Create waves from consecutive pivots
        waves: list[Wave] = []
        wave_defs = [
            (WaveLabel.W1, WaveType.IMPULSE),
            (WaveLabel.W2, WaveType.CORRECTIVE),
            (WaveLabel.W3, WaveType.IMPULSE),
            (WaveLabel.W4, WaveType.CORRECTIVE),
            (WaveLabel.W5, WaveType.IMPULSE),
        ]

        for i in range(min(len(pivots) - 1, 5)):
            label, wtype = wave_defs[i]
            waves.append(
                Wave(
                    label=label,
                    type=wtype,
                    start_timestamp=pivots[i].timestamp,
                    end_timestamp=pivots[i + 1].timestamp,
                    start_price=pivots[i].price,
                    end_price=pivots[i + 1].price,
                    start_index=pivots[i].index,
                    end_index=pivots[i + 1].index,
                )
            )

        if not waves:
            return None

        # Score the waves
        return self._score_waves(waves, is_exact=True)

    def _synthesize_wave2(
        self, waves: list[Wave], candles: list[Candle],
    ) -> list[Wave]:
        """
        If only W1 exists, synthesize W2 from the extreme price after W1.
        Ensures W2 is always drawn to the current extreme point.
        """
        if len(waves) != 1:
            return waves

        w1 = waves[0]
        is_uptrend = w1.end_price > w1.start_price

        search_start = w1.end_index + 1
        if search_start >= len(candles):
            return waves

        extreme_price = None
        extreme_idx = None

        for i in range(search_start, len(candles)):
            c = candles[i]
            price = c.low if is_uptrend else c.high
            if extreme_price is None or (
                (is_uptrend and price < extreme_price)
                or (not is_uptrend and price > extreme_price)
            ):
                extreme_price = price
                extreme_idx = i

        if extreme_price is None or extreme_idx is None:
            return waves

        w2 = Wave(
            label=WaveLabel.W2,
            type=WaveType.CORRECTIVE,
            start_timestamp=w1.end_timestamp,
            end_timestamp=candles[extreme_idx].timestamp,
            start_price=w1.end_price,
            end_price=extreme_price,
            start_index=w1.end_index,
            end_index=extreme_idx,
        )
        return [w1, w2]

    def _try_impulse_pattern(
        self, pivots: list[Pivot], start_idx: int, allow_partial: bool = False,
    ) -> list[Wave] | None:
        """
        Try to identify an impulse pattern starting from a given pivot.

        Args:
            pivots: Full pivot sequence
            start_idx: Starting index in the pivot list
            allow_partial: If True, return partial patterns (2+ pivots)

        Returns:
            List of waves if pattern found, None otherwise
        """
        available = len(pivots) - start_idx
        min_needed = 2 if allow_partial else 5

        if available < min_needed:
            return None

        # Get as many consecutive pivots as available (up to 6 for full pattern)
        p = pivots[start_idx : start_idx + 6]

        if len(p) < min_needed:
            return None

        # Validate minimum candle distance between consecutive pivots
        for j in range(len(p) - 1):
            if abs(p[j + 1].index - p[j].index) < self.min_wave_candles:
                if not allow_partial:
                    return None
                # For partial: truncate at the failing pair
                p = p[: j + 1]
                break

        if len(p) < 2:
            return None

        # Determine trend direction from first move
        is_uptrend = p[1].price > p[0].price

        # Validate alternating pivot types for as many pivots as we have
        if is_uptrend:
            expected_types = [PivotType.LOW, PivotType.HIGH, PivotType.LOW,
                              PivotType.HIGH, PivotType.LOW, PivotType.HIGH]
        else:
            expected_types = [PivotType.HIGH, PivotType.LOW, PivotType.HIGH,
                              PivotType.LOW, PivotType.HIGH, PivotType.LOW]

        for j in range(len(p)):
            if p[j].type != expected_types[j]:
                if not allow_partial:
                    return None
                # Truncate at the mismatch
                p = p[:j]
                break

        if len(p) < 2:
            return None

        # For complete patterns, ensure we have at least 5 pivots
        if not allow_partial and len(p) < 5:
            return None

        waves = []
        wave_defs = [
            (WaveLabel.W1, WaveType.IMPULSE),
            (WaveLabel.W2, WaveType.CORRECTIVE),
            (WaveLabel.W3, WaveType.IMPULSE),
            (WaveLabel.W4, WaveType.CORRECTIVE),
            (WaveLabel.W5, WaveType.IMPULSE),
        ]

        for i in range(min(len(p) - 1, 5)):
            label, wtype = wave_defs[i]
            waves.append(
                Wave(
                    label=label,
                    type=wtype,
                    start_timestamp=p[i].timestamp,
                    end_timestamp=p[i + 1].timestamp,
                    start_price=p[i].price,
                    end_price=p[i + 1].price,
                    start_index=p[i].index,
                    end_index=p[i + 1].index,
                )
            )

        return waves if waves else None

    def _extrapolate_timestamp(
        self, candles: list[Candle], base_index: int, offset_candles: float
    ) -> datetime:
        """
        Extrapolate a timestamp for a projected index that may be beyond the candle data.
        Uses average candle interval to project into the future.
        """
        if not candles:
            return datetime.utcnow()

        target_index = base_index + offset_candles

        # If within data range, interpolate
        if target_index < len(candles):
            idx = int(target_index)
            idx = max(0, min(idx, len(candles) - 1))
            return candles[idx].timestamp

        # Calculate average interval from recent candles
        recent = candles[-min(20, len(candles)):]
        if len(recent) < 2:
            return candles[-1].timestamp

        total_seconds = (recent[-1].timestamp - recent[0].timestamp).total_seconds()
        avg_interval = total_seconds / (len(recent) - 1)

        # Extrapolate beyond last candle
        candles_beyond = target_index - (len(candles) - 1)
        extra_seconds = avg_interval * candles_beyond
        return candles[-1].timestamp + timedelta(seconds=extra_seconds)

    def _build_higher_degree(
        self, wave_count: WaveCount, candles: list[Candle]
    ) -> HigherDegreeAnalysis | None:
        """
        Build higher-degree wave structure from a complete 5-wave impulse.
        Returns (I) wave with projected (II) and (III) zones.
        """
        if not wave_count.is_complete or len(wave_count.waves) < 5:
            return None

        waves = {w.label: w for w in wave_count.waves}
        w1 = waves.get(WaveLabel.W1)
        w5 = waves.get(WaveLabel.W5)

        if not w1 or not w5:
            return None

        is_uptrend = w1.end_price > w1.start_price
        direction = "up" if is_uptrend else "down"

        # Welle (I): entire impulse from W1 start to W5 end
        wave_i = HigherDegreeWave(
            label=HigherDegreeLabel.I,
            start_timestamp=w1.start_timestamp,
            end_timestamp=w5.end_timestamp,
            start_price=w1.start_price,
            end_price=w5.end_price,
            start_index=w1.start_index,
            end_index=w5.end_index,
        )

        wave_i_length = abs(w5.end_price - w1.start_price)
        wave_i_duration = w5.end_index - w1.start_index  # in candles

        projected_zones: list[ProjectedZone] = []

        # (II) Correction Zone: 50-61.8% retracement of (I)
        # Fibonacci time: (II) ends between 0.236–0.786 × (I) duration after (I) end
        ii_start_bar = float(w5.end_index) + wave_i_duration * 0.236
        ii_end_bar = float(w5.end_index) + wave_i_duration * 0.786
        ii_end_bar = max(ii_end_bar, ii_start_bar + 3)

        ii_time_start = self._extrapolate_timestamp(candles, w5.end_index, wave_i_duration * 0.236)
        ii_time_end = self._extrapolate_timestamp(candles, w5.end_index, wave_i_duration * 0.786)

        if is_uptrend:
            ii_price_top = w5.end_price - wave_i_length * 0.50
            ii_price_bottom = w5.end_price - wave_i_length * 0.618
        else:
            ii_price_bottom = w5.end_price + wave_i_length * 0.50
            ii_price_top = w5.end_price + wave_i_length * 0.618

        projected_zones.append(ProjectedZone(
            label="(II) Korrektur",
            price_top=round(max(ii_price_top, ii_price_bottom), 2),
            price_bottom=round(min(ii_price_top, ii_price_bottom), 2),
            time_start=ii_time_start,
            time_end=ii_time_end,
            start_bar_index=ii_start_bar,
            end_bar_index=ii_end_bar,
            zone_type="correction",
            zone_style="correction",
        ))

        # (III) Target Zone: 100-161.8% extension from (I)
        # Fibonacci time: (III) ends between 0.618–2.0 × (I) duration after (II) midpoint
        # Estimate (II) end at midpoint of 0.236–0.786 range ≈ 0.5 × (I) duration
        ii_mid_bar = float(w5.end_index) + wave_i_duration * 0.5
        iii_start_bar = ii_mid_bar + wave_i_duration * 0.618
        iii_end_bar = ii_mid_bar + wave_i_duration * 2.0
        iii_end_bar = max(iii_end_bar, iii_start_bar + 3)

        iii_offset_start = wave_i_duration * 0.5 + wave_i_duration * 0.618
        iii_offset_end = wave_i_duration * 0.5 + wave_i_duration * 2.0
        iii_time_start = self._extrapolate_timestamp(candles, w5.end_index, iii_offset_start)
        iii_time_end = self._extrapolate_timestamp(candles, w5.end_index, iii_offset_end)

        # (II) midpoint price for projection base
        ii_mid_price = (ii_price_top + ii_price_bottom) / 2

        if is_uptrend:
            iii_price_bottom = ii_mid_price + wave_i_length * 1.0
            iii_price_top = ii_mid_price + wave_i_length * 1.618
        else:
            iii_price_top = ii_mid_price - wave_i_length * 1.0
            iii_price_bottom = ii_mid_price - wave_i_length * 1.618

        projected_zones.append(ProjectedZone(
            label="(III) Ziel",
            price_top=round(max(iii_price_top, iii_price_bottom), 2),
            price_bottom=round(min(iii_price_top, iii_price_bottom), 2),
            time_start=iii_time_start,
            time_end=iii_time_end,
            start_bar_index=iii_start_bar,
            end_bar_index=iii_end_bar,
            zone_type="target",
            zone_style="target",
        ))

        return HigherDegreeAnalysis(
            completed_wave=wave_i,
            projected_zones=projected_zones,
            direction=direction,
        )

    def _synthetic_wave_from_zone(
        self, zone: ProjectedZone, label: WaveLabel, wave_type: WaveType,
        start_price: float, start_index: int, start_timestamp: datetime,
    ) -> Wave:
        """Create a synthetic Wave using the midpoint of a projected zone.
        Used for cascading projections when intermediate waves are not yet identified."""
        mid_price = (zone.price_top + zone.price_bottom) / 2
        mid_bar = int((zone.start_bar_index + zone.end_bar_index) / 2)
        mid_time = zone.time_start + (zone.time_end - zone.time_start) / 2
        return Wave(
            label=label,
            type=wave_type,
            start_timestamp=start_timestamp,
            end_timestamp=mid_time,
            start_price=start_price,
            end_price=mid_price,
            start_index=start_index,
            end_index=mid_bar,
        )

    def calculate_projected_zones(
        self,
        wave_count: WaveCount,
        candles: list[Candle],
    ) -> list[ProjectedZone]:
        """
        Calculate projected zones based on the last wave in the count.

        The last wave is always considered "in progress", so we show:
        1. The target/correction zone for the currently running wave
        2. The next zone after that

        This ensures the user always sees where the current wave might
        end and what comes next.
        """
        if not wave_count.waves or not candles:
            return []

        waves = {w.label: w for w in wave_count.waves}
        w1 = waves.get(WaveLabel.W1)
        w2 = waves.get(WaveLabel.W2)
        w3 = waves.get(WaveLabel.W3)
        w4 = waves.get(WaveLabel.W4)
        w5 = waves.get(WaveLabel.W5)

        if not w1:
            return []

        is_uptrend = w1.end_price > w1.start_price
        zones: list[ProjectedZone] = []

        # Determine the last wave in the count
        last_wave = wave_count.waves[-1]
        last_label = last_wave.label

        if last_label == WaveLabel.W1:
            # W1 is the last wave → show W2 correction + W3 target
            w2_zone = self._zone_golden_pocket(w1, candles, is_uptrend)
            zones.append(w2_zone)
            est_w2 = self._synthetic_wave_from_zone(
                w2_zone, WaveLabel.W2, WaveType.CORRECTIVE,
                w1.end_price, w1.end_index, w1.end_timestamp,
            )
            zones.append(self._zone_w3_target(w1, est_w2, candles, is_uptrend))

        elif last_label == WaveLabel.W2:
            # W2 is the last wave → show W2 correction + W3 target
            w2_zone = self._zone_golden_pocket(w1, candles, is_uptrend)
            zones.append(w2_zone)
            zones.append(self._zone_w3_target(w1, w2, candles, is_uptrend))

        elif last_label == WaveLabel.W3:
            # W3 is the last wave → W3 still running
            # Show W3 target + W4 correction
            zones.append(self._zone_w3_target(w1, w2, candles, is_uptrend))
            zones.append(self._zone_w4_correction(w1, w3, candles, is_uptrend))

        elif last_label == WaveLabel.W4:
            # W4 is the last wave → show W4 correction + W5 target
            w4_zone = self._zone_w4_correction(w1, w3, candles, is_uptrend)
            zones.append(w4_zone)
            zones.append(self._zone_w5_target(w1, w3, w4, candles, is_uptrend))

        elif last_label == WaveLabel.W5:
            # W5 is the last wave → W5 still running
            # Show W5 target + (II) correction (from higher degree)
            zones.append(self._zone_w5_target(w1, w3, w4, candles, is_uptrend))
            # (II)/(III) zones are merged from _build_higher_degree at API level

        return zones

    def calculate_fibonacci_levels(
        self,
        wave_count: WaveCount,
        candles: list[Candle],
    ) -> list[FibonacciLevel]:
        """
        Calculate Fibonacci retracement and extension price levels
        to be drawn as subtle horizontal dashed lines on the chart.
        Levels are context-dependent based on which waves are identified.
        """
        if not wave_count.waves or not candles:
            return []

        waves = {w.label: w for w in wave_count.waves}
        w1 = waves.get(WaveLabel.W1)
        w2 = waves.get(WaveLabel.W2)
        w3 = waves.get(WaveLabel.W3)
        w4 = waves.get(WaveLabel.W4)
        w5 = waves.get(WaveLabel.W5)

        if not w1:
            return []

        is_uptrend = w1.end_price > w1.start_price
        w1_len = abs(w1.end_price - w1.start_price)
        levels: list[FibonacciLevel] = []

        # Determine the last wave to decide which levels to show
        last_label = wave_count.waves[-1].label

        if last_label in (WaveLabel.W1, WaveLabel.W2):
            # W1 or W2 is last: show W1 retracements + W3 extensions from W2
            for ratio in [0.236, 0.382, 0.5, 0.618, 0.786]:
                if is_uptrend:
                    price = w1.end_price - w1_len * ratio
                else:
                    price = w1.end_price + w1_len * ratio
                levels.append(FibonacciLevel(
                    price=round(price, 2), ratio=ratio, label=str(ratio),
                    style="retracement", context="correction",
                    ref_timestamp=w1.end_timestamp,
                    ref_bar_index=float(w1.end_index),
                ))
            if w2:
                for ratio in [1.0, 1.272, 1.618, 2.618]:
                    if is_uptrend:
                        price = w2.end_price + w1_len * ratio
                    else:
                        price = w2.end_price - w1_len * ratio
                    levels.append(FibonacciLevel(
                        price=round(price, 2), ratio=ratio, label=str(ratio),
                        style="extension", context="target",
                        ref_timestamp=w2.end_timestamp,
                        ref_bar_index=float(w2.end_index),
                    ))

        elif last_label == WaveLabel.W3:
            # W3 is last (still running): show W3 extensions + W3 retracements
            # Extensions from W2 (W3 targets)
            if w2:
                for ratio in [1.0, 1.272, 1.618, 2.618]:
                    if is_uptrend:
                        price = w2.end_price + w1_len * ratio
                    else:
                        price = w2.end_price - w1_len * ratio
                    levels.append(FibonacciLevel(
                        price=round(price, 2), ratio=ratio, label=str(ratio),
                        style="extension", context="target",
                        ref_timestamp=w2.end_timestamp,
                        ref_bar_index=float(w2.end_index),
                    ))
            # Retracements of W3 (W4 correction targets)
            w3_len = abs(w3.end_price - w3.start_price)
            for ratio in [0.236, 0.382, 0.5, 0.618]:
                if is_uptrend:
                    price = w3.end_price - w3_len * ratio
                else:
                    price = w3.end_price + w3_len * ratio
                levels.append(FibonacciLevel(
                    price=round(price, 2), ratio=ratio, label=str(ratio),
                    style="retracement", context="correction",
                    ref_timestamp=w3.end_timestamp,
                    ref_bar_index=float(w3.end_index),
                ))

        elif last_label == WaveLabel.W4:
            # W4 is last: show W3-based extensions from W4 (W5 targets)
            w3_ext_len = abs(w3.end_price - w3.start_price) if w3 else w1_len
            for ratio in [0.382, 0.5, 0.618, 1.0]:
                if is_uptrend:
                    price = w4.end_price + w3_ext_len * ratio
                else:
                    price = w4.end_price - w3_ext_len * ratio
                levels.append(FibonacciLevel(
                    price=round(price, 2), ratio=ratio, label=str(ratio),
                    style="extension", context="target",
                    ref_timestamp=w4.end_timestamp,
                    ref_bar_index=float(w4.end_index),
                ))

        elif last_label == WaveLabel.W5:
            # W5 is last (still running): show W3-based extensions + impulse retracements
            # Extensions from W4 (W5 targets based on W3 length)
            if w4:
                w3_ext_len = abs(w3.end_price - w3.start_price) if w3 else w1_len
                for ratio in [0.382, 0.5, 0.618, 1.0]:
                    if is_uptrend:
                        price = w4.end_price + w3_ext_len * ratio
                    else:
                        price = w4.end_price - w3_ext_len * ratio
                    levels.append(FibonacciLevel(
                        price=round(price, 2), ratio=ratio, label=str(ratio),
                        style="extension", context="target",
                        ref_timestamp=w4.end_timestamp,
                        ref_bar_index=float(w4.end_index),
                    ))
            # Full impulse retracements (for (II) correction)
            impulse_len = abs(w5.end_price - w1.start_price)
            for ratio in [0.236, 0.382, 0.5, 0.618, 0.786]:
                if is_uptrend:
                    price = w5.end_price - impulse_len * ratio
                else:
                    price = w5.end_price + impulse_len * ratio
                levels.append(FibonacciLevel(
                    price=round(price, 2), ratio=ratio, label=str(ratio),
                    style="retracement", context="correction",
                    ref_timestamp=w5.end_timestamp,
                    ref_bar_index=float(w5.end_index),
                ))
            # Extensions for (III) target
            for ratio in [1.0, 1.618, 2.618]:
                if is_uptrend:
                    price = w5.end_price - impulse_len * 0.55 + impulse_len * ratio
                else:
                    price = w5.end_price + impulse_len * 0.55 - impulse_len * ratio
                levels.append(FibonacciLevel(
                    price=round(price, 2), ratio=ratio, label=str(ratio),
                    style="extension", context="target",
                    ref_timestamp=w5.end_timestamp,
                    ref_bar_index=float(w5.end_index),
                ))

        return levels

    def _zone_golden_pocket(
        self, w1: Wave, candles: list[Candle], is_uptrend: bool
    ) -> ProjectedZone:
        """W2 correction zone (50%-78.6% retracement of W1).
        Time: W2 typically ends between 0.382 and 0.618 × W1 duration after W1 end."""
        w1_len = abs(w1.end_price - w1.start_price)
        w1_dur = w1.end_index - w1.start_index

        if is_uptrend:
            price_a = w1.end_price - w1_len * 0.786
            price_b = w1.end_price - w1_len * 0.50
        else:
            price_a = w1.end_price + w1_len * 0.786
            price_b = w1.end_price + w1_len * 0.50

        # Fibonacci time: W2 ends at 0.382–0.618 × W1 duration from W1 end
        start_bar = float(w1.end_index) + w1_dur * 0.382
        end_bar = float(w1.end_index) + w1_dur * 0.618
        end_bar = max(end_bar, start_bar + 3)  # minimum 3 bars width
        time_start = self._extrapolate_timestamp(candles, w1.end_index, w1_dur * 0.382)
        time_end = self._extrapolate_timestamp(candles, w1.end_index, w1_dur * 0.618)

        return ProjectedZone(
            label="W2 Korrektur",
            price_top=round(max(price_a, price_b), 2),
            price_bottom=round(min(price_a, price_b), 2),
            time_start=time_start,
            time_end=time_end,
            start_bar_index=start_bar,
            end_bar_index=end_bar,
            zone_type="correction",
            zone_style="correction",
        )

    def _zone_w3_target(
        self, w1: Wave, w2: Wave, candles: list[Candle], is_uptrend: bool
    ) -> ProjectedZone:
        """W3 target zone: 100%-161.8% of W1 length projected from W2 end.
        Time: W3 typically reaches target at 1.0–1.618 × W1 duration from W2 end."""
        w1_len = abs(w1.end_price - w1.start_price)
        w1_dur = w1.end_index - w1.start_index

        if is_uptrend:
            price_a = w2.end_price + w1_len * 1.0
            price_b = w2.end_price + w1_len * 1.618
        else:
            price_a = w2.end_price - w1_len * 1.0
            price_b = w2.end_price - w1_len * 1.618

        # Fibonacci time: W3 reaches target at 1.0–1.618 × W1 duration from W2 end
        start_bar = float(w2.end_index) + w1_dur * 1.0
        end_bar = float(w2.end_index) + w1_dur * 1.618
        end_bar = max(end_bar, start_bar + 3)
        time_start = self._extrapolate_timestamp(candles, w2.end_index, w1_dur * 1.0)
        time_end = self._extrapolate_timestamp(candles, w2.end_index, w1_dur * 1.618)

        return ProjectedZone(
            label="W3 Ziel",
            price_top=round(max(price_a, price_b), 2),
            price_bottom=round(min(price_a, price_b), 2),
            time_start=time_start,
            time_end=time_end,
            start_bar_index=start_bar,
            end_bar_index=end_bar,
            zone_type="target",
            zone_style="target",
        )

    def _zone_w4_correction(
        self, w1: Wave, w3: Wave, candles: list[Candle], is_uptrend: bool
    ) -> ProjectedZone:
        """W4 correction zone: 23.6%-38.2% retracement of W3, constrained by W1 end.
        Time: W4 typically ends between 0.382–0.618 × W1 duration after W3 end
        (alternation principle: if W2 was short/sharp, W4 is longer/complex)."""
        w3_len = abs(w3.end_price - w3.start_price)
        w1_dur = w1.end_index - w1.start_index

        if is_uptrend:
            price_a = w3.end_price - w3_len * 0.382
            price_b = w3.end_price - w3_len * 0.236
            # Constraint: W4 must not go below W1 end price
            price_a = max(price_a, w1.end_price)
        else:
            price_a = w3.end_price + w3_len * 0.382
            price_b = w3.end_price + w3_len * 0.236
            # Constraint: W4 must not go above W1 end price
            price_a = min(price_a, w1.end_price)

        # Fibonacci time: W4 ends at 0.382–0.618 × W1 duration from W3 end
        start_bar = float(w3.end_index) + w1_dur * 0.382
        end_bar = float(w3.end_index) + w1_dur * 0.618
        end_bar = max(end_bar, start_bar + 3)
        time_start = self._extrapolate_timestamp(candles, w3.end_index, w1_dur * 0.382)
        time_end = self._extrapolate_timestamp(candles, w3.end_index, w1_dur * 0.618)

        return ProjectedZone(
            label="W4 Korrektur",
            price_top=round(max(price_a, price_b), 2),
            price_bottom=round(min(price_a, price_b), 2),
            time_start=time_start,
            time_end=time_end,
            start_bar_index=start_bar,
            end_bar_index=end_bar,
            zone_type="correction",
            zone_style="correction",
        )

    def _zone_w5_target(
        self, w1: Wave, w3: Wave, w4: Wave, candles: list[Candle], is_uptrend: bool
    ) -> ProjectedZone:
        """W5 target zone: Fibonacci extension of W3 length projected from W4 end.
        Uses 0.382–0.618 × W3 length as the target range.
        Time: W5 ≈ W1 duration (equality principle). Range: 0.382–1.272 × W1 duration."""
        w3_len = abs(w3.end_price - w3.start_price)
        w1_dur = w1.end_index - w1.start_index

        if is_uptrend:
            price_a = w4.end_price + w3_len * 0.382
            price_b = w4.end_price + w3_len * 0.618
        else:
            price_a = w4.end_price - w3_len * 0.382
            price_b = w4.end_price - w3_len * 0.618

        # Fibonacci time: W5 end = W4.end + (0.382–1.272) × W1 duration
        start_bar = float(w4.end_index) + w1_dur * 0.382
        end_bar = float(w4.end_index) + w1_dur * 1.272
        end_bar = max(end_bar, start_bar + 3)
        time_start = self._extrapolate_timestamp(candles, w4.end_index, w1_dur * 0.382)
        time_end = self._extrapolate_timestamp(candles, w4.end_index, w1_dur * 1.272)

        return ProjectedZone(
            label="W5 Ziel",
            price_top=round(max(price_a, price_b), 2),
            price_bottom=round(min(price_a, price_b), 2),
            time_start=time_start,
            time_end=time_end,
            start_bar_index=start_bar,
            end_bar_index=end_bar,
            zone_type="target",
            zone_style="target",
        )

    def calculate_risk_reward(
        self,
        wave_count: WaveCount,
        current_price: float,
        candles: list[Candle] | None = None,
        projected_zones: list[ProjectedZone] | None = None,
    ) -> RiskReward | None:
        """
        Calculate risk/reward levels based on the wave count.
        R:R is computed against the next projected target zone.
        Returns None for complete patterns (no active trade setup).
        """
        if not wave_count.waves:
            return None

        # No R:R for complete 5-wave patterns — trade is done
        if wave_count.is_complete:
            return None

        waves = {w.label: w for w in wave_count.waves}
        w1 = waves.get(WaveLabel.W1)
        w2 = waves.get(WaveLabel.W2)
        w4 = waves.get(WaveLabel.W4)
        w5 = waves.get(WaveLabel.W5)

        if not w1:
            return None

        is_uptrend = w1.end_price > w1.start_price
        w1_duration = w1.end_index - w1.start_index

        if is_uptrend:
            if w4:
                entry_price = w4.end_price
                stop_loss = w1.end_price * 0.99
            elif w2:
                entry_price = w2.end_price
                stop_loss = w1.start_price * 0.99
            else:
                entry_price = current_price
                stop_loss = w1.start_price * 0.99
        else:
            if w4:
                entry_price = w4.end_price
                stop_loss = w1.end_price * 1.01
            elif w2:
                entry_price = w2.end_price
                stop_loss = w1.start_price * 1.01
            else:
                entry_price = current_price
                stop_loss = w1.start_price * 1.01

        risk = abs(entry_price - stop_loss)

        # Find nearest target zone for R:R calculation
        reward = risk  # default 1:1 if no target zone found
        if projected_zones:
            for z in projected_zones:
                if z.zone_style == "target":
                    mid_target = (z.price_top + z.price_bottom) / 2
                    reward = abs(mid_target - entry_price)
                    break

        rr_ratio = reward / risk if risk > 0 else 0

        # Time projections
        time_start = None
        stop_time_end = None

        if candles and w1_duration > 0:
            if w5:
                base_index = w5.end_index
                time_start = w5.end_timestamp
            elif w4:
                base_index = w4.end_index
                time_start = w4.end_timestamp
            elif w2:
                base_index = w2.end_index
                time_start = w2.end_timestamp
            else:
                base_index = w1.end_index
                time_start = w1.end_timestamp

            stop_time_end = self._extrapolate_timestamp(
                candles, base_index, w1_duration * 0.382
            )

        return RiskReward(
            entry_price=round(entry_price, 2),
            stop_loss=round(stop_loss, 2),
            risk_reward_ratio=round(rr_ratio, 2),
            time_start=time_start,
            stop_time_end=stop_time_end,
        )
