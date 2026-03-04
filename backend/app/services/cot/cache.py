"""
SQLite cache for COT data.
Implements 24-hour TTL with intelligent invalidation based on CFTC release schedule.
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path
import threading

logger = logging.getLogger(__name__)


class COTCache:
    """SQLite-based cache for COT data with TTL support."""

    def __init__(self, db_path: str = "data/cot_cache.db", ttl_seconds: int = 86400):
        """
        Initialize the COT cache.

        Args:
            db_path: Path to SQLite database file
            ttl_seconds: Time-to-live in seconds (default 24 hours)
        """
        self.db_path = db_path
        self.ttl_seconds = ttl_seconds
        self._local = threading.local()
        self._ensure_db_directory()
        self._init_db()

    def _ensure_db_directory(self) -> None:
        """Ensure the database directory exists."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False
            )
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection

    def _init_db(self) -> None:
        """Initialize the database schema."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cot_cache (
                symbol TEXT PRIMARY KEY,
                data_json TEXT NOT NULL,
                report_date TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cot_cache_expires
            ON cot_cache(expires_at)
        """)

        conn.commit()

    def get(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get cached COT data for a symbol.

        Args:
            symbol: Yahoo Finance symbol

        Returns:
            Cached data dict or None if not found/expired
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        now = datetime.utcnow().isoformat()

        cursor.execute("""
            SELECT data_json, report_date, fetched_at
            FROM cot_cache
            WHERE symbol = ? AND expires_at > ?
        """, (symbol, now))

        row = cursor.fetchone()
        if row:
            try:
                data = json.loads(row["data_json"])
                data["from_cache"] = True
                data["cache_timestamp"] = row["fetched_at"]
                return data
            except json.JSONDecodeError:
                logger.error(f"Failed to decode cached data for {symbol}")
                return None

        return None

    def set(
        self,
        symbol: str,
        data: Dict[str, Any],
        report_date: str,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """
        Cache COT data for a symbol.

        Args:
            symbol: Yahoo Finance symbol
            data: COT data to cache
            report_date: Date of the COT report
            ttl_seconds: Optional custom TTL (uses default if not provided)
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        ttl = ttl_seconds or self.ttl_seconds
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=ttl)

        # Remove cache-related fields before storing
        data_to_store = {k: v for k, v in data.items()
                        if k not in ("from_cache", "cache_timestamp")}

        cursor.execute("""
            INSERT OR REPLACE INTO cot_cache
            (symbol, data_json, report_date, fetched_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            symbol,
            json.dumps(data_to_store),
            report_date,
            now.isoformat(),
            expires_at.isoformat()
        ))

        conn.commit()
        logger.debug(f"Cached COT data for {symbol}, expires at {expires_at}")

    def invalidate(self, symbol: str) -> bool:
        """
        Invalidate cached data for a symbol.

        Args:
            symbol: Yahoo Finance symbol

        Returns:
            True if data was invalidated, False if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM cot_cache WHERE symbol = ?", (symbol,))
        conn.commit()

        deleted = cursor.rowcount > 0
        if deleted:
            logger.debug(f"Invalidated cache for {symbol}")

        return deleted

    def invalidate_all(self) -> int:
        """
        Invalidate all cached data.

        Returns:
            Number of entries deleted
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM cot_cache")
        conn.commit()

        deleted = cursor.rowcount
        logger.debug(f"Invalidated {deleted} cache entries")

        return deleted

    def cleanup_expired(self) -> int:
        """
        Remove expired cache entries.

        Returns:
            Number of entries cleaned up
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        now = datetime.utcnow().isoformat()

        cursor.execute("DELETE FROM cot_cache WHERE expires_at <= ?", (now,))
        conn.commit()

        deleted = cursor.rowcount
        if deleted > 0:
            logger.debug(f"Cleaned up {deleted} expired cache entries")

        return deleted

    def get_cache_info(self, symbol: str) -> Optional[Dict[str, str]]:
        """
        Get cache metadata for a symbol.

        Args:
            symbol: Yahoo Finance symbol

        Returns:
            Dict with report_date, fetched_at, expires_at or None
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT report_date, fetched_at, expires_at
            FROM cot_cache
            WHERE symbol = ?
        """, (symbol,))

        row = cursor.fetchone()
        if row:
            return {
                "report_date": row["report_date"],
                "fetched_at": row["fetched_at"],
                "expires_at": row["expires_at"]
            }

        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        conn = self._get_connection()
        cursor = conn.cursor()

        now = datetime.utcnow().isoformat()

        cursor.execute("SELECT COUNT(*) as total FROM cot_cache")
        total = cursor.fetchone()["total"]

        cursor.execute(
            "SELECT COUNT(*) as valid FROM cot_cache WHERE expires_at > ?",
            (now,)
        )
        valid = cursor.fetchone()["valid"]

        cursor.execute("SELECT symbol, report_date FROM cot_cache")
        symbols = {row["symbol"]: row["report_date"] for row in cursor.fetchall()}

        return {
            "total_entries": total,
            "valid_entries": valid,
            "expired_entries": total - valid,
            "cached_symbols": symbols
        }

    def close(self) -> None:
        """Close the database connection."""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None
