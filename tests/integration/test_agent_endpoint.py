import uuid
from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from starlette import status

from linkurator_core.application.agents.query_agent_handler import QueryAgentHandler
from linkurator_core.application.auth.validate_session_token import ValidateTokenHandler
from linkurator_core.domain.agents.query_agent_service import AgentQueryResult
from linkurator_core.domain.users.session import Session
from linkurator_core.infrastructure.fastapi.create_app import Handlers, create_app_from_handlers

USER_UUID = uuid.UUID("8efe1fe3-906d-4aa4-8fbe-b47810c197d8")


@pytest.fixture(name="query_agent_handler")
def query_agent_handler_fixture() -> QueryAgentHandler:
    mock_handler = AsyncMock(spec=QueryAgentHandler)
    mock_result = AgentQueryResult(
        message="Here's what I found!",
        items=[uuid.uuid4(), uuid.uuid4()],
        topics=[uuid.uuid4()],
        subscriptions=[uuid.uuid4(), uuid.uuid4()],
    )
    mock_handler.handle.return_value = mock_result
    return mock_handler


@pytest.fixture(name="handlers")
def dummy_handlers(query_agent_handler: QueryAgentHandler) -> Handlers:
    dummy_validate_token_handler = AsyncMock(spec=ValidateTokenHandler)
    dummy_validate_token_handler.handle.return_value = Session(
        user_id=USER_UUID,
        expires_at=datetime.fromisoformat("3000-01-01T00:00:00+00:00"),
        token="token",
    )

    return Handlers(
        validate_token=dummy_validate_token_handler,
        validate_user_password=AsyncMock(),
        register_user_with_email=AsyncMock(),
        register_user_with_google=AsyncMock(),
        validate_new_user_request=AsyncMock(),
        request_password_change=AsyncMock(),
        change_password_from_request=AsyncMock(),
        google_client=AsyncMock(),
        google_youtube_client=AsyncMock(),
        get_subscription=AsyncMock(),
        get_user_subscriptions=AsyncMock(),
        find_subscriptions_by_name_handler=AsyncMock(),
        follow_subscription_handler=AsyncMock(),
        unfollow_subscription_handler=AsyncMock(),
        get_subscription_items_handler=AsyncMock(),
        delete_subscription_items_handler=AsyncMock(),
        refresh_subscription_handler=AsyncMock(),
        get_user_profile_handler=AsyncMock(),
        edit_user_profile_handler=AsyncMock(),
        find_user_handler=AsyncMock(),
        delete_user_handler=AsyncMock(),
        get_curators_handler=AsyncMock(),
        follow_curator_handler=AsyncMock(),
        unfollow_curator_handler=AsyncMock(),
        get_topic_handler=AsyncMock(),
        get_topic_items_handler=AsyncMock(),
        get_user_topics_handler=AsyncMock(),
        find_topics_by_name_handler=AsyncMock(),
        get_curator_topics_handler=AsyncMock(),
        get_curator_items_handler=AsyncMock(),
        create_topic_handler=AsyncMock(),
        assign_subscription_to_topic_handler=AsyncMock(),
        delete_topic_handler=AsyncMock(),
        unassign_subscription_from_topic_handler=AsyncMock(),
        update_topic_handler=AsyncMock(),
        get_item_handler=AsyncMock(),
        create_item_interaction_handler=AsyncMock(),
        delete_item_interaction_handler=AsyncMock(),
        get_user_external_credentials_handler=AsyncMock(),
        add_external_credentials_handler=AsyncMock(),
        delete_external_credential_handler=AsyncMock(),
        follow_topic_handler=AsyncMock(),
        unfollow_topic_handler=AsyncMock(),
        favorite_topic_handler=AsyncMock(),
        unfavorite_topic_handler=AsyncMock(),
        get_platform_statistics=AsyncMock(),
        update_user_subscriptions_handler=AsyncMock(),
        query_agent_handler=query_agent_handler,
    )


def test_query_agent_endpoint_returns_200(handlers: Handlers) -> None:
    client = TestClient(create_app_from_handlers(handlers))

    response = client.post(
        "/agent/query",
        json={"query": "What should I watch today?"},
        cookies={"token": "valid_token"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "message" in data
    assert "items" in data
    assert "topics" in data
    assert "subscriptions" in data
    assert isinstance(data["items"], list)
    assert isinstance(data["topics"], list)
    assert isinstance(data["subscriptions"], list)


def test_query_agent_endpoint_requires_authentication(handlers: Handlers) -> None:
    client = TestClient(create_app_from_handlers(handlers))

    response = client.post(
        "/agent/query",
        json={"query": "What should I watch today?"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_query_agent_endpoint_validates_request_body(handlers: Handlers) -> None:
    client = TestClient(create_app_from_handlers(handlers))

    response = client.post(
        "/agent/query",
        json={},  # Missing required query field
        cookies={"token": "valid_token"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
