import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from starlette.status import HTTP_400_BAD_REQUEST

from linkurator_core.application.auth.validate_session_token import ValidateTokenHandler
from linkurator_core.application.items.get_subscription_items_handler import (
    GetSubscriptionItemsHandler,
    GetSubscriptionItemsResponse,
)
from linkurator_core.application.items.get_topic_items_handler import (
    GetTopicItemsHandler,
    ItemWithInteractionsAndSubscription,
)
from linkurator_core.application.topics.get_topic_handler import GetTopicHandler, GetTopicResponse
from linkurator_core.application.topics.get_user_topics_handler import CuratorTopic, GetUserTopicsHandler
from linkurator_core.application.users.get_user_profile_handler import GetUserProfileHandler
from linkurator_core.domain.common import utils
from linkurator_core.domain.common.exceptions import (
    CannotUnfollowAssignedSubscriptionError,
    SubscriptionNotFoundError,
    TopicNotFoundError,
)
from linkurator_core.domain.common.mock_factory import mock_sub, mock_topic, mock_user
from linkurator_core.domain.items.item import Item
from linkurator_core.domain.items.item_with_interactions import ItemWithInteractions
from linkurator_core.domain.users.session import Session
from linkurator_core.domain.users.user import User, Username
from linkurator_core.infrastructure.fastapi.create_app import Handlers, create_app_from_handlers

USER_UUID = uuid.UUID("8efe1fe3-906d-4aa4-8fbe-b47810c197d8")


@pytest.fixture(name="handlers")
def dummy_handlers() -> Handlers:
    dummy_validate_token_handler = AsyncMock(spec=ValidateTokenHandler)
    dummy_validate_token_handler.handle.return_value = Session(
        user_id=USER_UUID,
        expires_at=datetime.fromisoformat("3000-01-01T00:00:00+00:00"),
        token="token")

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
    )


def test_health_returns_200(handlers: Handlers) -> None:
    client = TestClient(create_app_from_handlers(handlers))

    response = client.get("/health")
    assert response.content == b'"OK"'
    assert response.status_code == 200


def test_user_profile_returns_200(handlers: Handlers) -> None:
    dummy_get_user_profile_handler = AsyncMock(spec=GetUserProfileHandler)
    dummy_get_user_profile_handler.handle.return_value = User(
        uuid=uuid.UUID("cb856f4f-8371-4648-af75-38fb34231092"),
        first_name="first name",
        last_name="last name",
        username=Username("username"),
        email="test@email.com",
        avatar_url=utils.parse_url("https://test.com/avatar.png"),
        locale="en-US",
        updated_at=datetime.fromtimestamp(0, tz=timezone.utc),
        created_at=datetime.fromtimestamp(0, tz=timezone.utc),
        scanned_at=datetime.fromtimestamp(0, tz=timezone.utc),
        last_login_at=datetime.fromtimestamp(0, tz=timezone.utc),
        _subscription_uuids=set(),
        _youtube_subscriptions_uuids=set(),
        _unfollowed_youtube_subscriptions_uuids=set(),
        _followed_topics=set(),
        _favorite_topics=set(),
        google_refresh_token="refresh token",
        is_admin=False,
        curators=set(),
        password_hash=None,
    )
    handlers.get_user_profile_handler = dummy_get_user_profile_handler

    client = TestClient(create_app_from_handlers(handlers), cookies={"token": "token"})

    response = client.get("/profile")
    assert response.status_code == 200
    assert response.json()["uuid"] == "cb856f4f-8371-4648-af75-38fb34231092"
    assert response.json()["first_name"] == "first name"
    assert response.json()["last_name"] == "last name"
    assert response.json()["username"] == "username"
    assert response.json()["email"] == "test@email.com"
    assert response.json()["created_at"] == "1970-01-01T00:00:00+00:00"
    assert response.json()["last_scanned_at"] == "1970-01-01T00:00:00+00:00"


def test_user_profile_returns_404_when_user_not_found(handlers: Handlers) -> None:
    dummy_get_user_profile_handler = AsyncMock(spec=GetUserProfileHandler)
    dummy_get_user_profile_handler.handle.return_value = None
    handlers.get_user_profile_handler = dummy_get_user_profile_handler

    client = TestClient(create_app_from_handlers(handlers), cookies={"token": "token"})

    response = client.get("/profile")
    assert response.status_code == 404


