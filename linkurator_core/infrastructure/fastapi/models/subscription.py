from __future__ import annotations

from uuid import UUID

from pydantic import AnyUrl, BaseModel

from linkurator_core.domain.subscriptions.subscription import Subscription, SubscriptionProvider
from linkurator_core.domain.users.user import User
from linkurator_core.infrastructure.fastapi.models.schema import Iso8601Datetime


class SubscriptionSchema(BaseModel):
    """Information about the different channels the user is subscribed to."""

    uuid: UUID
    name: str
    url: AnyUrl
    thumbnail: AnyUrl
    provider: SubscriptionProvider
    created_at: Iso8601Datetime
    scanned_at: Iso8601Datetime
    followed: bool

    @classmethod
    def from_domain_subscription(cls, subscription: Subscription, user: User | None) -> SubscriptionSchema:
        followed = False if user is None else subscription.uuid in user.get_subscriptions()
        return cls(uuid=subscription.uuid, name=subscription.name, url=subscription.url,
                   thumbnail=subscription.thumbnail, created_at=subscription.created_at,
                   scanned_at=subscription.scanned_at, followed=followed, provider=subscription.provider)
