"""
SQLite-based cache for news analysis results.
Provides persistence and TTL-based expiration.
"""

import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from threading import Lock

logger = logging.getLogger(__name__)


class NewsCache:
    """
    SQLite-based cache for Gemini news analysis results.
    Thread-safe with connection pooling.
    """

    def __init__(self, db_path: str = "data/news_cache.db", ttl_seconds: int = 14400):
        """
        Initialize the cache.

        Args:
            db_path: Path to SQLite database file
            ttl_seconds: Time-to-live in seconds (default: 4 hours)
        """
        self.db_path = db_path
        self.ttl_seconds = ttl_seconds
        self._lock = Lock()

        # Ensure data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Initialize database
        self._init_db()

    def _init_db(self):
        """Initialize the database schema."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS news_cache (
                    symbol TEXT PRIMARY KEY,
                    analysis_json TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def get(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get cached analysis for a symbol.

        Args:
            symbol: Commodity symbol (e.g., "GC=F")

        Returns:
            Cached analysis dict or None if not found/expired
        """
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.execute(
                        "SELECT analysis_json, timestamp, expires_at FROM news_cache WHERE symbol = ?",
                        (symbol,)
                    )
                    row = cursor.fetchone()

                    if not row:
                        return None

                    analysis_json, timestamp, expires_at = row

                    # Check expiration
                    expires_dt = datetime.fromisoformat(expires_at)
                    if datetime.utcnow() > expires_dt:
                        # Cache expired, delete entry
                        conn.execute("DELETE FROM news_cache WHERE symbol = ?", (symbol,))
                        conn.commit()
                        logger.info(f"Cache expired for {symbol}")
                        return None

                    # Parse and return
                    analysis = json.loads(analysis_json)
                    analysis["from_cache"] = True
                    analysis["cache_timestamp"] = timestamp

                    logger.info(f"Cache hit for {symbol}")
                    return analysis

            except Exception as e:
                logger.error(f"Error reading cache for {symbol}: {e}")
                return None

    def set(self, symbol: str, analysis: Dict[str, Any]) -> bool:
        """
        Store analysis in cache.

        Args:
            symbol: Commodity symbol
            analysis: Analysis dict to cache

        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            try:
                now = datetime.utcnow()
                expires_at = now + timedelta(seconds=self.ttl_seconds)

                # Remove cache metadata before storing
                analysis_to_store = {k: v for k, v in analysis.items()
                                    if k not in ("from_cache", "cache_timestamp")}

                with self._get_connection() as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO news_cache (symbol, analysis_json, timestamp, expires_at)
                        VALUES (?, ?, ?, ?)
                    """, (
                        symbol,
                        json.dumps(analysis_to_store),
                        now.isoformat(),
                        expires_at.isoformat()
                    ))
                    conn.commit()

                logger.info(f"Cached analysis for {symbol}, expires at {expires_at}")
                return True

            except Exception as e:
                logger.error(f"Error caching analysis for {symbol}: {e}")
                return False

    def invalidate(self, symbol: str) -> bool:
        """
        Invalidate cache for a specific symbol.

        Args:
            symbol: Commodity symbol

        Returns:
            True if entry was deleted, False otherwise
        """
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.execute(
                        "DELETE FROM news_cache WHERE symbol = ?",
                        (symbol,)
                    )
                    conn.commit()
                    deleted = cursor.rowcount > 0

                    if deleted:
                        logger.info(f"Invalidated cache for {symbol}")
                    return deleted

            except Exception as e:
                logger.error(f"Error invalidating cache for {symbol}: {e}")
                return False

    def clear(self) -> int:
        """
        Clear all cached entries.

        Returns:
            Number of entries deleted
        """
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.execute("DELETE FROM news_cache")
                    conn.commit()
                    count = cursor.rowcount

                    logger.info(f"Cleared {count} entries from news cache")
                    return count

            except Exception as e:
                logger.error(f"Error clearing cache: {e}")
                return 0

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats
        """
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.execute("SELECT COUNT(*) FROM news_cache")
                    total = cursor.fetchone()[0]

                    cursor = conn.execute(
                        "SELECT COUNT(*) FROM news_cache WHERE expires_at > ?",
                        (datetime.utcnow().isoformat(),)
                    )
                    valid = cursor.fetchone()[0]

                    return {
                        "total_entries": total,
                        "valid_entries": valid,
                        "expired_entries": total - valid,
                        "ttl_seconds": self.ttl_seconds,
                    }

            except Exception as e:
                logger.error(f"Error getting cache stats: {e}")
                return {"error": str(e)}