def test_item_pagination_returns_one_page(handlers: Handlers) -> None:
    sub = mock_sub()
    item1 = Item.new(name="item1",
                     description="",
                     uuid=uuid.UUID("ae1b82ee-f870-4a1f-a1c8-898c10ce9eb8"),
                     subscription_uuid=sub.uuid,
                     url=utils.parse_url("https://ae1b82ee.com"),
                     thumbnail=utils.parse_url("https://test.com/thumbnail.png"),
                     published_at=datetime.fromtimestamp(0, tz=timezone.utc))
    dummy_get_subscription_items_handler = AsyncMock(spec=GetSubscriptionItemsHandler)
    dummy_get_subscription_items_handler.handle.return_value = GetSubscriptionItemsResponse(
        items=[ItemWithInteractions(item=item1, interactions=[])], subscription=sub,
    )
    handlers.get_subscription_items_handler = dummy_get_subscription_items_handler

    client = TestClient(create_app_from_handlers(handlers), cookies={"token": "token"})

    response = client.get(f"/subscriptions/{sub.uuid}/items?created_before_ts=777.0&page_number=0&page_size=1")
    assert response.status_code == 200
    assert len(response.json()["elements"]) == 1
    assert response.json()["next_page"] == (
        f"http://testserver/subscriptions/{sub.uuid}/items?"
        "created_before_ts=777.0&page_number=1&page_size=1")
    assert response.json()["previous_page"] is None


def test_get_subscription_items_parses_query_parameters(handlers: Handlers) -> None:
    dummy_handler = AsyncMock(spec=GetSubscriptionItemsHandler)
    dummy_handler.handle.return_value = GetSubscriptionItemsResponse(items=[], subscription=mock_sub())
    handlers.get_subscription_items_handler = dummy_handler

    client = TestClient(create_app_from_handlers(handlers), cookies={"token": "token"})

    client.get(
        "/subscriptions/3e9232e7-fa87-4e14-a642-9df94d619c1a/items?"
        "page_number=0&page_size=1&search=test&created_before_ts=0&"
        "max_duration=100&min_duration=10&"
        "include_interactions=without_interactions,recommended,viewed,hidden,discouraged")
    dummy_handler.handle.assert_called_once_with(
        user_id=USER_UUID,
        subscription_id=uuid.UUID("3e9232e7-fa87-4e14-a642-9df94d619c1a"),
        created_before=datetime.fromtimestamp(0, tz=timezone.utc),
        page_number=0,
        page_size=1,
        text_filter="test",
        min_duration=10,
        max_duration=100,
        include_items_without_interactions=True,
        include_recommended_items=True,
        include_discouraged_items=True,
        include_viewed_items=True,
        include_hidden_items=True)


def test_get_subscription_items_recommended_and_without_interactions(handlers: Handlers) -> None:
    sub = mock_sub()
    dummy_get_subscription_items_handler = AsyncMock(spec=GetSubscriptionItemsHandler)
    dummy_get_subscription_items_handler.handle.return_value = GetSubscriptionItemsResponse(
        items=[], subscription=sub,
    )
    handlers.get_subscription_items_handler = dummy_get_subscription_items_handler

    client = TestClient(create_app_from_handlers(handlers), cookies={"token": "token"})

    client.get(
        f"/subscriptions/{sub.uuid}/items?"
        "page_number=0&page_size=1&search=test&created_before_ts=0&"
        "include_interactions=without_interactions,recommended")
    dummy_get_subscription_items_handler.handle.assert_called_once_with(
        user_id=USER_UUID,
        subscription_id=sub.uuid,
        created_before=datetime.fromtimestamp(0, tz=timezone.utc),
        page_number=0,
        page_size=1,
        text_filter="test",
        min_duration=None,
        max_duration=None,
        include_items_without_interactions=True,
        include_recommended_items=True,
        include_discouraged_items=False,
        include_viewed_items=False,
        include_hidden_items=False)


def test_create_user_topic_returns_201(handlers: Handlers) -> None:
    client = TestClient(create_app_from_handlers(handlers), cookies={"token": "token"})

    response = client.post(
        "/topics/",
        json={
            "uuid": "ae1b82ee-f870-4a1f-a1c8-898c10ce9eb8",
            "name": "topic1",
            "subscriptions_ids": [],
        })
    assert response.status_code == 201
    assert response.content == b""


