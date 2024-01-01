from datetime import datetime, timezone, timedelta
from ipaddress import IPv4Address
import uuid

from math import floor
import pytest

from linkurator_core.domain.users.session import Session
from linkurator_core.infrastructure.mongodb.session_repository import MongoDBSessionRepository, TokenAlreadyExists


@pytest.fixture(name="session_repo", scope="session")
def fixture_session_repo(db_name: str) -> MongoDBSessionRepository:
    return MongoDBSessionRepository(IPv4Address('127.0.0.1'), 27017, db_name, "develop", "develop")


def test_get_session_by_token(session_repo: MongoDBSessionRepository) -> None:
    session = Session(
        token="test_token_1",
        user_id=uuid.UUID("4bf64498-239e-4bcb-a5a1-b84a7708ad01"),
        expires_at=datetime.now(tz=timezone.utc) + timedelta(days=1)
    )

    session_repo.add(session)
    the_session = session_repo.get(session.token)

    assert the_session is not None
    assert the_session.token == session.token
    assert the_session.user_id == session.user_id
    assert int(the_session.expires_at.timestamp() * 100) == floor(session.expires_at.timestamp() * 100)


def test_get_session_by_token_not_found(session_repo: MongoDBSessionRepository) -> None:
    the_session = session_repo.get("not_found")

    assert the_session is None


def test_delete_session(session_repo: MongoDBSessionRepository) -> None:
    session = Session(
        token="test_token_2",
        user_id=uuid.UUID("6e57581d-1046-4001-9c07-7de9fc19afa5"),
        expires_at=datetime.now(tz=timezone.utc) + timedelta(days=1)
    )

    session_repo.add(session)
    the_session = session_repo.get(session.token)

    assert the_session is not None
    assert the_session.token == session.token

    session_repo.delete(session.token)
    deleted_session = session_repo.get(session.token)
    assert deleted_session is None


def test_two_sessions_with_the_same_token_returns_an_error(session_repo: MongoDBSessionRepository) -> None:
    session = Session(
        token="test_token_3",
        user_id=uuid.UUID("6e57581d-1046-4001-9c07-7de9fc19afa5"),
        expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )

    session_repo.add(session)
    the_session = session_repo.get(session.token)

    assert the_session is not None
    assert the_session.token == session.token

    with pytest.raises(TokenAlreadyExists):
        session_repo.add(session)
