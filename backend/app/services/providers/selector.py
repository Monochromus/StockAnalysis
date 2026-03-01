"""Provider selection logic."""
from __future__ import annotations

from typing import List, Optional

from .base import BaseProvider, is_intraday_interval


class ProviderSelector:
    """Selects the best provider based on requirements and availability."""

    def __init__(self, providers: List[BaseProvider]):
        self._providers = providers

    def select(
        self,
        interval: str,
        user_preference: Optional[str] = None,
    ) -> List[BaseProvider]:
        """
        Select providers in order of preference.

        Returns a list of providers to try, in order of preference.
        The first provider that succeeds will be used.

        Selection logic:
        1. If user specifies a preference, put that first (if available)
        2. For intraday: Alpha Vantage > Twelve Data > yfinance
        3. For daily/weekly: yfinance > Twelve Data > Alpha Vantage
        4. Filter out unavailable providers and those that don't support the interval
        5. Check rate limits
        """
        # Filter to available providers that support this interval
        available = [
            p for p in self._providers
            if p.is_available() and p.supports_interval(interval)
        ]

        if not available:
            return []

        # Sort by priority (lower = better)
        is_intraday = is_intraday_interval(interval)

        def get_priority(provider: BaseProvider) -> int:
            base_priority = provider.info.priority

            # Adjust priority based on interval type
            if is_intraday:
                # For intraday, prefer providers with good intraday support
                # Alpha Vantage (1) and Twelve Data (2) are better than yfinance (3)
                return base_priority
            else:
                # For daily, yfinance is preferred (free, reliable)
                # Invert so yfinance (3) becomes best
                if provider.info.name == "yfinance":
                    return 0
                return base_priority

            return base_priority

        sorted_providers = sorted(available, key=get_priority)

        # If user has a preference, move that provider to front
        if user_preference:
            pref_lower = user_preference.lower()
            preferred = None
            others = []

            for p in sorted_providers:
                if p.info.name.lower() == pref_lower:
                    preferred = p
                else:
                    others.append(p)

            if preferred:
                return [preferred] + others

        return sorted_providers

    def get_all_providers(self) -> List[BaseProvider]:
        """Return all registered providers."""
        return self._providers

    def get_provider_by_name(self, name: str) -> Optional[BaseProvider]:
        """Get a specific provider by name."""
        for p in self._providers:
            if p.info.name.lower() == name.lower():
                return p
        return None
