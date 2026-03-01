from __future__ import annotations
from app.schemas import Wave, WaveLabel, FibonacciScore
from app.utils.math_helpers import calculate_retracement, calculate_extension, gaussian_score


class FibonacciAnalyzer:
    """
    Analyzes wave relationships against Fibonacci ratios.
    """

    # Ideal Fibonacci ratios for each wave
    WAVE2_RETRACEMENT_TARGETS = [0.50, 0.618]  # 50% or 61.8% retracement of W1
    WAVE3_EXTENSION_TARGETS = [1.618, 2.618]   # 161.8% or 261.8% extension of W1
    WAVE4_RETRACEMENT_TARGETS = [0.382]        # 38.2% retracement of W3
    WAVE5_EXTENSION_TARGETS = [0.618, 1.0]     # 61.8% or 100% of W1

    def __init__(self, sigma: float = 0.08):
        """
        Initialize the Fibonacci analyzer.

        Args:
            sigma: Standard deviation for Gaussian scoring (controls tolerance)
        """
        self.sigma = sigma

    def analyze_all(self, waves: list[Wave]) -> list[FibonacciScore]:
        """
        Analyze all waves for Fibonacci relationships.

        Args:
            waves: List of waves to analyze

        Returns:
            List of FibonacciScore for each applicable wave
        """
        scores = []
        wave_dict = {w.label: w for w in waves}

        # Wave 2 retracement
        w1 = wave_dict.get(WaveLabel.W1)
        w2 = wave_dict.get(WaveLabel.W2)
        if w1 and w2:
            score = self._score_wave2(w1, w2)
            if score:
                scores.append(score)

        # Wave 3 extension
        w3 = wave_dict.get(WaveLabel.W3)
        if w1 and w2 and w3:
            score = self._score_wave3(w1, w2, w3)
            if score:
                scores.append(score)

        # Wave 4 retracement
        w4 = wave_dict.get(WaveLabel.W4)
        if w3 and w4:
            score = self._score_wave4(w3, w4)
            if score:
                scores.append(score)

        # Wave 5 extension
        w5 = wave_dict.get(WaveLabel.W5)
        if w1 and w4 and w5:
            score = self._score_wave5(w1, w4, w5)
            if score:
                scores.append(score)

        return scores

    def _score_wave2(self, w1: Wave, w2: Wave) -> FibonacciScore | None:
        """Score Wave 2's retracement of Wave 1."""
        actual_ratio = calculate_retracement(w1.start_price, w1.end_price, w2.end_price)

        # Find best matching target
        best_target, best_score = self._find_best_match(
            actual_ratio, self.WAVE2_RETRACEMENT_TARGETS
        )

        return FibonacciScore(
            wave_label=WaveLabel.W2,
            expected_ratio=best_target,
            actual_ratio=round(actual_ratio, 4),
            deviation=round(abs(actual_ratio - best_target), 4),
            score=best_score,
        )

    def _score_wave3(self, w1: Wave, w2: Wave, w3: Wave) -> FibonacciScore | None:
        """Score Wave 3's extension relative to Wave 1."""
        # Wave 3 extension from Wave 2's end
        w1_length = abs(w1.end_price - w1.start_price)
        if w1_length == 0:
            return None

        w3_length = abs(w3.end_price - w3.start_price)
        actual_ratio = w3_length / w1_length

        best_target, best_score = self._find_best_match(
            actual_ratio, self.WAVE3_EXTENSION_TARGETS
        )

        return FibonacciScore(
            wave_label=WaveLabel.W3,
            expected_ratio=best_target,
            actual_ratio=round(actual_ratio, 4),
            deviation=round(abs(actual_ratio - best_target), 4),
            score=best_score,
        )

    def _score_wave4(self, w3: Wave, w4: Wave) -> FibonacciScore | None:
        """Score Wave 4's retracement of Wave 3."""
        actual_ratio = calculate_retracement(w3.start_price, w3.end_price, w4.end_price)

        best_target, best_score = self._find_best_match(
            actual_ratio, self.WAVE4_RETRACEMENT_TARGETS
        )

        return FibonacciScore(
            wave_label=WaveLabel.W4,
            expected_ratio=best_target,
            actual_ratio=round(actual_ratio, 4),
            deviation=round(abs(actual_ratio - best_target), 4),
            score=best_score,
        )

    def _score_wave5(self, w1: Wave, w4: Wave, w5: Wave) -> FibonacciScore | None:
        """Score Wave 5's relationship to Wave 1."""
        w1_length = abs(w1.end_price - w1.start_price)
        if w1_length == 0:
            return None

        w5_length = abs(w5.end_price - w5.start_price)
        actual_ratio = w5_length / w1_length

        best_target, best_score = self._find_best_match(
            actual_ratio, self.WAVE5_EXTENSION_TARGETS
        )

        return FibonacciScore(
            wave_label=WaveLabel.W5,
            expected_ratio=best_target,
            actual_ratio=round(actual_ratio, 4),
            deviation=round(abs(actual_ratio - best_target), 4),
            score=best_score,
        )

    def _find_best_match(self, actual: float, targets: list[float]) -> tuple[float, float]:
        """Find the best matching Fibonacci target and return target and score."""
        best_target = targets[0]
        best_score = gaussian_score(actual, targets[0], self.sigma)

        for target in targets[1:]:
            score = gaussian_score(actual, target, self.sigma)
            if score > best_score:
                best_score = score
                best_target = target

        return best_target, best_score

    def calculate_overall_score(self, scores: list[FibonacciScore]) -> float:
        """Calculate weighted average score across all Fibonacci measurements."""
        if not scores:
            return 0.0

        # Weight Wave 3 higher as it's most critical
        weights = {
            WaveLabel.W2: 1.0,
            WaveLabel.W3: 1.5,
            WaveLabel.W4: 1.0,
            WaveLabel.W5: 0.8,
        }

        total_weight = 0.0
        weighted_sum = 0.0

        for score in scores:
            weight = weights.get(score.wave_label, 1.0)
            weighted_sum += score.score * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        return round(weighted_sum / total_weight, 2)
