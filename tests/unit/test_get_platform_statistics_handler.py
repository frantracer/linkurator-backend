from datetime import datetime, timezone, timedelta

import pytest

from linkurator_core.application.statistics.get_platform_statistics import GetPlatformStatisticsHandler
from linkurator_core.domain.common.mock_factory import mock_user
from linkurator_core.infrastructure.in_memory.user_repository import InMemoryUserRepository


@pytest.mark.asyncio
async def test_get_platform_statistics_handler() -> None:
    # Given
    user_repository = InMemoryUserRepository()
    user1 = mock_user()
    user1.last_login_at = datetime.now(timezone.utc) - timedelta(days=29)
    user2 = mock_user()
    user2.last_login_at = datetime.now(timezone.utc) - timedelta(days=31)
    await user_repository.add(user1)
    await user_repository.add(user2)

    handler = GetPlatformStatisticsHandler(user_repository)

    # When
    statistics = await handler.handle()

    # Then
    assert statistics.registered_users == 2
    assert statistics.active_users == 1
