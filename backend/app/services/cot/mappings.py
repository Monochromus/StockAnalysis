"""
Symbol to COT mapping for commodity futures.
Maps Yahoo Finance symbols to CFTC COT report commodity names.
"""

from typing import Dict, Optional, List


class COTMapping:
    """Mapping between Yahoo Finance symbols and CFTC COT commodity names."""

    # Yahoo Finance Symbol -> COT commodity info
    SYMBOL_TO_COT: Dict[str, Dict[str, str]] = {
        # Energy
        "CL=F": {"name": "CRUDE OIL, LIGHT SWEET", "group": "Petroleum", "exchange": "NYMEX"},
        "NG=F": {"name": "NATURAL GAS", "group": "Natural Gas", "exchange": "NYMEX"},
        "HO=F": {"name": "NY HARBOR ULSD", "group": "Petroleum", "exchange": "NYMEX"},
        "RB=F": {"name": "RBOB GASOLINE", "group": "Petroleum", "exchange": "NYMEX"},
        "BZ=F": {"name": "BRENT CRUDE OIL LAST DAY", "group": "Petroleum", "exchange": "NYMEX"},

        # Precious Metals
        "GC=F": {"name": "GOLD", "group": "Precious Metals", "exchange": "COMEX"},
        "SI=F": {"name": "SILVER", "group": "Precious Metals", "exchange": "COMEX"},
        "PL=F": {"name": "PLATINUM", "group": "Precious Metals", "exchange": "NYMEX"},
        "PA=F": {"name": "PALLADIUM", "group": "Precious Metals", "exchange": "NYMEX"},

        # Base Metals
        "HG=F": {"name": "COPPER", "group": "Base Metals", "exchange": "COMEX"},

        # Grains
        "ZC=F": {"name": "CORN", "group": "Grains", "exchange": "CBOT"},
        "ZW=F": {"name": "WHEAT-SRW", "group": "Grains", "exchange": "CBOT"},
        "ZS=F": {"name": "SOYBEANS", "group": "Oilseeds", "exchange": "CBOT"},
        "ZM=F": {"name": "SOYBEAN MEAL", "group": "Oilseeds", "exchange": "CBOT"},
        "ZL=F": {"name": "SOYBEAN OIL", "group": "Oilseeds", "exchange": "CBOT"},
        "ZO=F": {"name": "OATS", "group": "Grains", "exchange": "CBOT"},
        "ZR=F": {"name": "ROUGH RICE", "group": "Grains", "exchange": "CBOT"},
        "KE=F": {"name": "WHEAT-HRW", "group": "Grains", "exchange": "KCBT"},

        # Softs
        "KC=F": {"name": "COFFEE C", "group": "Softs", "exchange": "ICE"},
        "SB=F": {"name": "SUGAR NO. 11", "group": "Softs", "exchange": "ICE"},
        "CT=F": {"name": "COTTON NO. 2", "group": "Softs", "exchange": "ICE"},
        "CC=F": {"name": "COCOA", "group": "Softs", "exchange": "ICE"},
        "OJ=F": {"name": "FRZN CONCENTRATED ORANGE JUICE", "group": "Softs", "exchange": "ICE"},

        # Livestock
        "LE=F": {"name": "LIVE CATTLE", "group": "Livestock", "exchange": "CME"},
        "HE=F": {"name": "LEAN HOGS", "group": "Livestock", "exchange": "CME"},
        "GF=F": {"name": "FEEDER CATTLE", "group": "Livestock", "exchange": "CME"},
    }

    # Alternative names for fuzzy matching
    ALTERNATIVE_NAMES: Dict[str, List[str]] = {
        "CRUDE OIL, LIGHT SWEET": ["CRUDE OIL", "WTI CRUDE", "LIGHT SWEET CRUDE"],
        "NATURAL GAS": ["NAT GAS", "HENRY HUB NATURAL GAS"],
        "NY HARBOR ULSD": ["HEATING OIL", "ULSD", "NY HARBOR"],
        "WHEAT-SRW": ["WHEAT", "CHICAGO WHEAT", "SOFT RED WINTER WHEAT"],
        "WHEAT-HRW": ["KC WHEAT", "KANSAS WHEAT", "HARD RED WINTER"],
        "COFFEE C": ["COFFEE", "ARABICA COFFEE"],
        "SUGAR NO. 11": ["SUGAR", "RAW SUGAR", "WORLD SUGAR"],
        "COTTON NO. 2": ["COTTON", "US COTTON"],
        "FRZN CONCENTRATED ORANGE JUICE": ["ORANGE JUICE", "OJ", "FCOJ"],
    }

    @classmethod
    def get_cot_info(cls, symbol: str) -> Optional[Dict[str, str]]:
        """Get COT info for a Yahoo Finance symbol."""
        return cls.SYMBOL_TO_COT.get(symbol)

    @classmethod
    def get_cot_name(cls, symbol: str) -> Optional[str]:
        """Get COT commodity name for a Yahoo Finance symbol."""
        info = cls.SYMBOL_TO_COT.get(symbol)
        return info["name"] if info else None

    @classmethod
    def get_exchange(cls, symbol: str) -> Optional[str]:
        """Get exchange for a Yahoo Finance symbol."""
        info = cls.SYMBOL_TO_COT.get(symbol)
        return info["exchange"] if info else None

    @classmethod
    def get_group(cls, symbol: str) -> Optional[str]:
        """Get commodity group for a Yahoo Finance symbol."""
        info = cls.SYMBOL_TO_COT.get(symbol)
        return info["group"] if info else None

    @classmethod
    def get_supported_symbols(cls) -> List[str]:
        """Get list of all supported Yahoo Finance symbols."""
        return list(cls.SYMBOL_TO_COT.keys())

    @classmethod
    def get_symbols_by_group(cls, group: str) -> List[str]:
        """Get all symbols for a specific commodity group."""
        return [
            symbol for symbol, info in cls.SYMBOL_TO_COT.items()
            if info["group"] == group
        ]

    @classmethod
    def get_all_groups(cls) -> List[str]:
        """Get list of all commodity groups."""
        groups = set(info["group"] for info in cls.SYMBOL_TO_COT.values())
        return sorted(list(groups))

    @classmethod
    def is_supported(cls, symbol: str) -> bool:
        """Check if a symbol is supported for COT analysis."""
        return symbol in cls.SYMBOL_TO_COT

    @classmethod
    def search_by_name(cls, search_term: str) -> List[str]:
        """Search for symbols by commodity name."""
        search_lower = search_term.lower()
        matches = []

        for symbol, info in cls.SYMBOL_TO_COT.items():
            # Check main name
            if search_lower in info["name"].lower():
                matches.append(symbol)
                continue

            # Check alternative names
            alt_names = cls.ALTERNATIVE_NAMES.get(info["name"], [])
            for alt_name in alt_names:
                if search_lower in alt_name.lower():
                    matches.append(symbol)
                    break

        return matches
