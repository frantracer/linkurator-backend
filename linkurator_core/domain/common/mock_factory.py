from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from linkurator_core.domain.common import utils
from linkurator_core.domain.common.utils import parse_url
from linkurator_core.domain.items.interaction import Interaction, InteractionType
from linkurator_core.domain.items.item import Item, ItemProvider
from linkurator_core.domain.subscriptions.subscription import Subscription, SubscriptionProvider
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.users.external_service_credential import ExternalServiceCredential, ExternalServiceType
from linkurator_core.domain.users.user import User, Username


def mock_user(
        uuid: UUID | None = None,
        subscribed_to: list[UUID] | None = None,
        refresh_token: str | None = None,
        is_admin: bool = False,
        curators: set[UUID] | None = None,
        topics: set[UUID] | None = None,
        email: str | None = None,
        username: Username | None = None,
) -> User:
    uuid = uuid or uuid4()
    return User.new(
        uuid=uuid,
        last_name="name",
        first_name="user",
        username=username or Username(str(uuid)),
        email=email or f"{uuid}@email.com",
        locale="en",
        avatar_url=parse_url(f"https://avatar.com/{uuid}.png"),
        google_refresh_token=str(uuid) if refresh_token is None else refresh_token,
        subscription_uuids=set(subscribed_to) if subscribed_to is not None else set(),
        is_admin=is_admin,
        curators=set() if curators is None else curators,
        followed_topics=set() if topics is None else topics,
    )


def mock_sub(uuid: UUID | None = None, name: str = "Test", url: str | None = None,
             provider: SubscriptionProvider = SubscriptionProvider.YOUTUBE,
             ) -> Subscription:
    uuid = uuid or uuid4()
    return Subscription.new(
        uuid=uuid,
        provider=provider,
        name=name,
        url=parse_url(f"https://www.youtube.com/channel/{uuid}") if url is None else parse_url(url),
        thumbnail=parse_url(f"https://www.youtube.com/channel/{uuid}/thumbnail"),
        external_data={},
    )


def mock_topic(
        uuid: UUID | None = None,
        name: str | None = None,
        user_uuid: UUID | None = None,
        subscription_uuids: list[UUID] | None = None,
) -> Topic:
    uuid = uuid or uuid4()
    user_uuid = user_uuid or uuid4()
    return Topic.new(
        uuid=uuid,
        name=f"{uuid}" if name is None else name,
        user_id=user_uuid,
        subscription_ids=[] if subscription_uuids is None else subscription_uuids,
    )


def mock_credential(
        user_id: UUID | None = None,
        credential_type: ExternalServiceType = ExternalServiceType.YOUTUBE_API_KEY,
) -> ExternalServiceCredential:
    user_id = user_id or uuid4()
    return ExternalServiceCredential(
        user_id=user_id,
        credential_type=credential_type,
        credential_value="test-api-key",
        created_at=datetime(2020, 1, 1, 4, 4, 4, tzinfo=timezone.utc),
        updated_at=datetime(2022, 1, 1, 4, 4, 4, tzinfo=timezone.utc),
    )


def mock_item(
        item_uuid: UUID | None = None,
        sub_uuid: UUID | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        published_at: datetime | None = None,
        name: str | None = None,
        description: str | None = None,
        url: str | None = None,
        version: int | None = None,
        duration: int | None = None,
) -> Item:
    random_uuid = item_uuid if item_uuid is not None else uuid4()
    random_name = f"some name {random_uuid}" if name is None else name
    random_description = f"some description with emojis {random_uuid} 🙂" if description is None else description
    random_subscription_uuid = sub_uuid if sub_uuid is not None else uuid4()
    random_url = utils.parse_url(url) if url is not None else utils.parse_url(f"https://{random_uuid}.com")
    random_thumbnail = utils.parse_url(f"https://{random_uuid}.com/thumbnail.png")
    random_published_at = published_at if published_at is not None else datetime.now(tz=timezone.utc)
    random_created_at = created_at if created_at is not None else datetime.now(tz=timezone.utc)
    random_updated_at = updated_at if updated_at is not None else datetime.now(tz=timezone.utc)
    version = version if version is not None else 1

    return Item(
        name=random_name,
        description=random_description,
        uuid=random_uuid,
        subscription_uuid=random_subscription_uuid,
        url=random_url,
        thumbnail=random_thumbnail,
        published_at=random_published_at,
        created_at=random_created_at,
        updated_at=random_updated_at,
        version=version,
        duration=duration,
        provider=ItemProvider.YOUTUBE,
    )


def mock_interaction(
        uuid: UUID | None = None,
        user_id: UUID | None = None,
        item_id: UUID | None = None,
        created_at: datetime | None = None,
        interaction_type: InteractionType = InteractionType.RECOMMENDED,
) -> Interaction:
    uuid = uuid or uuid4()
    item_id = item_id or uuid4()
    user_id = user_id or uuid4()
    created_at = created_at or datetime.now(tz=timezone.utc)
    return Interaction(
        uuid=uuid,
        user_uuid=user_id,
        item_uuid=item_id,
        created_at=created_at,
        type=interaction_type,
    )