def test_delete_topic_returns_204(handlers: Handlers) -> None:
    client = TestClient(create_app_from_handlers(handlers), cookies={"token": "token"})

    response = client.delete("/topics/ae1b82ee-f870-4a1f-a1c8-898c10ce9eb8")
    assert response.status_code == 204
    assert response.content == b""


def test_delete_non_existing_topic_returns_404(handlers: Handlers) -> None:
    dummy_handler = AsyncMock()
    dummy_handler.handle.side_effect = TopicNotFoundError
    handlers.delete_topic_handler = dummy_handler
    client = TestClient(create_app_from_handlers(handlers), cookies={"token": "token"})

    response = client.delete("/topics/ae1b82ee-f870-4a1f-a1c8-898c10ce9eb8")
    assert response.status_code == 404


def test_get_topics_returns_200(handlers: Handlers) -> None:
    curator = mock_user(uuid=uuid.UUID("24060726-9ee6-450e-bec2-0edf8e7b33b2"))

    topic = mock_topic(
        uuid=uuid.UUID("f22b92da-5b90-455f-8141-fb4a37f07805"),
        name="topic1",
        user_uuid=curator.uuid,
    )
    handlers.get_user_topics_handler = AsyncMock(spec=GetUserTopicsHandler)
    handlers.get_user_topics_handler.handle.return_value = [CuratorTopic(topic=topic, curator=curator)]

    handlers.get_user_profile_handler = AsyncMock(spec=GetUserProfileHandler)
    handlers.get_user_profile_handler.handle.return_value = None

    client = TestClient(create_app_from_handlers(handlers), cookies={"token": "token"})

    response = client.get("/topics")
    assert response.status_code == 200
    assert len(response.json()["elements"]) == 1
    assert response.json()["next_page"] is None
    assert response.json()["previous_page"] is None


def test_get_topic_returns_200(handlers: Handlers) -> None:
    curator = mock_user(uuid=uuid.UUID("f5b11947-0203-45b5-9c55-f3bd391ed150"))
    topic = mock_topic(
        uuid=uuid.UUID("f8be01d6-98b3-4ba7-a540-d2f008d1adbc"),
        name="topic1",
        user_uuid=curator.uuid,
        subscription_uuids=[uuid.UUID("00ff1b4a-aeed-4321-8e40-53e78c13685d")],
    )
    handlers.get_topic_handler = AsyncMock(spec=GetTopicHandler)
    handlers.get_topic_handler.handle.return_value = GetTopicResponse(topic=topic, curator=curator)

    handlers.get_user_profile_handler = AsyncMock(spec=GetUserProfileHandler)
    handlers.get_user_profile_handler.handle.return_value = None

    client = TestClient(create_app_from_handlers(handlers), cookies={"token": "token"})

    response = client.get("/topics/f8be01d6-98b3-4ba7-a540-d2f008d1adbc")
    assert response.status_code == 200
    assert response.json()["uuid"] == "f8be01d6-98b3-4ba7-a540-d2f008d1adbc"
    assert response.json()["name"] == "topic1"
    assert response.json()["user_id"] == "f5b11947-0203-45b5-9c55-f3bd391ed150"
    assert response.json()["subscriptions_ids"] == ["00ff1b4a-aeed-4321-8e40-53e78c13685d"]
    assert response.json()["followed"] is False


def test_get_followed_topic_returns_200(handlers: Handlers) -> None:
    curator = mock_user()
    topic = mock_topic(user_uuid=curator.uuid)
    user = mock_user(topics={topic.uuid})

    handlers.get_topic_handler = AsyncMock(spec=GetTopicHandler)
    handlers.get_topic_handler.handle.return_value = GetTopicResponse(topic=topic, curator=curator)

    handlers.get_user_profile_handler = AsyncMock(spec=GetUserProfileHandler)
    handlers.get_user_profile_handler.handle.return_value = user

    client = TestClient(create_app_from_handlers(handlers), cookies={"token": "token"})

    response = client.get("/topics/f8be01d6-98b3-4ba7-a540-d2f008d1adbc")
    assert response.status_code == 200
    assert response.json()["followed"] is True


def test_get_topic_returns_404_when_topic_not_found(handlers: Handlers) -> None:
    dummy_handler = AsyncMock()
    dummy_handler.handle.side_effect = TopicNotFoundError
    handlers.get_topic_handler = dummy_handler

    client = TestClient(create_app_from_handlers(handlers), cookies={"token": "token"})

    response = client.get("/topics/925df229-e3cf-4435-88f0-9153b7ff37d6")
    assert response.status_code == 404


