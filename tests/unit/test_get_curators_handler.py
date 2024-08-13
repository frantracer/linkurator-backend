from uuid import UUID

import pytest

from linkurator_core.application.users.get_curators_handler import GetCuratorsHandler
from linkurator_core.domain.common.mock_factory import mock_user
from linkurator_core.infrastructure.in_memory.user_repository import InMemoryUserRepository


@pytest.mark.asyncio
async def test_get_curators_handler() -> None:
    user_repository = InMemoryUserRepository()
    curator1 = mock_user()
    curator2 = mock_user()
    user = mock_user(curators={curator1.uuid, curator2.uuid})

    await user_repository.add(user)
    await user_repository.add(curator1)
    await user_repository.add(curator2)

    handler = GetCuratorsHandler(user_repository)

    curators = await handler.handle(user.uuid)

    assert len(curators) == 2
    assert curator1 in curators
    assert curator2 in curators


@pytest.mark.asyncio
async def test_get_not_existing_curator_returns_nothing() -> None:
    user_repository = InMemoryUserRepository()
    user = mock_user(curators={UUID("141f3f1c-2b0f-4d88-aa8e-9d6165200091")})

    await user_repository.add(user)

    handler = GetCuratorsHandler(user_repository)

    curators = await handler.handle(user.uuid)

    assert len(curators) == 0
