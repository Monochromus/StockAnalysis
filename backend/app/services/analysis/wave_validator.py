from app.schemas import Wave, WaveLabel, ValidationResult
from app.utils.math_helpers import calculate_retracement, wave_length


class WaveValidator:
    """
    Validates Elliott Wave patterns against the three cardinal rules.
    """

    def validate_all(self, waves: list[Wave]) -> list[ValidationResult]:
        """
        Run all validation rules on the wave sequence.

        Args:
            waves: List of waves forming an impulse pattern

        Returns:
            List of ValidationResult for each rule
        """
        results = []

        # Only validate if we have enough waves
        wave_dict = {w.label: w for w in waves}

        results.append(self._validate_rule1_wave2_retracement(wave_dict))
        results.append(self._validate_rule2_wave3_not_shortest(wave_dict))
        results.append(self._validate_rule3_wave4_no_overlap(wave_dict))

        return results

    def _validate_rule1_wave2_retracement(self, waves: dict[WaveLabel, Wave]) -> ValidationResult:
        """
        Rule 1: Wave 2 cannot retrace more than 100% of Wave 1.
        Wave 2 must not go below the start of Wave 1.
        """
        rule_name = "Rule 1: Wave 2 Retracement"
        rule_desc = "Wave 2 cannot retrace more than 100% of Wave 1"

        w1 = waves.get(WaveLabel.W1)
        w2 = waves.get(WaveLabel.W2)

        if not w1 or not w2:
            return ValidationResult(
                rule_name=rule_name,
                rule_description=rule_desc,
                passed=True,
                details="Insufficient waves to validate",
            )

        # Calculate retracement of Wave 2
        retracement = calculate_retracement(w1.start_price, w1.end_price, w2.end_price)

        passed = retracement <= 1.0

        return ValidationResult(
            rule_name=rule_name,
            rule_description=rule_desc,
            passed=passed,
            details=f"Wave 2 retraced {retracement*100:.1f}% of Wave 1" +
                    (" (valid)" if passed else " (VIOLATION: >100%)"),
        )

    def _validate_rule2_wave3_not_shortest(self, waves: dict[WaveLabel, Wave]) -> ValidationResult:
        """
        Rule 2: Wave 3 can never be the shortest impulse wave.
        Among waves 1, 3, and 5, wave 3 must not be the shortest.
        """
        rule_name = "Rule 2: Wave 3 Length"
        rule_desc = "Wave 3 cannot be the shortest among waves 1, 3, and 5"

        w1 = waves.get(WaveLabel.W1)
        w3 = waves.get(WaveLabel.W3)
        w5 = waves.get(WaveLabel.W5)

        if not w1 or not w3:
            return ValidationResult(
                rule_name=rule_name,
                rule_description=rule_desc,
                passed=True,
                details="Insufficient waves to validate",
            )

        w1_len = wave_length(w1.start_price, w1.end_price)
        w3_len = wave_length(w3.start_price, w3.end_price)

        if w5:
            w5_len = wave_length(w5.start_price, w5.end_price)
            lengths = [("W1", w1_len), ("W3", w3_len), ("W5", w5_len)]
        else:
            lengths = [("W1", w1_len), ("W3", w3_len)]

        # Sort by length
        sorted_lengths = sorted(lengths, key=lambda x: x[1])
        shortest = sorted_lengths[0]

        passed = shortest[0] != "W3"

        details = f"Lengths: W1={w1_len:.2f}, W3={w3_len:.2f}"
        if w5:
            details += f", W5={w5_len:.2f}"
        details += f". Shortest: {shortest[0]}"
        if not passed:
            details += " (VIOLATION: Wave 3 is shortest)"

        return ValidationResult(
            rule_name=rule_name,
            rule_description=rule_desc,
            passed=passed,
            details=details,
        )

    def _validate_rule3_wave4_no_overlap(self, waves: dict[WaveLabel, Wave]) -> ValidationResult:
        """
        Rule 3: Wave 4 cannot overlap with Wave 1 price territory.
        The low of Wave 4 must stay above the high of Wave 1 (in uptrend).
        """
        rule_name = "Rule 3: Wave 4 No Overlap"
        rule_desc = "Wave 4 cannot enter the price territory of Wave 1"

        w1 = waves.get(WaveLabel.W1)
        w4 = waves.get(WaveLabel.W4)

        if not w1 or not w4:
            return ValidationResult(
                rule_name=rule_name,
                rule_description=rule_desc,
                passed=True,
                details="Insufficient waves to validate",
            )

        # Determine if uptrend or downtrend
        is_uptrend = w1.end_price > w1.start_price

        if is_uptrend:
            # Wave 4 low must be above Wave 1 high
            w1_high = max(w1.start_price, w1.end_price)
            w4_low = min(w4.start_price, w4.end_price)
            passed = w4_low > w1_high
            details = f"W1 high: {w1_high:.2f}, W4 low: {w4_low:.2f}"
        else:
            # Wave 4 high must be below Wave 1 low
            w1_low = min(w1.start_price, w1.end_price)
            w4_high = max(w4.start_price, w4.end_price)
            passed = w4_high < w1_low
            details = f"W1 low: {w1_low:.2f}, W4 high: {w4_high:.2f}"

        if not passed:
            details += " (VIOLATION: overlap detected)"
        else:
            details += " (valid: no overlap)"

        return ValidationResult(
            rule_name=rule_name,
            rule_description=rule_desc,
            passed=passed,
            details=details,
        )

    def is_valid_impulse(self, waves: list[Wave]) -> bool:
        """Check if the wave pattern passes all validation rules."""
        results = self.validate_all(waves)
        return all(r.passed for r in results)