def test_get_topic_items_returns_200(handlers: Handlers) -> None:
    dummy_handler = AsyncMock(spec=GetTopicItemsHandler)
    sub = mock_sub()
    item1 = Item.new(
        uuid=uuid.UUID("1f897d4d-e4bc-40fb-8b58-5d7168c5c5ac"),
        name="item1",
        description="",
        subscription_uuid=sub.uuid,
        url=utils.parse_url("https://ae1b82ee.com"),
        thumbnail=utils.parse_url("https://test.com/thumbnail.png"),
        published_at=datetime.fromtimestamp(0, tz=timezone.utc))
    dummy_handler.handle.return_value = [
        ItemWithInteractionsAndSubscription(item=item1, interactions=[], subscription=sub),
    ]
    handlers.get_topic_items_handler = dummy_handler

    client = TestClient(create_app_from_handlers(handlers), cookies={"token": "token"})

    response = client.get(
        "/topics/1f897d4d-e4bc-40fb-8b58-5d7168c5c5ac/items?"
        "created_before_ts=888.0&page_number=0&page_size=1")
    assert response.status_code == 200
    assert len(response.json()["elements"]) == 1
    assert response.json()["next_page"] == ("http://testserver/topics/1f897d4d-e4bc-40fb-8b58-5d7168c5c5ac/items?"
                                            "created_before_ts=888.0&page_number=1&page_size=1")
    assert response.json()["previous_page"] is None


def test_get_topic_items_for_non_existing_topic_returns_404(handlers: Handlers) -> None:
    dummy_handler = AsyncMock()
    dummy_handler.handle.side_effect = TopicNotFoundError
    handlers.get_topic_items_handler = dummy_handler

    client = TestClient(create_app_from_handlers(handlers), cookies={"token": "token"})

    response = client.get("/topics/925df229-e3cf-4435-88f0-9153b7ff37d6/items?page_number=0&page_size=1")
    assert response.status_code == 404


def test_get_topic_items_parses_query_parameters(handlers: Handlers) -> None:
    dummy_get_topic_items_handler = AsyncMock(spec=GetTopicItemsHandler)
    dummy_get_topic_items_handler.handle.return_value = []
    handlers.get_topic_items_handler = dummy_get_topic_items_handler

    client = TestClient(create_app_from_handlers(handlers), cookies={"token": "token"})

    client.get(
        "/topics/3e9232e7-fa87-4e14-a642-9df94d619c1a/items?"
        "page_number=0&page_size=1&search=test&created_before_ts=0&"
        "max_duration=100&min_duration=10&"
        "include_interactions=without_interactions,recommended,viewed,hidden,discouraged&"
        "excluded_subscriptions=1f897d4d-e4bc-40fb-8b58-5d7168c5c5ac,0fe0fb76-6312-4468-b61d-e0834bf99ff2",
    )
    dummy_get_topic_items_handler.handle.assert_called_once_with(
        user_id=USER_UUID,
        topic_id=uuid.UUID("3e9232e7-fa87-4e14-a642-9df94d619c1a"),
        created_before=datetime.fromtimestamp(0, tz=timezone.utc),
        page_number=0,
        page_size=1,
        text_filter="test",
        min_duration=10,
        max_duration=100,
        include_items_without_interactions=True,
        include_recommended_items=True,
        include_discouraged_items=True,
        include_viewed_items=True,
        include_hidden_items=True,
        excluded_subscriptions={uuid.UUID("1f897d4d-e4bc-40fb-8b58-5d7168c5c5ac"),
                                uuid.UUID("0fe0fb76-6312-4468-b61d-e0834bf99ff2")},
    )


