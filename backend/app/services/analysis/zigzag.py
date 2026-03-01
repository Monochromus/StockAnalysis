from app.schemas import Candle, Pivot, PivotType, PivotSequence


class ZigZagDetector:
    """
    Detects significant swing highs and lows using a percentage threshold.
    """

    def __init__(self, threshold_percent: float = 5.0):
        """
        Initialize the ZigZag detector.

        Args:
            threshold_percent: Minimum percentage move to register a new pivot (default 5%)
        """
        self.threshold_percent = threshold_percent

    def detect_pivots(self, candles: list[Candle]) -> PivotSequence:
        """
        Detect pivot points (swing highs and lows) in the candle data.

        Args:
            candles: List of OHLCV candles

        Returns:
            PivotSequence containing detected pivots
        """
        if len(candles) < 3:
            return PivotSequence(
                pivots=[],
                threshold_percent=self.threshold_percent,
                total_candles=len(candles),
            )

        pivots: list[Pivot] = []
        threshold = self.threshold_percent / 100

        # Find initial direction
        first_high_idx = 0
        first_low_idx = 0
        first_high = candles[0].high
        first_low = candles[0].low

        # Scan first few bars to establish initial high and low
        for i, candle in enumerate(candles[:min(10, len(candles))]):
            if candle.high > first_high:
                first_high = candle.high
                first_high_idx = i
            if candle.low < first_low:
                first_low = candle.low
                first_low_idx = i

        # Determine initial direction based on which extreme came first
        if first_high_idx < first_low_idx:
            # Started with a high, looking for lows first
            last_pivot_type = PivotType.HIGH
            last_pivot_price = first_high
            last_pivot_idx = first_high_idx
        else:
            # Started with a low, looking for highs first
            last_pivot_type = PivotType.LOW
            last_pivot_price = first_low
            last_pivot_idx = first_low_idx

        # Track potential pivot
        potential_pivot_price = last_pivot_price
        potential_pivot_idx = last_pivot_idx

        for i, candle in enumerate(candles):
            if last_pivot_type == PivotType.HIGH:
                # Looking for a low
                if candle.low < potential_pivot_price:
                    potential_pivot_price = candle.low
                    potential_pivot_idx = i

                # Check if we've moved enough to confirm the low and start looking for high
                if candle.high > potential_pivot_price * (1 + threshold):
                    # Confirm the low pivot
                    pivots.append(
                        Pivot(
                            timestamp=candles[potential_pivot_idx].timestamp,
                            price=potential_pivot_price,
                            type=PivotType.LOW,
                            index=potential_pivot_idx,
                            significance=self._calculate_significance(
                                last_pivot_price, potential_pivot_price
                            ),
                        )
                    )
                    last_pivot_type = PivotType.LOW
                    last_pivot_price = potential_pivot_price
                    last_pivot_idx = potential_pivot_idx
                    potential_pivot_price = candle.high
                    potential_pivot_idx = i

            else:  # last_pivot_type == PivotType.LOW
                # Looking for a high
                if candle.high > potential_pivot_price:
                    potential_pivot_price = candle.high
                    potential_pivot_idx = i

                # Check if we've moved enough to confirm the high and start looking for low
                if candle.low < potential_pivot_price * (1 - threshold):
                    # Confirm the high pivot
                    pivots.append(
                        Pivot(
                            timestamp=candles[potential_pivot_idx].timestamp,
                            price=potential_pivot_price,
                            type=PivotType.HIGH,
                            index=potential_pivot_idx,
                            significance=self._calculate_significance(
                                last_pivot_price, potential_pivot_price
                            ),
                        )
                    )
                    last_pivot_type = PivotType.HIGH
                    last_pivot_price = potential_pivot_price
                    last_pivot_idx = potential_pivot_idx
                    potential_pivot_price = candle.low
                    potential_pivot_idx = i

        # Add the last potential pivot if significant
        if potential_pivot_idx != last_pivot_idx:
            change = abs(potential_pivot_price - last_pivot_price) / last_pivot_price
            if change >= threshold * 0.5:  # Slightly relaxed for final pivot
                final_type = PivotType.LOW if last_pivot_type == PivotType.HIGH else PivotType.HIGH
                pivots.append(
                    Pivot(
                        timestamp=candles[potential_pivot_idx].timestamp,
                        price=potential_pivot_price,
                        type=final_type,
                        index=potential_pivot_idx,
                        significance=self._calculate_significance(
                            last_pivot_price, potential_pivot_price
                        ),
                    )
                )

        return PivotSequence(
            pivots=pivots,
            threshold_percent=self.threshold_percent,
            total_candles=len(candles),
        )

    def _calculate_significance(self, prev_price: float, curr_price: float) -> float:
        """Calculate the significance of a pivot based on price change."""
        if prev_price == 0:
            return 0.0
        return abs(curr_price - prev_price) / prev_price * 100
