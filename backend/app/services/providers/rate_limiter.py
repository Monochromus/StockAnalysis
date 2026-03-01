"""Thread-safe rate limiter for API providers."""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque


@dataclass
class RateLimiter:
    """Thread-safe rate limiter with per-minute and per-day limits."""

    requests_per_minute: int = 0  # 0 = unlimited
    requests_per_day: int = 0     # 0 = unlimited

    _minute_requests: Deque[float] = field(default_factory=deque)
    _day_requests: Deque[float] = field(default_factory=deque)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def __post_init__(self):
        # Dataclass field default_factory handles initialization correctly
        # No additional initialization needed
        pass

    def _cleanup_old_requests(self, now: float) -> None:
        """Remove old requests from tracking."""
        minute_ago = now - 60
        day_ago = now - 86400

        # Clean minute window
        while self._minute_requests and self._minute_requests[0] < minute_ago:
            self._minute_requests.popleft()

        # Clean day window
        while self._day_requests and self._day_requests[0] < day_ago:
            self._day_requests.popleft()

    def can_request(self) -> bool:
        """Check if a request can be made within rate limits."""
        # If no limits set, always allow
        if self.requests_per_minute == 0 and self.requests_per_day == 0:
            return True

        with self._lock:
            now = time.time()
            self._cleanup_old_requests(now)

            # Check minute limit
            if self.requests_per_minute > 0:
                if len(self._minute_requests) >= self.requests_per_minute:
                    return False

            # Check day limit
            if self.requests_per_day > 0:
                if len(self._day_requests) >= self.requests_per_day:
                    return False

            return True

    def record_request(self) -> None:
        """Record that a request was made."""
        with self._lock:
            now = time.time()
            self._cleanup_old_requests(now)

            if self.requests_per_minute > 0:
                self._minute_requests.append(now)
            if self.requests_per_day > 0:
                self._day_requests.append(now)

    def get_remaining(self) -> dict:
        """Get remaining requests for minute and day windows."""
        with self._lock:
            now = time.time()
            self._cleanup_old_requests(now)

            # Use None for unlimited instead of infinity (not JSON-serializable)
            minute_remaining = (
                self.requests_per_minute - len(self._minute_requests)
                if self.requests_per_minute > 0
                else None
            )
            day_remaining = (
                self.requests_per_day - len(self._day_requests)
                if self.requests_per_day > 0
                else None
            )

            return {
                "minute_remaining": minute_remaining,
                "day_remaining": day_remaining,
                "minute_limit": self.requests_per_minute,
                "day_limit": self.requests_per_day,
            }

    def wait_time_seconds(self) -> float:
        """Get the number of seconds to wait before next request is allowed."""
        if self.can_request():
            return 0.0

        with self._lock:
            now = time.time()

            # If minute limit is hit, wait for oldest request to expire
            if self.requests_per_minute > 0 and self._minute_requests:
                if len(self._minute_requests) >= self.requests_per_minute:
                    oldest = self._minute_requests[0]
                    wait = 60 - (now - oldest)
                    if wait > 0:
                        return wait

            # If day limit is hit, return large wait time
            if self.requests_per_day > 0 and self._day_requests:
                if len(self._day_requests) >= self.requests_per_day:
                    oldest = self._day_requests[0]
                    wait = 86400 - (now - oldest)
                    if wait > 0:
                        return wait

            return 0.0
