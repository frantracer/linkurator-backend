from uuid import UUID

from pydantic import AnyUrl, BaseModel

from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.infrastructure.fastapi.models.schema import Iso8601Datetime


class SubscriptionSchema(BaseModel):
    """
    Information about the different channels the user is subscribed to
    """
    uuid: UUID
    name: str
    url: AnyUrl
    thumbnail: AnyUrl
    created_at: Iso8601Datetime
    scanned_at: Iso8601Datetime

    @classmethod
    def from_domain_subscription(cls, subscription: Subscription):
        return cls(uuid=subscription.uuid, name=subscription.name, url=subscription.url,
                   thumbnail=subscription.thumbnail, created_at=subscription.created_at,
                   scanned_at=subscription.scanned_at)
