from datetime import datetime, timezone
from typing import Optional, List
from uuid import uuid4, UUID

from linkurator_core.domain.common.utils import parse_url
from linkurator_core.domain.subscriptions.subscription import SubscriptionProvider, Subscription
from linkurator_core.domain.users.external_service_credential import ExternalServiceCredential, ExternalServiceType
from linkurator_core.domain.users.user import User


def mock_user(uuid: Optional[UUID] = None, subscribed_to: Optional[List[UUID]] = None) -> User:
    uuid = uuid or uuid4()
    return User.new(uuid=uuid,
                    last_name="name",
                    first_name="user",
                    email=f"{uuid}@email.com",
                    locale="en",
                    avatar_url=parse_url(f"https://avatar.com/{uuid}.png"),
                    google_refresh_token=str(uuid),
                    subscription_uuids=subscribed_to)


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


def mock_credential(user_id: Optional[UUID] = None) -> ExternalServiceCredential:
    user_id = user_id or uuid4()
    return ExternalServiceCredential(
        user_id=user_id,
        credential_type=ExternalServiceType.YOUTUBE_API_KEY,
        credential_value="test-api-key",
        created_at=datetime(2020, 1, 1, 4, 4, 4, tzinfo=timezone.utc),
        updated_at=datetime(2022, 1, 1, 4, 4, 4, tzinfo=timezone.utc)
    )
