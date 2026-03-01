"""
Detrended Fluctuation Analysis (DFA) Calculator.

Implements the DFA-n algorithm for calculating the Hurst exponent (α)
from financial time series data. DFA is preferred over classical R/S analysis
because it handles non-stationarity and trends in the data.

Mathematical Background:
- α < 0.5: Anti-correlated (mean-reverting)
- α = 0.5: Uncorrelated (random walk)
- 0.5 < α < 1.0: Long-range correlated (trending)
- α = 1.0: 1/f noise (pink noise)
- α > 1.0: Non-stationary, very strong trend
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np
from scipy import stats


@dataclass
class DFAResult:
    """Result of a DFA calculation."""

    alpha: float
    """The DFA exponent (Hurst exponent). Range typically 0.3-0.8 for financial data."""

    r_squared: float
    """Goodness of fit (R²) of the log-log regression. Higher is better."""

    segment_sizes: List[int]
    """The segment sizes (n values) used in the calculation."""

    fluctuations: List[float]
    """The fluctuation function F(n) values for each segment size."""

    intercept: float
    """The intercept of the log-log regression."""

    std_error: float
    """Standard error of the alpha estimate."""

    data_points: int
    """Number of data points used in the analysis."""

    @property
    def is_trending(self) -> bool:
        """Returns True if alpha indicates trending behavior (α > 0.5)."""
        return self.alpha > 0.5

    @property
    def is_mean_reverting(self) -> bool:
        """Returns True if alpha indicates mean-reverting behavior (α < 0.5)."""
        return self.alpha < 0.5

    @property
    def regime(self) -> str:
        """Returns the market regime classification."""
        if self.alpha < 0.35:
            return "strongly_mean_reverting"
        elif self.alpha < 0.45:
            return "mean_reverting"
        elif self.alpha <= 0.55:
            return "random_walk"
        elif self.alpha <= 0.65:
            return "trending"
        else:
            return "strongly_trending"

    @property
    def confidence_category(self) -> str:
        """Returns confidence category based on R² and std_error."""
        if self.r_squared >= 0.95 and self.std_error < 0.05:
            return "very_high"
        elif self.r_squared >= 0.90 and self.std_error < 0.08:
            return "high"
        elif self.r_squared >= 0.80 and self.std_error < 0.12:
            return "medium"
        else:
            return "low"


class DFACalculator:
    """
    Calculates the Detrended Fluctuation Analysis (DFA) exponent.

    The DFA algorithm:
    1. Integrate the time series (cumulative sum of deviations from mean)
    2. Divide into non-overlapping segments of size n
    3. Fit a polynomial trend to each segment and remove it (detrending)
    4. Calculate the root-mean-square fluctuation F(n)
    5. Repeat for different segment sizes
    6. The slope of log(F(n)) vs log(n) gives the DFA exponent α

    Args:
        polynomial_order: Order of polynomial for detrending (1=linear, 2=quadratic, 3=cubic).
                         DFA-2 (quadratic) is recommended for financial data.
        min_segment_size: Minimum segment size for analysis.
        max_segment_ratio: Maximum segment size as ratio of data length.
        num_segments: Number of different segment sizes to use.
    """

    def __init__(
        self,
        polynomial_order: int = 2,
        min_segment_size: int = 4,
        max_segment_ratio: float = 0.25,
        num_segments: int = 20,
    ):
        if polynomial_order < 1 or polynomial_order > 3:
            raise ValueError("polynomial_order must be 1, 2, or 3")
        if min_segment_size < 4:
            raise ValueError("min_segment_size must be at least 4")
        if max_segment_ratio <= 0 or max_segment_ratio > 0.5:
            raise ValueError("max_segment_ratio must be between 0 and 0.5")
        if num_segments < 5:
            raise ValueError("num_segments must be at least 5")

        self.polynomial_order = polynomial_order
        self.min_segment_size = min_segment_size
        self.max_segment_ratio = max_segment_ratio
        self.num_segments = num_segments

    def calculate(self, prices: np.ndarray) -> DFAResult:
        """
        Calculate the DFA exponent for a price series.

        Args:
            prices: Array of prices (not returns). Can be OHLC close prices.

        Returns:
            DFAResult containing the alpha exponent and diagnostic information.

        Raises:
            ValueError: If insufficient data points for analysis.
        """
        prices = np.asarray(prices, dtype=np.float64)

        if len(prices) < 50:
            raise ValueError(f"Insufficient data: need at least 50 points, got {len(prices)}")

        # Convert prices to log returns
        returns = np.diff(np.log(prices))

        # Remove any NaN or infinite values
        returns = returns[np.isfinite(returns)]

        if len(returns) < 50:
            raise ValueError(f"Insufficient valid returns: need at least 50, got {len(returns)}")

        # Step 1: Integrate the series (cumulative sum of deviations from mean)
        mean_return = np.mean(returns)
        integrated = np.cumsum(returns - mean_return)

        # Step 2: Determine segment sizes (logarithmically spaced)
        n_data = len(integrated)
        max_segment = int(n_data * self.max_segment_ratio)

        # Ensure we have valid segment range
        if max_segment < self.min_segment_size * 2:
            max_segment = self.min_segment_size * 2

        segment_sizes = self._get_segment_sizes(n_data, max_segment)

        if len(segment_sizes) < 5:
            raise ValueError("Not enough valid segment sizes for DFA analysis")

        # Step 3-4: Calculate fluctuation function F(n) for each segment size
        fluctuations = []
        valid_segment_sizes = []

        for n in segment_sizes:
            f_n = self._calculate_fluctuation(integrated, n)
            if f_n is not None and f_n > 0:
                fluctuations.append(f_n)
                valid_segment_sizes.append(n)

        if len(valid_segment_sizes) < 5:
            raise ValueError("Could not calculate enough valid fluctuation values")

        # Step 5: Linear regression on log-log plot
        log_n = np.log(valid_segment_sizes)
        log_f = np.log(fluctuations)

        slope, intercept, r_value, p_value, std_err = stats.linregress(log_n, log_f)

        return DFAResult(
            alpha=slope,
            r_squared=r_value ** 2,
            segment_sizes=valid_segment_sizes,
            fluctuations=fluctuations,
            intercept=intercept,
            std_error=std_err,
            data_points=len(prices),
        )

    def _get_segment_sizes(self, n_data: int, max_segment: int) -> List[int]:
        """Generate logarithmically spaced segment sizes."""
        # Use logarithmic spacing for better coverage
        log_min = np.log(self.min_segment_size)
        log_max = np.log(max_segment)

        segment_sizes = np.exp(np.linspace(log_min, log_max, self.num_segments))
        segment_sizes = np.unique(np.round(segment_sizes).astype(int))

        # Filter to valid range
        segment_sizes = segment_sizes[
            (segment_sizes >= self.min_segment_size) &
            (segment_sizes <= max_segment)
        ]

        return list(segment_sizes)

    def _calculate_fluctuation(self, integrated: np.ndarray, n: int) -> Optional[float]:
        """
        Calculate the fluctuation function F(n) for a given segment size.

        This method implements the detrending step by fitting a polynomial
        to each segment and computing the RMS of the residuals.
        """
        n_data = len(integrated)
        num_segments = n_data // n

        if num_segments < 2:
            return None

        # Process segments from both ends (forward and backward)
        variances = []

        # Forward segments
        for i in range(num_segments):
            start = i * n
            end = start + n
            segment = integrated[start:end]

            variance = self._segment_variance(segment)
            if variance is not None:
                variances.append(variance)

        # Backward segments (to use all data)
        for i in range(num_segments):
            start = n_data - (i + 1) * n
            end = start + n
            if start >= 0:
                segment = integrated[start:end]
                variance = self._segment_variance(segment)
                if variance is not None:
                    variances.append(variance)

        if not variances:
            return None

        # F(n) = sqrt(mean of variances)
        return np.sqrt(np.mean(variances))

    def _segment_variance(self, segment: np.ndarray) -> Optional[float]:
        """Calculate the variance of a segment after polynomial detrending."""
        n = len(segment)
        if n < self.polynomial_order + 2:
            return None

        # Create x values for polynomial fitting
        x = np.arange(n)

        try:
            # Fit polynomial and get residuals
            coeffs = np.polyfit(x, segment, self.polynomial_order)
            trend = np.polyval(coeffs, x)
            residuals = segment - trend

            # Return variance (mean of squared residuals)
            return np.mean(residuals ** 2)
        except (np.linalg.LinAlgError, ValueError):
            return None

    def calculate_from_returns(self, returns: np.ndarray) -> DFAResult:
        """
        Calculate DFA from returns directly (instead of prices).

        Args:
            returns: Array of returns (can be simple or log returns).

        Returns:
            DFAResult containing the alpha exponent and diagnostic information.
        """
        returns = np.asarray(returns, dtype=np.float64)
        returns = returns[np.isfinite(returns)]

        if len(returns) < 50:
            raise ValueError(f"Insufficient data: need at least 50 returns, got {len(returns)}")

        # Integrate the returns
        mean_return = np.mean(returns)
        integrated = np.cumsum(returns - mean_return)

        # Calculate segment sizes
        n_data = len(integrated)
        max_segment = int(n_data * self.max_segment_ratio)

        if max_segment < self.min_segment_size * 2:
            max_segment = self.min_segment_size * 2

        segment_sizes = self._get_segment_sizes(n_data, max_segment)

        if len(segment_sizes) < 5:
            raise ValueError("Not enough valid segment sizes for DFA analysis")

        # Calculate fluctuations
        fluctuations = []
        valid_segment_sizes = []

        for n in segment_sizes:
            f_n = self._calculate_fluctuation(integrated, n)
            if f_n is not None and f_n > 0:
                fluctuations.append(f_n)
                valid_segment_sizes.append(n)

        if len(valid_segment_sizes) < 5:
            raise ValueError("Could not calculate enough valid fluctuation values")

        # Linear regression
        log_n = np.log(valid_segment_sizes)
        log_f = np.log(fluctuations)

        slope, intercept, r_value, p_value, std_err = stats.linregress(log_n, log_f)

        return DFAResult(
            alpha=slope,
            r_squared=r_value ** 2,
            segment_sizes=valid_segment_sizes,
            fluctuations=fluctuations,
            intercept=intercept,
            std_error=std_err,
            data_points=len(returns) + 1,  # +1 for the "price" that would generate these returns
        )
