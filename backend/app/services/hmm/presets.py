"""HMM Preset Management for saving and loading model/strategy configurations."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HMMPreset(BaseModel):
    """A saved HMM configuration preset."""

    name: str = Field(..., description="Unique preset name")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    # Metadata
    symbol: str = Field(..., description="Symbol this preset was created for")
    period: str = Field("1y", description="Data period")
    interval: str = Field("1d", description="Data interval")

    # HMM Model Settings
    n_states: int = Field(7, ge=3, le=10)
    n_iter: int = Field(100, ge=10, le=500)
    model_type: str = Field("hmm_gaussian")
    student_t_df: float = Field(5.0)
    selected_features: List[str] = Field(default=["log_return", "range", "volume_change"])

    # Strategy Parameters
    required_confirmations: int = Field(7)
    rsi_oversold: float = Field(30.0)
    rsi_overbought: float = Field(70.0)
    rsi_bull_min: float = Field(40.0)
    rsi_bear_max: float = Field(60.0)
    macd_threshold: float = Field(0.0)
    momentum_threshold: float = Field(0.0)
    adx_trend_threshold: float = Field(25.0)
    volume_ratio_threshold: float = Field(1.0)
    regime_confidence_min: float = Field(0.5)
    cooldown_periods: int = Field(48)
    bullish_regimes: List[str] = Field(default=["Bull Run", "Bull", "Neutral Up"])
    bearish_regimes: List[str] = Field(default=["Crash", "Bear", "Neutral Down"])
    stop_loss_pct: float = Field(0.0)
    take_profit_pct: float = Field(0.0)
    trailing_stop_pct: float = Field(0.0)
    max_hold_periods: int = Field(0)
    ma_period: int = Field(50)
    exit_on_regime_change: bool = Field(True)
    exit_on_opposite_signal: bool = Field(True)

    # Backtest Settings
    leverage: float = Field(1.0)
    slippage_pct: float = Field(0.001)
    commission_pct: float = Field(0.001)
    initial_capital: float = Field(10000.0)

    # Performance metrics from when preset was saved (optional)
    saved_alpha: Optional[float] = None
    saved_sharpe: Optional[float] = None
    saved_total_return: Optional[float] = None


class PresetManager:
    """Manages HMM presets with file-based persistence."""

    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize preset manager.

        Args:
            storage_dir: Directory to store presets. Defaults to ~/.stockanalysis/presets
        """
        if storage_dir is None:
            home = Path.home()
            storage_dir = home / ".stockanalysis" / "presets"

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.presets_file = self.storage_dir / "hmm_presets.json"

        # Load existing presets
        self._presets: Dict[str, HMMPreset] = {}
        self._load_presets()

    def _load_presets(self) -> None:
        """Load presets from disk."""
        if self.presets_file.exists():
            try:
                with open(self.presets_file, "r") as f:
                    data = json.load(f)
                    for name, preset_data in data.items():
                        self._presets[name] = HMMPreset(**preset_data)
            except Exception as e:
                print(f"Error loading presets: {e}")
                self._presets = {}

    def _save_presets(self) -> None:
        """Save presets to disk."""
        try:
            data = {name: preset.model_dump() for name, preset in self._presets.items()}
            with open(self.presets_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving presets: {e}")
            raise

    def generate_default_name(self, symbol: str, interval: str, period: str) -> str:
        """Generate a default preset name from symbol, interval, and period."""
        return f"{symbol}_{interval}_{period}"

    def save_preset(self, preset: HMMPreset) -> HMMPreset:
        """
        Save a preset.

        Args:
            preset: The preset to save

        Returns:
            The saved preset
        """
        preset.updated_at = datetime.utcnow().isoformat()
        if preset.name not in self._presets:
            preset.created_at = preset.updated_at

        self._presets[preset.name] = preset
        self._save_presets()
        return preset

    def get_preset(self, name: str) -> Optional[HMMPreset]:
        """
        Get a preset by name.

        Args:
            name: Preset name

        Returns:
            The preset if found, None otherwise
        """
        return self._presets.get(name)

    def list_presets(self) -> List[HMMPreset]:
        """
        List all presets.

        Returns:
            List of all presets sorted by updated_at descending
        """
        presets = list(self._presets.values())
        presets.sort(key=lambda p: p.updated_at, reverse=True)
        return presets

    def delete_preset(self, name: str) -> bool:
        """
        Delete a preset.

        Args:
            name: Preset name

        Returns:
            True if deleted, False if not found
        """
        if name in self._presets:
            del self._presets[name]
            self._save_presets()
            return True
        return False

    def preset_exists(self, name: str) -> bool:
        """Check if a preset exists."""
        return name in self._presets


# Global preset manager instance
_preset_manager: Optional[PresetManager] = None


def get_preset_manager() -> PresetManager:
    """Get the global preset manager instance."""
    global _preset_manager
    if _preset_manager is None:
        _preset_manager = PresetManager()
    return _preset_manager
