"""Prophet configuration dataclass."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ProphetConfig:
    """Configuration for Prophet forecasting model."""

    # Training data sizes for different horizons (as fraction of total data)
    long_term_fraction: float = 1.0    # 100% of data
    mid_term_fraction: float = 0.5     # 50% of data
    short_term_fraction: float = 0.25  # 25% of data

    # Forecast periods for each horizon
    forecast_periods: int = 365  # Days to forecast

    # Prophet model parameters
    # For stock prices, reduce seasonality impact since they don't have true seasonality
    yearly_seasonality: bool = True
    weekly_seasonality: bool = False  # Disable weekly - stocks don't have weekly patterns
    daily_seasonality: bool = False

    # Changepoint configuration
    changepoint_prior_scale: float = 0.05
    seasonality_prior_scale: float = 0.1  # Reduced from 10.0 to dampen seasonality
    changepoint_range: float = 0.8

    # Uncertainty intervals
    interval_width: float = 0.95  # 95% confidence interval

    # Growth model
    growth: str = "linear"  # or "logistic" for bounded growth

    # Cap and floor for logistic growth (optional)
    cap: Optional[float] = None
    floor: Optional[float] = None

    # Regressors (custom additional features)
    regressors: List[str] = field(default_factory=list)

    # Country holidays
    country_holidays: Optional[str] = None  # e.g., "US", "DE"


@dataclass
class ForecastHorizon:
    """Represents a forecast horizon configuration."""

    name: str  # "long_term", "mid_term", "short_term"
    display_name: str  # "Langfristig", "Mittelfristig", "Kurzfristig"
    data_fraction: float  # Fraction of historical data to use
    color: str  # Hex color for visualization

    @classmethod
    def get_defaults(cls) -> List["ForecastHorizon"]:
        """Get default forecast horizons."""
        return [
            cls(
                name="long_term",
                display_name="Langfristig",
                data_fraction=1.0,
                color="#1f77b4"  # Blue
            ),
            cls(
                name="mid_term",
                display_name="Mittelfristig",
                data_fraction=0.5,
                color="#2ca02c"  # Green
            ),
            cls(
                name="short_term",
                display_name="Kurzfristig",
                data_fraction=0.25,
                color="#d62728"  # Red
            ),
        ]
