from datetime import datetime, timezone
from typing import Optional, List
from uuid import uuid4, UUID

from linkurator_core.domain.common import utils
from linkurator_core.domain.common.utils import parse_url
from linkurator_core.domain.items.interaction import Interaction, InteractionType
from linkurator_core.domain.items.item import Item, ItemProvider
from linkurator_core.domain.subscriptions.subscription import SubscriptionProvider, Subscription
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.users.external_service_credential import ExternalServiceCredential, ExternalServiceType
from linkurator_core.domain.users.user import User


def mock_user(
        uuid: Optional[UUID] = None,
        subscribed_to: Optional[List[UUID]] = None,
        refresh_token: Optional[str] = None,
        is_admin: bool = False
) -> User:
    uuid = uuid or uuid4()
    return User.new(uuid=uuid,
                    last_name="name",
                    first_name="user",
                    username=str(uuid),
                    email=f"{uuid}@email.com",
                    locale="en",
                    avatar_url=parse_url(f"https://avatar.com/{uuid}.png"),
                    google_refresh_token=str(uuid) if refresh_token is None else refresh_token,
                    subscription_uuids=subscribed_to,
                    is_admin=is_admin)


def mock_sub(uuid: Optional[UUID] = None) -> Subscription:
    uuid = uuid or uuid4()
    return Subscription.new(
        uuid=uuid,
        provider=SubscriptionProvider.YOUTUBE,
        name='Test',
        url=parse_url(f'https://www.youtube.com/channel/{uuid}'),
        thumbnail=parse_url(f'https://www.youtube.com/channel/{uuid}/thumbnail'),
        external_data={},
    )


def mock_topic(uuid: Optional[UUID] = None, user_uuid: Optional[UUID] = None) -> Topic:
    uuid = uuid or uuid4()
    user_uuid = user_uuid or uuid4()
    return Topic.new(
        uuid=uuid,
        name=f'Topic {uuid}',
        user_id=user_uuid,
        subscription_ids=[],
    )


def mock_credential(
        user_id: Optional[UUID] = None,
        credential_type: ExternalServiceType = ExternalServiceType.YOUTUBE_API_KEY
) -> ExternalServiceCredential:
    user_id = user_id or uuid4()
    return ExternalServiceCredential(
        user_id=user_id,
        credential_type=credential_type,
        credential_value="test-api-key",
        created_at=datetime(2020, 1, 1, 4, 4, 4, tzinfo=timezone.utc),
        updated_at=datetime(2022, 1, 1, 4, 4, 4, tzinfo=timezone.utc)
    )


def mock_item(
        item_uuid: Optional[UUID] = None,
        sub_uuid: Optional[UUID] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        published_at: Optional[datetime] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        url: Optional[str] = None,
        version: Optional[int] = None,
        duration: Optional[int] = None,
) -> Item:
    random_uuid = item_uuid if item_uuid is not None else uuid4()
    random_name = f"some name {random_uuid}" if name is None else name
    random_description = f"some description with emojis {random_uuid} 🙂" if description is None else description
    random_subscription_uuid = sub_uuid if sub_uuid is not None else uuid4()
    random_url = utils.parse_url(url) if url is not None else utils.parse_url(f'https://{random_uuid}.com')
    random_thumbnail = utils.parse_url(f'https://{random_uuid}.com/thumbnail.png')
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
        provider=ItemProvider.YOUTUBE
    )


def mock_interaction(
        uuid: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        item_id: Optional[UUID] = None,
        created_at: Optional[datetime] = None,
        interaction_type: InteractionType = InteractionType.RECOMMENDED
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
        type=interaction_type
    )
