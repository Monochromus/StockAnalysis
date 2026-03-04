"""
CFTC COT Data Client.
Fetches Commitments of Traders data from the CFTC Socrata API.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import httpx
import pandas as pd

from .mappings import COTMapping

logger = logging.getLogger(__name__)


class COTClient:
    """Client for fetching COT data from CFTC Socrata API."""

    # CFTC Socrata API endpoints
    BASE_URL = "https://publicreporting.cftc.gov/resource"

    # Dataset IDs
    DATASETS = {
        "legacy_futures": "6dca-aqww",      # Legacy Futures Only
        "legacy_combined": "jun7-fc8e",      # Legacy Futures + Options
        "disaggregated_futures": "72hh-3qpy",  # Disaggregated Futures Only
        "tff_futures": "gpe5-46if",          # Traders in Financial Futures
    }

    # Column mappings from CFTC API to our schema
    LEGACY_COLUMNS = {
        "report_date_as_yyyy_mm_dd": "report_date",
        "open_interest_all": "open_interest",
        "noncomm_positions_long_all": "noncommercial_long",
        "noncomm_positions_short_all": "noncommercial_short",
        "noncomm_positions_spreading_all": "noncommercial_spreading",
        "comm_positions_long_all": "commercial_long",
        "comm_positions_short_all": "commercial_short",
        "tot_rept_positions_long_all": "total_reportable_long",
        "tot_rept_positions_short_all": "total_reportable_short",
        "nonrept_positions_long_all": "nonreportable_long",
        "nonrept_positions_short_all": "nonreportable_short",
        "market_and_exchange_names": "market_exchange",
        "contract_market_name": "contract_name",
        "cftc_contract_market_code": "contract_code",
    }

    def __init__(
        self,
        app_token: Optional[str] = None,
        timeout: float = 30.0
    ):
        """
        Initialize the COT client.

        Args:
            app_token: Optional Socrata app token for higher rate limits
            timeout: Request timeout in seconds
        """
        self.app_token = app_token
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    def _build_url(self, dataset_id: str) -> str:
        """Build API URL for a dataset."""
        return f"{self.BASE_URL}/{dataset_id}.json"

    def _build_headers(self) -> Dict[str, str]:
        """Build request headers."""
        headers = {"Accept": "application/json"}
        if self.app_token:
            headers["X-App-Token"] = self.app_token
        return headers

    def _fetch_data(
        self,
        dataset_id: str,
        commodity_name: str,
        limit: int = 260,  # ~5 years of weekly data
        order: str = "report_date_as_yyyy_mm_dd DESC"
    ) -> List[Dict[str, Any]]:
        """
        Fetch COT data from CFTC API.

        Args:
            dataset_id: CFTC dataset ID
            commodity_name: Commodity name to filter by
            limit: Maximum number of records
            order: Sort order

        Returns:
            List of raw COT records
        """
        url = self._build_url(dataset_id)
        headers = self._build_headers()

        # Build SoQL query - search in contract name
        # Use UPPER for case-insensitive matching
        where_clause = f"UPPER(contract_market_name) like UPPER('%{commodity_name}%')"

        params = {
            "$where": where_clause,
            "$limit": str(limit),
            "$order": order,
        }

        try:
            response = self._client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            if not data:
                logger.warning(f"No COT data found for: {commodity_name}")
                return []

            logger.debug(f"Fetched {len(data)} COT records for {commodity_name}")
            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching COT data: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error fetching COT data: {e}")
            raise

    def _parse_legacy_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a legacy COT record into our schema."""
        parsed = {}

        for api_col, our_col in self.LEGACY_COLUMNS.items():
            value = record.get(api_col)
            if value is not None:
                # Convert numeric strings to integers
                if our_col not in ("report_date", "market_exchange", "contract_name", "contract_code"):
                    try:
                        parsed[our_col] = int(float(value))
                    except (ValueError, TypeError):
                        parsed[our_col] = value
                else:
                    parsed[our_col] = value

        # Calculate net positions
        if "commercial_long" in parsed and "commercial_short" in parsed:
            parsed["commercial_net"] = parsed["commercial_long"] - parsed["commercial_short"]

        if "noncommercial_long" in parsed and "noncommercial_short" in parsed:
            parsed["noncommercial_net"] = parsed["noncommercial_long"] - parsed["noncommercial_short"]

        if "nonreportable_long" in parsed and "nonreportable_short" in parsed:
            parsed["nonreportable_net"] = parsed["nonreportable_long"] - parsed["nonreportable_short"]

        # Calculate percentages of open interest
        oi = parsed.get("open_interest", 0)
        if oi > 0:
            comm_total = parsed.get("commercial_long", 0) + parsed.get("commercial_short", 0)
            noncomm_total = parsed.get("noncommercial_long", 0) + parsed.get("noncommercial_short", 0)
            parsed["commercial_pct_oi"] = round((comm_total / 2) / oi * 100, 2)
            parsed["noncommercial_pct_oi"] = round((noncomm_total / 2) / oi * 100, 2)
        else:
            parsed["commercial_pct_oi"] = 0.0
            parsed["noncommercial_pct_oi"] = 0.0

        return parsed

    def get_legacy_futures(
        self,
        symbol: str,
        weeks: int = 52
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get legacy futures COT data for a symbol.

        Args:
            symbol: Yahoo Finance symbol (e.g., "GC=F")
            weeks: Number of weeks of history

        Returns:
            List of parsed COT records or None if not found
        """
        commodity_name = COTMapping.get_cot_name(symbol)
        if not commodity_name:
            logger.warning(f"No COT mapping for symbol: {symbol}")
            return None

        try:
            raw_data = self._fetch_data(
                self.DATASETS["legacy_futures"],
                commodity_name,
                limit=weeks + 10  # Extra buffer for filtering
            )

            if not raw_data:
                return None

            # Parse and filter
            parsed = []
            for record in raw_data:
                parsed_record = self._parse_legacy_record(record)
                if parsed_record.get("report_date"):
                    parsed.append(parsed_record)

            # Sort by date descending and limit
            parsed.sort(key=lambda x: x["report_date"], reverse=True)
            return parsed[:weeks]

        except Exception as e:
            logger.error(f"Error fetching legacy COT data for {symbol}: {e}")
            raise

    def get_latest_report_date(self) -> Optional[str]:
        """
        Get the date of the most recent COT report.

        Returns:
            Date string in YYYY-MM-DD format or None
        """
        url = self._build_url(self.DATASETS["legacy_futures"])
        headers = self._build_headers()

        params = {
            "$select": "report_date_as_yyyy_mm_dd",
            "$order": "report_date_as_yyyy_mm_dd DESC",
            "$limit": "1",
        }

        try:
            response = self._client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            if data:
                return data[0].get("report_date_as_yyyy_mm_dd")
            return None

        except Exception as e:
            logger.error(f"Error fetching latest report date: {e}")
            return None

    def get_available_commodities(self) -> List[Dict[str, str]]:
        """
        Get list of available commodities in COT reports.

        Returns:
            List of dicts with commodity name and exchange
        """
        url = self._build_url(self.DATASETS["legacy_futures"])
        headers = self._build_headers()

        params = {
            "$select": "contract_market_name, market_and_exchange_names",
            "$group": "contract_market_name, market_and_exchange_names",
            "$order": "contract_market_name ASC",
        }

        try:
            response = self._client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            return [
                {
                    "name": record.get("contract_market_name", ""),
                    "exchange": record.get("market_and_exchange_names", ""),
                }
                for record in data
            ]

        except Exception as e:
            logger.error(f"Error fetching available commodities: {e}")
            return []

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
