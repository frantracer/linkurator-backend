from uuid import UUID

import pytest

from linkurator_core.application.users.get_curators_handler import GetCuratorsHandler
from linkurator_core.domain.common.mock_factory import mock_user
from linkurator_core.domain.users.user import Username
from linkurator_core.infrastructure.in_memory.user_repository import InMemoryUserRepository


@pytest.mark.asyncio()
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


@pytest.mark.asyncio()
async def test_get_not_existing_curator_returns_nothing() -> None:
    user_repository = InMemoryUserRepository()
    user = mock_user(curators={UUID("141f3f1c-2b0f-4d88-aa8e-9d6165200091")})

    await user_repository.add(user)

    handler = GetCuratorsHandler(user_repository)

    curators = await handler.handle(user.uuid)

    assert len(curators) == 0


@pytest.mark.asyncio()
async def test_search_curators_by_partial_username() -> None:
    user_repository = InMemoryUserRepository()
    john_doe = mock_user(username=Username("john_doe"))
    jane_smith = mock_user(username=Username("jane_smith"))
    johnny_walker = mock_user(username=Username("johnny_walker"))
    bob_jones = mock_user(username=Username("bob_jones"))

    await user_repository.add(john_doe)
    await user_repository.add(jane_smith)
    await user_repository.add(johnny_walker)
    await user_repository.add(bob_jones)

    handler = GetCuratorsHandler(user_repository)

    curators = await handler.handle(username="john")

    assert len(curators) == 2
    assert john_doe in curators
    assert johnny_walker in curators
    assert jane_smith not in curators
    assert bob_jones not in curators


@pytest.mark.asyncio()
async def test_search_curators_by_partial_username_case_insensitive() -> None:
    user_repository = InMemoryUserRepository()
    john_doe = mock_user(username=Username("john_doe"))
    jane_smith = mock_user(username=Username("jane_smith"))

    await user_repository.add(john_doe)
    await user_repository.add(jane_smith)

    handler = GetCuratorsHandler(user_repository)

    curators = await handler.handle(username="JOHN")

    assert len(curators) == 1
    assert john_doe in curators
    assert jane_smith not in curators


@pytest.mark.asyncio()
async def test_search_curators_by_non_existing_username() -> None:
    user_repository = InMemoryUserRepository()
    john_doe = mock_user(username=Username("john_doe"))

    await user_repository.add(john_doe)

    handler = GetCuratorsHandler(user_repository)

    curators = await handler.handle(username="xyz")

    assert len(curators) == 0


@pytest.mark.asyncio()
async def test_get_followed_curators_filtered_by_username() -> None:
    user_repository = InMemoryUserRepository()
    john_doe = mock_user(username=Username("john_doe"))
    jane_smith = mock_user(username=Username("jane_smith"))
    johnny_walker = mock_user(username=Username("johnny_walker"))
    user = mock_user(curators={john_doe.uuid, jane_smith.uuid, johnny_walker.uuid})

    await user_repository.add(user)
    await user_repository.add(john_doe)
    await user_repository.add(jane_smith)
    await user_repository.add(johnny_walker)

    handler = GetCuratorsHandler(user_repository)

    curators = await handler.handle(user_id=user.uuid, username="john")

    assert len(curators) == 2
    assert john_doe in curators
    assert johnny_walker in curators
    assert jane_smith not in curators


@pytest.mark.asyncio()
async def test_get_followed_curators_with_empty_username_filter() -> None:
    user_repository = InMemoryUserRepository()
    curator1 = mock_user(username=Username("john_doe"))
    curator2 = mock_user(username=Username("jane_smith"))
    user = mock_user(curators={curator1.uuid, curator2.uuid})

    await user_repository.add(user)
    await user_repository.add(curator1)
    await user_repository.add(curator2)

    handler = GetCuratorsHandler(user_repository)

    curators = await handler.handle(user_id=user.uuid, username="")

    assert len(curators) == 2
    assert curator1 in curators
    assert curator2 in curators


@pytest.mark.asyncio()
async def test_get_curators_with_no_parameters_returns_empty() -> None:
    user_repository = InMemoryUserRepository()
    john_doe = mock_user(username=Username("john_doe"))

    await user_repository.add(john_doe)

    handler = GetCuratorsHandler(user_repository)

    curators = await handler.handle()

    assert len(curators) == 0
