import uuid
from datetime import datetime, timedelta, timezone
from ipaddress import IPv4Address
from math import floor
from typing import Any

import pytest

from linkurator_core.domain.users.session import Session
from linkurator_core.domain.users.session_repository import SessionRepository
from linkurator_core.infrastructure.mongodb.session_repository import (
    MongoDBSessionRepository,
)
from linkurator_core.infrastructure.mongodb.session_repository import TokenAlreadyExists as MongoTokenAlreadyExists
from linkurator_core.infrastructure.postgres.session_repository import (
    PostgresSessionRepository,
)
from linkurator_core.infrastructure.postgres.session_repository import TokenAlreadyExists as PostgresTokenAlreadyExists


@pytest.fixture(name="session_repo", scope="session", params=["mongodb", "postgresql"])
def fixture_session_repo(db_name: str, request: Any) -> SessionRepository:
    if request.param == "postgresql":
        return PostgresSessionRepository(IPv4Address("127.0.0.1"), 5432, db_name, "develop", "develop")
    return MongoDBSessionRepository(IPv4Address("127.0.0.1"), 27017, db_name, "develop", "develop")


def test_get_session_by_token(session_repo: SessionRepository) -> None:
    session = Session(
        token="test_token_1",
        user_id=uuid.UUID("4bf64498-239e-4bcb-a5a1-b84a7708ad01"),
        expires_at=datetime.now(tz=timezone.utc) + timedelta(days=1),
    )

    session_repo.add(session)
    the_session = session_repo.get(session.token)

    assert the_session is not None
    assert the_session.token == session.token
    assert the_session.user_id == session.user_id
    assert int(the_session.expires_at.timestamp() * 100) == floor(session.expires_at.timestamp() * 100)


def test_get_session_by_token_not_found(session_repo: SessionRepository) -> None:
    the_session = session_repo.get("not_found")

    assert the_session is None


def test_delete_session(session_repo: SessionRepository) -> None:
    session = Session(
        token="test_token_2",
        user_id=uuid.UUID("6e57581d-1046-4001-9c07-7de9fc19afa5"),
        expires_at=datetime.now(tz=timezone.utc) + timedelta(days=1),
    )

    session_repo.add(session)
    the_session = session_repo.get(session.token)

    assert the_session is not None
    assert the_session.token == session.token

    session_repo.delete(session.token)
    deleted_session = session_repo.get(session.token)
    assert deleted_session is None


def test_two_sessions_with_the_same_token_returns_an_error(session_repo: SessionRepository) -> None:
    session = Session(
        token="test_token_3",
        user_id=uuid.UUID("6e57581d-1046-4001-9c07-7de9fc19afa5"),
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )

    session_repo.add(session)
    the_session = session_repo.get(session.token)

    assert the_session is not None
    assert the_session.token == session.token

    with pytest.raises((MongoTokenAlreadyExists, PostgresTokenAlreadyExists)):
        session_repo.add(session)
