"""
Sigmoid mapping function for adaptive threshold calculation.

Maps the DFA alpha exponent to a threshold multiplier using a generalized
sigmoid function. This provides smooth transitions between market regimes
rather than hard cutoffs.

The sigmoid function:
f(α) = β_min + (β_max - β_min) / (1 + e^(-k·(α - α_mid)))

Properties:
- When α << α_mid: f(α) ≈ β_min (sensitive, small swings detected)
- When α = α_mid:  f(α) = (β_min + β_max) / 2 (neutral)
- When α >> α_mid: f(α) ≈ β_max (tolerant, only large swings count)
"""

from dataclasses import dataclass
import numpy as np


def sigmoid_mapping(
    alpha: float,
    beta_min: float = 0.5,
    beta_max: float = 3.0,
    k: float = 10.0,
    alpha_mid: float = 0.5,
) -> float:
    """
    Map DFA alpha to threshold multiplier using sigmoid function.

    Args:
        alpha: DFA exponent value (typically 0.3-0.8 for financial data).
        beta_min: Minimum multiplier (for mean-reverting, α << 0.5).
        beta_max: Maximum multiplier (for trending, α >> 0.5).
        k: Steepness of the sigmoid transition (higher = sharper).
        alpha_mid: Midpoint of the sigmoid (inflection point).

    Returns:
        Threshold multiplier to be applied to ATR.

    Examples:
        >>> sigmoid_mapping(0.3)  # Mean-reverting
        0.62  # Close to beta_min, sensitive to small swings
        >>> sigmoid_mapping(0.5)  # Random walk
        1.75  # Midpoint between beta_min and beta_max
        >>> sigmoid_mapping(0.7)  # Trending
        2.88  # Close to beta_max, only large swings count
    """
    # Clamp alpha to reasonable range to avoid numerical issues
    alpha = max(0.0, min(2.0, alpha))

    # Calculate sigmoid
    beta_range = beta_max - beta_min
    exponent = -k * (alpha - alpha_mid)

    # Prevent overflow
    if exponent > 700:
        return beta_min
    elif exponent < -700:
        return beta_max

    return beta_min + beta_range / (1 + np.exp(exponent))


@dataclass
class SigmoidConfig:
    """Configuration for sigmoid mapping."""

    beta_min: float = 0.5
    beta_max: float = 3.0
    k: float = 10.0
    alpha_mid: float = 0.5


class SigmoidMapper:
    """
    Configurable sigmoid mapping with additional utilities.

    Provides:
    - Standard mapping with configured parameters
    - Inverse mapping (multiplier to alpha)
    - Derivative for sensitivity analysis
    - Visualization helpers
    """

    def __init__(
        self,
        beta_min: float = 0.5,
        beta_max: float = 3.0,
        k: float = 10.0,
        alpha_mid: float = 0.5,
    ):
        self.beta_min = beta_min
        self.beta_max = beta_max
        self.k = k
        self.alpha_mid = alpha_mid
        self.beta_range = beta_max - beta_min

    def map(self, alpha: float) -> float:
        """Map alpha to threshold multiplier."""
        return sigmoid_mapping(
            alpha,
            self.beta_min,
            self.beta_max,
            self.k,
            self.alpha_mid,
        )

    def map_array(self, alphas: np.ndarray) -> np.ndarray:
        """Map an array of alpha values."""
        alphas = np.clip(alphas, 0.0, 2.0)
        exponent = -self.k * (alphas - self.alpha_mid)
        exponent = np.clip(exponent, -700, 700)
        return self.beta_min + self.beta_range / (1 + np.exp(exponent))

    def inverse(self, beta: float) -> float:
        """
        Inverse mapping: threshold multiplier to alpha.

        Useful for understanding what alpha would produce a given multiplier.

        Args:
            beta: Threshold multiplier value.

        Returns:
            Alpha value that would produce this multiplier.
        """
        # Clamp beta to valid range
        beta = max(self.beta_min + 0.001, min(self.beta_max - 0.001, beta))

        # Solve sigmoid for alpha:
        # β = β_min + (β_max - β_min) / (1 + e^(-k(α - α_mid)))
        # => (β - β_min) * (1 + e^(-k(α - α_mid))) = β_max - β_min
        # => 1 + e^(-k(α - α_mid)) = (β_max - β_min) / (β - β_min)
        # => e^(-k(α - α_mid)) = (β_max - β_min) / (β - β_min) - 1
        # => -k(α - α_mid) = ln((β_max - β_min) / (β - β_min) - 1)
        # => α = α_mid - (1/k) * ln((β_max - β_min) / (β - β_min) - 1)

        ratio = self.beta_range / (beta - self.beta_min) - 1
        if ratio <= 0:
            return self.alpha_mid + 1.0  # Very high alpha
        return self.alpha_mid - (1 / self.k) * np.log(ratio)

    def derivative(self, alpha: float) -> float:
        """
        Calculate the derivative df/dα at a given alpha.

        Useful for understanding sensitivity of the mapping.
        The derivative is highest at α_mid (maximum sensitivity).

        Args:
            alpha: Alpha value.

        Returns:
            Derivative of the sigmoid at this alpha.
        """
        alpha = max(0.0, min(2.0, alpha))
        exponent = -self.k * (alpha - self.alpha_mid)

        if abs(exponent) > 700:
            return 0.0

        exp_val = np.exp(exponent)
        denominator = (1 + exp_val) ** 2

        return self.k * self.beta_range * exp_val / denominator

    def get_characteristic_points(self) -> dict:
        """
        Get characteristic points of the sigmoid curve.

        Returns dict with:
        - mean_reverting: alpha where f(α) ≈ β_min + 0.1*(β_max - β_min)
        - neutral: alpha_mid where f(α) = midpoint
        - trending: alpha where f(α) ≈ β_max - 0.1*(β_max - β_min)
        """
        return {
            "mean_reverting": {
                "alpha": self.inverse(self.beta_min + 0.1 * self.beta_range),
                "beta": self.beta_min + 0.1 * self.beta_range,
            },
            "neutral": {
                "alpha": self.alpha_mid,
                "beta": self.beta_min + 0.5 * self.beta_range,
            },
            "trending": {
                "alpha": self.inverse(self.beta_max - 0.1 * self.beta_range),
                "beta": self.beta_max - 0.1 * self.beta_range,
            },
        }

    def generate_curve(self, n_points: int = 100) -> tuple:
        """
        Generate sigmoid curve data for visualization.

        Args:
            n_points: Number of points to generate.

        Returns:
            Tuple of (alpha_values, beta_values) as numpy arrays.
        """
        alphas = np.linspace(0, 1, n_points)
        betas = self.map_array(alphas)
        return alphas, betas
