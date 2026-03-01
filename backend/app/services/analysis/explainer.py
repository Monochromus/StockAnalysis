from __future__ import annotations
from app.schemas import WaveCount, WaveLabel, RiskReward


class WaveExplainer:
    """
    Generates human-readable explanations for wave analysis.
    """

    def explain(
        self,
        wave_count: WaveCount | None,
        alternatives: list[WaveCount],
        risk_reward: RiskReward | None,
    ) -> str:
        """
        Generate a comprehensive explanation of the analysis.

        Args:
            wave_count: Primary wave count
            alternatives: Alternative wave counts
            risk_reward: Risk/reward analysis

        Returns:
            Human-readable explanation
        """
        if not wave_count:
            return self._no_pattern_explanation()

        parts = []

        # Wave pattern summary
        parts.append(self._pattern_summary(wave_count))

        # Validation summary
        parts.append(self._validation_summary(wave_count))

        # Fibonacci analysis
        parts.append(self._fibonacci_summary(wave_count))

        # Risk/Reward
        if risk_reward:
            parts.append(self._risk_reward_summary(risk_reward))

        # Alternatives
        if alternatives:
            parts.append(self._alternatives_summary(alternatives))

        return "\n\n".join(parts)

    def _no_pattern_explanation(self) -> str:
        return (
            "No clear Elliott Wave pattern was detected in the current data. "
            "This could indicate:\n"
            "- The market is in a complex corrective phase\n"
            "- The zigzag threshold may need adjustment\n"
            "- More price data may be needed for pattern recognition\n\n"
            "Consider adjusting the analysis parameters or viewing a different timeframe."
        )

    def _pattern_summary(self, wave_count: WaveCount) -> str:
        """Summarize the wave pattern."""
        wave_labels = [w.label.value for w in wave_count.waves]
        wave_str = " → ".join(wave_labels)

        status = "complete" if wave_count.is_complete else "incomplete"
        trend = self._determine_trend(wave_count)

        return (
            f"**{wave_count.wave_type.value.upper()} PATTERN DETECTED**\n"
            f"Waves identified: {wave_str}\n"
            f"Pattern status: {status}\n"
            f"Trend direction: {trend}\n"
            f"Confidence: {wave_count.overall_confidence:.1f}%"
        )

    def _validation_summary(self, wave_count: WaveCount) -> str:
        """Summarize validation results."""
        lines = ["**ELLIOTT WAVE RULES**"]

        for result in wave_count.validation_results:
            status = "✓" if result.passed else "✗"
            lines.append(f"{status} {result.rule_name}")
            if result.details:
                lines.append(f"   {result.details}")

        all_passed = all(r.passed for r in wave_count.validation_results)
        if all_passed:
            lines.append("\nAll cardinal rules satisfied - valid Elliott Wave structure.")
        else:
            lines.append("\nWarning: Some rules violated - consider alternative counts.")

        return "\n".join(lines)

    def _fibonacci_summary(self, wave_count: WaveCount) -> str:
        """Summarize Fibonacci analysis."""
        lines = ["**FIBONACCI ANALYSIS**"]

        for score in wave_count.fibonacci_scores:
            quality = self._score_to_quality(score.score)
            lines.append(
                f"Wave {score.wave_label.value}: "
                f"Actual {score.actual_ratio:.3f} vs Expected {score.expected_ratio:.3f} "
                f"({quality}, Score: {score.score:.1f})"
            )

        return "\n".join(lines)

    def _risk_reward_summary(self, rr: RiskReward) -> str:
        """Summarize risk/reward levels."""
        return (
            f"**TRADING LEVELS**\n"
            f"Entry: ${rr.entry_price:,.2f}\n"
            f"Stop Loss: ${rr.stop_loss:,.2f}\n"
            f"Risk/Reward Ratio: 1:{rr.risk_reward_ratio:.2f}"
        )

    def _alternatives_summary(self, alternatives: list[WaveCount]) -> str:
        """Summarize alternative wave counts."""
        lines = [f"**ALTERNATIVE COUNTS** ({len(alternatives)} found)"]

        for i, alt in enumerate(alternatives[:3], 1):  # Show top 3
            wave_labels = " → ".join([w.label.value for w in alt.waves])
            lines.append(
                f"{i}. {wave_labels} (Confidence: {alt.overall_confidence:.1f}%)"
            )

        return "\n".join(lines)

    def _determine_trend(self, wave_count: WaveCount) -> str:
        """Determine the trend direction from the wave pattern."""
        if not wave_count.waves:
            return "Unknown"

        first_wave = wave_count.waves[0]
        if first_wave.end_price > first_wave.start_price:
            return "Bullish (Uptrend)"
        else:
            return "Bearish (Downtrend)"

    def _score_to_quality(self, score: float) -> str:
        """Convert a numeric score to a quality descriptor."""
        if score >= 90:
            return "Excellent"
        elif score >= 70:
            return "Good"
        elif score >= 50:
            return "Fair"
        elif score >= 30:
            return "Weak"
        else:
            return "Poor"
