from datetime import datetime, timedelta
from typing import Callable, Dict, List

from linkurator_core.domain.common.utils import datetime_now


class AnonymousUserRateLimiter:
    """Rate limiter for anonymous users based on request timestamps."""

    def __init__(
        self,
        max_requests: int = 2,
        window_minutes: int = 5,
        datetime_now_func: Callable[[], datetime] = datetime_now,
    ) -> None:
        self.max_requests = max_requests
        self.window_minutes = window_minutes
        self.datetime_now_func = datetime_now_func
        self._request_history: Dict[str, List[datetime]] = {}

    def is_rate_limit_exceeded(self, identifier: str) -> bool:
        """
        Check if the rate limit is exceeded for the given identifier.

        Args:
        ----
            identifier: A unique identifier for the anonymous user (e.g., IP address, session ID)

        Returns:
        -------
            True if rate limit is exceeded, False otherwise

        """
        now = self.datetime_now_func()
        cutoff_time = now - timedelta(minutes=self.window_minutes)

        # Get or create request history for this identifier
        if identifier not in self._request_history:
            self._request_history[identifier] = []

        request_times = self._request_history[identifier]

        # Remove requests outside the time window
        request_times[:] = [req_time for req_time in request_times if req_time > cutoff_time]

        # Check if adding this request would exceed the limit
        if len(request_times) >= self.max_requests:
            return True

        # Record this request
        request_times.append(now)
        return False