def test_get_topic_items_recommended_and_without_interactions(handlers: Handlers) -> None:
    dummy_get_topic_items_handler = AsyncMock(spec=GetTopicItemsHandler)
    dummy_get_topic_items_handler.handle.return_value = []
    handlers.get_topic_items_handler = dummy_get_topic_items_handler

    client = TestClient(create_app_from_handlers(handlers), cookies={"token": "token"})

    client.get(
        "/topics/3e9232e7-fa87-4e14-a642-9df94d619c1a/items?"
        "page_number=0&page_size=1&search=test&created_before_ts=0&"
        "include_interactions=without_interactions,recommended")
    dummy_get_topic_items_handler.handle.assert_called_once_with(
        user_id=USER_UUID,
        topic_id=uuid.UUID("3e9232e7-fa87-4e14-a642-9df94d619c1a"),
        created_before=datetime.fromtimestamp(0, tz=timezone.utc),
        page_number=0,
        page_size=1,
        text_filter="test",
        min_duration=None,
        max_duration=None,
        include_items_without_interactions=True,
        include_recommended_items=True,
        include_discouraged_items=False,
        include_viewed_items=False,
        include_hidden_items=False,
        excluded_subscriptions=None,
    )


def test_assign_subscription_to_topic_returns_200(handlers: Handlers) -> None:
    client = TestClient(create_app_from_handlers(handlers), cookies={"token": "token"})

    response = client.post(
        "/topics/f22b92da-5b90-455f-8141-fb4a37f07805/subscriptions/ae1b82ee-f870-4a1f-a1c8-898c10ce9eb8")
    assert response.status_code == 201
    assert response.content == b""


def test_assign_non_existing_subscription_to_topic_returns_404(handlers: Handlers) -> None:
    dummy_handler = AsyncMock()
    dummy_handler.handle.side_effect = SubscriptionNotFoundError
    handlers.assign_subscription_to_topic_handler = dummy_handler
    client = TestClient(create_app_from_handlers(handlers), cookies={"token": "token"})

    response = client.post(
        "/topics/f22b92da-5b90-455f-8141-fb4a37f07805/subscriptions/ae1b82ee-f870-4a1f-a1c8-898c10ce9eb8")
    assert response.status_code == 404


def test_assign_subscription_to_non_existing_topic_returns_404(handlers: Handlers) -> None:
    dummy_handler = AsyncMock()
    dummy_handler.handle.side_effect = TopicNotFoundError
    handlers.assign_subscription_to_topic_handler = dummy_handler
    client = TestClient(create_app_from_handlers(handlers), cookies={"token": "token"})

    response = client.post(
        "/topics/f22b92da-5b90-455f-8141-fb4a37f07805/subscriptions/ae1b82ee-f870-4a1f-a1c8-898c10ce9eb8")
    assert response.status_code == 404


def test_unassign_subscription_from_topic_returns_204(handlers: Handlers) -> None:
    client = TestClient(create_app_from_handlers(handlers), cookies={"token": "token"})

    response = client.delete(
        "/topics/f22b92da-5b90-455f-8141-fb4a37f07805/subscriptions/ae1b82ee-f870-4a1f-a1c8-898c10ce9eb8")
    assert response.status_code == 204
    assert response.content == b""


def test_unassign_non_existing_subscription_from_topic_returns_404(handlers: Handlers) -> None:
    dummy_handler = AsyncMock()
    dummy_handler.handle.side_effect = SubscriptionNotFoundError
    handlers.unassign_subscription_from_topic_handler = dummy_handler
    client = TestClient(create_app_from_handlers(handlers), cookies={"token": "token"})

    response = client.delete(
        "/topics/f22b92da-5b90-455f-8141-fb4a37f07805/subscriptions/ae1b82ee-f870-4a1f-a1c8-898c10ce9eb8")
    assert response.status_code == 404


def test_unassign_subscription_from_non_existing_topic_returns_404(handlers: Handlers) -> None:
    dummy_handler = AsyncMock()
    dummy_handler.handle.side_effect = TopicNotFoundError
    handlers.unassign_subscription_from_topic_handler = dummy_handler
    client = TestClient(create_app_from_handlers(handlers), cookies={"token": "token"})

    response = client.delete(
        "/topics/f22b92da-5b90-455f-8141-fb4a37f07805/subscriptions/ae1b82ee-f870-4a1f-a1c8-898c10ce9eb8")
    assert response.status_code == 404


