"""
COT Data Analyzer.
Calculates COT Index, net positions, changes, and generates trading signals.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class COTAnalyzer:
    """Analyzer for COT data calculations and signal generation."""

    @staticmethod
    def calculate_net_positions(record: Dict[str, Any]) -> Dict[str, int]:
        """
        Calculate net positions from a COT record.

        Returns:
            Dict with commercial_net, noncommercial_net, nonreportable_net
        """
        return {
            "commercial_net": record.get("commercial_long", 0) - record.get("commercial_short", 0),
            "noncommercial_net": record.get("noncommercial_long", 0) - record.get("noncommercial_short", 0),
            "nonreportable_net": record.get("nonreportable_long", 0) - record.get("nonreportable_short", 0),
        }

    @staticmethod
    def calculate_cot_index(
        current_net: int,
        history: List[int],
        lookback_weeks: int = 52
    ) -> float:
        """
        Calculate COT Index (0-100).

        The COT Index shows where current positioning stands relative to
        the historical range. 0 = lowest in lookback period, 100 = highest.

        Args:
            current_net: Current net position
            history: List of historical net positions
            lookback_weeks: Number of weeks for lookback

        Returns:
            COT Index value (0-100)
        """
        if not history:
            return 50.0

        # Use lookback period
        lookback_data = history[:lookback_weeks]
        if not lookback_data:
            return 50.0

        min_net = min(lookback_data)
        max_net = max(lookback_data)

        # Avoid division by zero
        if max_net == min_net:
            return 50.0

        index = (current_net - min_net) / (max_net - min_net) * 100
        return round(max(0, min(100, index)), 2)

    @staticmethod
    def calculate_changes(
        history: List[Dict[str, Any]],
        position_type: str = "commercial"
    ) -> Tuple[int, int]:
        """
        Calculate weekly and monthly position changes.

        Args:
            history: List of COT records (newest first)
            position_type: "commercial" or "noncommercial"

        Returns:
            Tuple of (weekly_change, monthly_change)
        """
        net_key = f"{position_type}_net"

        if len(history) < 2:
            return 0, 0

        current = history[0].get(net_key, 0)
        weekly_change = current - history[1].get(net_key, 0) if len(history) > 1 else 0

        # Monthly change (4 weeks ago)
        monthly_change = current - history[4].get(net_key, 0) if len(history) > 4 else weekly_change

        return weekly_change, monthly_change

    @classmethod
    def generate_signal(
        cls,
        cot_index_commercial: float,
        cot_index_noncommercial: float,
        weekly_change_commercial: int,
        weekly_change_noncommercial: int
    ) -> Tuple[str, str, str]:
        """
        Generate trading signal based on COT data.

        Logic:
        - Commercials are "smart money" - their extreme positions often
          precede market reversals
        - When commercials are extremely long (high COT index) → bullish
        - When commercials are extremely short (low COT index) → bearish
        - Non-commercial extremes often indicate crowded trades

        Args:
            cot_index_commercial: Commercial COT Index (0-100)
            cot_index_noncommercial: Non-commercial COT Index (0-100)
            weekly_change_commercial: Weekly change in commercial net
            weekly_change_noncommercial: Weekly change in non-commercial net

        Returns:
            Tuple of (signal, strength, interpretation)
        """
        signal = "neutral"
        strength = "weak"
        interpretation = ""

        # Strong bullish: Commercials extremely long, specs extremely short
        if cot_index_commercial >= 80 and cot_index_noncommercial <= 20:
            signal = "bullish"
            strength = "strong"
            interpretation = (
                "Commercials at extreme long positions while speculators are extremely short. "
                "Smart money positioning suggests potential bullish reversal."
            )
        # Strong bearish: Commercials extremely short, specs extremely long
        elif cot_index_commercial <= 20 and cot_index_noncommercial >= 80:
            signal = "bearish"
            strength = "strong"
            interpretation = (
                "Commercials at extreme short positions while speculators are extremely long. "
                "Crowded long trade with smart money on the opposite side suggests caution."
            )
        # Moderate bullish
        elif cot_index_commercial >= 70:
            signal = "bullish"
            strength = "moderate"
            interpretation = (
                "Commercials holding elevated long positions. "
                "This often precedes upward price moves."
            )
        # Moderate bearish
        elif cot_index_commercial <= 30:
            signal = "bearish"
            strength = "moderate"
            interpretation = (
                "Commercials holding reduced long positions. "
                "This often precedes downward price moves."
            )
        # Slight bullish based on changes
        elif weekly_change_commercial > 0 and cot_index_commercial >= 50:
            signal = "bullish"
            strength = "weak"
            interpretation = (
                "Commercials increasing long positions. "
                "Watch for continuation of accumulation."
            )
        # Slight bearish based on changes
        elif weekly_change_commercial < 0 and cot_index_commercial <= 50:
            signal = "bearish"
            strength = "weak"
            interpretation = (
                "Commercials reducing long positions. "
                "Watch for continuation of distribution."
            )
        else:
            interpretation = (
                "No extreme positioning detected. "
                "Market is in a neutral zone without clear COT-based directional bias."
            )

        return signal, strength, interpretation

    @classmethod
    def analyze(
        cls,
        history: List[Dict[str, Any]],
        lookback_weeks: int = 52
    ) -> Dict[str, Any]:
        """
        Perform full COT analysis.

        Args:
            history: List of COT records (newest first)
            lookback_weeks: Lookback period for COT Index

        Returns:
            Complete analysis dict
        """
        if not history:
            return {
                "error": "No data available",
                "cot_index_commercial": 50.0,
                "cot_index_noncommercial": 50.0,
                "weekly_change_commercial": 0,
                "weekly_change_noncommercial": 0,
                "monthly_change_commercial": 0,
                "monthly_change_noncommercial": 0,
                "signal": "neutral",
                "signal_strength": "weak",
                "interpretation": "Insufficient data for analysis.",
            }

        current = history[0]

        # Extract net position histories
        commercial_nets = [r.get("commercial_net", 0) for r in history]
        noncommercial_nets = [r.get("noncommercial_net", 0) for r in history]

        # Calculate COT indices
        cot_index_comm = cls.calculate_cot_index(
            commercial_nets[0] if commercial_nets else 0,
            commercial_nets,
            lookback_weeks
        )
        cot_index_noncomm = cls.calculate_cot_index(
            noncommercial_nets[0] if noncommercial_nets else 0,
            noncommercial_nets,
            lookback_weeks
        )

        # Calculate changes
        weekly_comm, monthly_comm = cls.calculate_changes(history, "commercial")
        weekly_noncomm, monthly_noncomm = cls.calculate_changes(history, "noncommercial")

        # Generate signal
        signal, strength, interpretation = cls.generate_signal(
            cot_index_comm,
            cot_index_noncomm,
            weekly_comm,
            weekly_noncomm
        )

        return {
            "cot_index_commercial": cot_index_comm,
            "cot_index_noncommercial": cot_index_noncomm,
            "lookback_weeks": lookback_weeks,
            "weekly_change_commercial": weekly_comm,
            "weekly_change_noncommercial": weekly_noncomm,
            "monthly_change_commercial": monthly_comm,
            "monthly_change_noncommercial": monthly_noncomm,
            "signal": signal,
            "signal_strength": strength,
            "interpretation": interpretation,
        }
