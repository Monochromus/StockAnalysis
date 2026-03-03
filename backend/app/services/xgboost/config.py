"""XGBoost configuration dataclass."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class XGBoostConfig:
    """Configuration for XGBoost residual correction model."""

    # Hyperparameters (UI-steuerbar)
    n_estimators: int = 500
    max_depth: int = 4
    learning_rate: float = 0.05
    subsample: float = 0.8
    colsample_bytree: float = 0.8
    min_child_weight: int = 5
    reg_alpha: float = 0.1
    reg_lambda: float = 1.0
    early_stopping_rounds: int = 50

    # Feature-Gruppen (togglebar)
    use_time_features: bool = True
    use_lag_features: bool = True
    use_rolling_features: bool = True
    use_prophet_components: bool = True
    use_market_structure: bool = True

    # Training
    train_test_split: float = 0.8
    random_state: int = 42

    # Feature configuration
    lag_residual_periods: List[int] = field(default_factory=lambda: [1, 2, 3, 4, 5])
    lag_price_periods: List[int] = field(default_factory=lambda: [1, 3, 5])
    rolling_windows: List[int] = field(default_factory=lambda: [7, 30])

    # NaN handling
    min_warmup_rows: int = 30  # Rows to drop due to rolling windows

    def get_enabled_feature_groups(self) -> List[str]:
        """Get list of enabled feature groups."""
        groups = []
        if self.use_time_features:
            groups.append("time")
        if self.use_lag_features:
            groups.append("lag")
        if self.use_rolling_features:
            groups.append("rolling")
        if self.use_prophet_components:
            groups.append("prophet")
        if self.use_market_structure:
            groups.append("market")
        return groups
