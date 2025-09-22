from datetime import datetime, timedelta, timezone

from linkurator_core.infrastructure.rate_limiter import AnonymousUserRateLimiter


def test_rate_limiter_allows_requests_after_time_window() -> None:
    rate_limiter = AnonymousUserRateLimiter(max_requests=2, window_minutes=5)
    identifier = "test_user_3"

    # Mock current time
    base_time = datetime.now(timezone.utc)

    rate_limiter.datetime_now_func = lambda: base_time

    # First 2 requests should be allowed
    assert not rate_limiter.is_rate_limit_exceeded(identifier)
    assert not rate_limiter.is_rate_limit_exceeded(identifier)

    # 3rd request should be blocked
    assert rate_limiter.is_rate_limit_exceeded(identifier)

    # Move time forward beyond the window
    rate_limiter.datetime_now_func = lambda: base_time + timedelta(minutes=6)

    # Should allow requests again
    assert not rate_limiter.is_rate_limit_exceeded(identifier)


def test_rate_limiter_different_identifiers_are_independent() -> None:
    rate_limiter = AnonymousUserRateLimiter(max_requests=2, window_minutes=5)

    # User 1 makes 2 requests
    assert not rate_limiter.is_rate_limit_exceeded("user_1")
    assert not rate_limiter.is_rate_limit_exceeded("user_1")

    # User 1's 3rd request should be blocked
    assert rate_limiter.is_rate_limit_exceeded("user_1")

    # User 2 should still be able to make requests
    assert not rate_limiter.is_rate_limit_exceeded("user_2")
    assert not rate_limiter.is_rate_limit_exceeded("user_2")