def test_get_subscriptions_items_returns_200(handlers: Handlers) -> None:
    sub = mock_sub()
    dummy_handler = AsyncMock(spec=GetSubscriptionItemsHandler)
    item1 = Item.new(
        uuid=uuid.UUID("1f897d4d-e4bc-40fb-8b58-5d7168c5c5ac"),
        name="item1",
        description="",
        subscription_uuid=sub.uuid,
        url=utils.parse_url("https://ae1b82ee.com"),
        thumbnail=utils.parse_url("https://test.com/thumbnail.png"),
        published_at=datetime.fromtimestamp(0, tz=timezone.utc))
    dummy_handler.handle.return_value = GetSubscriptionItemsResponse(
        items=[ItemWithInteractions(item=item1, interactions=[])], subscription=sub)
    handlers.get_subscription_items_handler = dummy_handler

    client = TestClient(create_app_from_handlers(handlers), cookies={"token": "token"})

    response = client.get(
        f"/subscriptions/{sub.uuid}/items?"
        "created_before_ts=999.0&page_number=0&page_size=1")
    assert response.status_code == 200
    assert len(response.json()["elements"]) == 1
    assert response.json()["next_page"] == (
        f"http://testserver/subscriptions/{sub.uuid}/items?"
        "created_before_ts=999.0&page_number=1&page_size=1")
    assert response.json()["previous_page"] is None


def test_find_by_invalid_username_returns_bad_request_error(handlers: Handlers) -> None:
    client = TestClient(create_app_from_handlers(handlers), cookies={"token": "token"})

    response = client.get("/curators/username/a%20a")

    assert response.status_code == HTTP_400_BAD_REQUEST


def test_register_new_user_with_invalid_username_returns_bad_request_error(handlers: Handlers) -> None:
    client = TestClient(create_app_from_handlers(handlers), cookies={"token": "token"})

    response = client.post(
        "/register_email",
        json={
            "email": "johndoe@email.com",
            "password": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            "first_name": "John",
            "last_name": "Doe",
            "username": "a a",
            "validation_base_url": "https://linkurator-test.com/validate",
        })

    assert response.status_code == HTTP_400_BAD_REQUEST


def test_unfollow_subscription_returns_204(handlers: Handlers) -> None:
    dummy_handler = AsyncMock()
    dummy_handler.handle.return_value = None
    handlers.unfollow_subscription_handler = dummy_handler
    client = TestClient(create_app_from_handlers(handlers), cookies={"token": "token"})

    response = client.delete("/subscriptions/36477a42-3874-45c8-9472-baab09204484/follow")
    assert response.status_code == 204
    assert response.content == b""


def test_unfollow_assigned_subscription_returns_403(handlers: Handlers) -> None:
    dummy_handler = AsyncMock()
    dummy_handler.handle.side_effect = CannotUnfollowAssignedSubscriptionError
    handlers.unfollow_subscription_handler = dummy_handler
    client = TestClient(create_app_from_handlers(handlers), cookies={"token": "token"})

    response = client.delete("/subscriptions/362a9ddb-1838-419e-acef-0159b0f27e2b/follow")
    assert response.status_code == 403


def test_favorite_topic_returns_201(handlers: Handlers) -> None:
    client = TestClient(create_app_from_handlers(handlers), cookies={"token": "token"})

    response = client.post("/topics/f22b92da-5b90-455f-8141-fb4a37f07805/favorite")
    assert response.status_code == 201
    assert response.content == b""


def test_favorite_non_existing_topic_returns_404(handlers: Handlers) -> None:
    dummy_handler = AsyncMock()
    dummy_handler.handle.side_effect = TopicNotFoundError
    handlers.favorite_topic_handler = dummy_handler
    client = TestClient(create_app_from_handlers(handlers), cookies={"token": "token"})

    response = client.post("/topics/f22b92da-5b90-455f-8141-fb4a37f07805/favorite")
    assert response.status_code == 404


def test_favorite_topic_without_authentication_returns_401(handlers: Handlers) -> None:
    client = TestClient(create_app_from_handlers(handlers))

    response = client.post("/topics/f22b92da-5b90-455f-8141-fb4a37f07805/favorite")
    assert response.status_code == 401


def test_unfavorite_topic_returns_204(handlers: Handlers) -> None:
    client = TestClient(create_app_from_handlers(handlers), cookies={"token": "token"})

    response = client.delete("/topics/f22b92da-5b90-455f-8141-fb4a37f07805/favorite")
    assert response.status_code == 204
    assert response.content == b""


def test_unfavorite_topic_without_authentication_returns_401(handlers: Handlers) -> None:
    client = TestClient(create_app_from_handlers(handlers))

    response = client.delete("/topics/f22b92da-5b90-455f-8141-fb4a37f07805/favorite")
    assert response.status_code == 401
