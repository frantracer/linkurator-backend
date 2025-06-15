import pytest

from linkurator_core.application.users.find_user_handler import FindCuratorHandler
from linkurator_core.domain.common.mock_factory import mock_user
from linkurator_core.domain.users.user import Username
from linkurator_core.infrastructure.in_memory.user_repository import InMemoryUserRepository


@pytest.mark.asyncio()
async def test_find_existing_followed_curator_returns_curator_and_followed_flag() -> None:
    curator = mock_user()
    user = mock_user(curators={curator.uuid})
    user_repo = InMemoryUserRepository()
    await user_repo.add(user)
    await user_repo.add(curator)

    handler = FindCuratorHandler(user_repo)

    response = await handler.handle(curator.username, user.uuid)

    assert response.user == curator
    assert response.followed is True


@pytest.mark.asyncio()
async def test_find_existing_unfollowed_curator_returns_curator_and_unfollowed_flag() -> None:
    curator = mock_user()
    user = mock_user()
    user_repo = InMemoryUserRepository()
    await user_repo.add(user)
    await user_repo.add(curator)

    handler = FindCuratorHandler(user_repo)

    response = await handler.handle(curator.username, user.uuid)

    assert response.user == curator
    assert response.followed is False


@pytest.mark.asyncio()
async def test_find_non_existing_curator_returns_none_and_unfollowed_flag() -> None:
    user = mock_user()
    user_repo = InMemoryUserRepository()
    await user_repo.add(user)

    handler = FindCuratorHandler(user_repo)

    response = await handler.handle(Username("non_existing_curator"), user.uuid)

    assert response.user is None
    assert response.followed is False
