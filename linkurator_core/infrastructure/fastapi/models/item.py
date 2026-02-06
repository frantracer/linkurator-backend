from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import AnyUrl, BaseModel

from linkurator_core.domain.common.units import Seconds
from linkurator_core.domain.items.interaction import Interaction, InteractionType
from linkurator_core.domain.items.item import Item
from linkurator_core.domain.items.item_with_interactions import CuratorInteractions
from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.domain.users.user import User
from linkurator_core.infrastructure.fastapi.models.curator import CuratorSchema
from linkurator_core.infrastructure.fastapi.models.schema import Iso8601Datetime
from linkurator_core.infrastructure.fastapi.models.subscription import SubscriptionSchema


class RecommendedBySchema(BaseModel):
    """Curator with their interactions for an item."""

    curator: CuratorSchema
    created_at: Iso8601Datetime

    @classmethod
    def from_domain(cls, curator: User, created_at: datetime) -> RecommendedBySchema:
        return cls(
            curator=CuratorSchema.from_domain_user(user=curator, followed=True),
            created_at=created_at,
        )


class ItemSchema(BaseModel):
    """Content item that belongs to a subscription."""

    uuid: UUID
    subscription_uuid: UUID
    subscription: SubscriptionSchema
    name: str
    description: str
    url: AnyUrl
    thumbnail: AnyUrl
    created_at: Iso8601Datetime
    published_at: Iso8601Datetime
    duration: Seconds | None

    recommended: bool
    discouraged: bool
    viewed: bool
    hidden: bool

    recommended_by: list[RecommendedBySchema]

    @classmethod
    def from_domain_item(
        cls,
        item: Item,
        subscription: Subscription,
        user_interactions: list[Interaction] | None = None,
        curator_interactions: list[CuratorInteractions] | None = None,
    ) -> ItemSchema:
        user_interactions = [
            interaction for interaction in user_interactions or [] if interaction.item_uuid == item.uuid
        ]
        recommended = any(reaction.type == InteractionType.RECOMMENDED for reaction in user_interactions)
        discouraged = any(reaction.type == InteractionType.DISCOURAGED for reaction in user_interactions)
        viewed = any(reaction.type == InteractionType.VIEWED for reaction in user_interactions)
        hidden = any(reaction.type == InteractionType.HIDDEN for reaction in user_interactions)

        recommended_by: list[RecommendedBySchema] = []
        curator_interactions = curator_interactions or []
        for curator_interaction in curator_interactions:
            for interaction in curator_interaction.interactions:
                if interaction.type == InteractionType.RECOMMENDED and interaction.item_uuid == item.uuid:
                    recommended_by.append(
                        RecommendedBySchema.from_domain(curator_interaction.curator, interaction.created_at),
                    )

        return cls(
            uuid=item.uuid,
            subscription_uuid=item.subscription_uuid,
            subscription=SubscriptionSchema.from_domain_subscription(subscription, None),
            name=item.name,
            description=item.description,
            url=item.url,
            thumbnail=item.thumbnail,
            created_at=item.created_at,
            published_at=item.published_at,
            recommended=recommended,
            discouraged=discouraged,
            viewed=viewed,
            hidden=hidden,
            duration=item.duration,
            recommended_by=recommended_by,
        )


class InteractionFilterSchema(Enum):
    """Filter items by interaction type."""

    WITHOUT_INTERACTIONS = "without_interactions"
    RECOMMENDED = "recommended"
    DISCOURAGED = "discouraged"
    VIEWED = "viewed"
    HIDDEN = "hidden"


VALID_INTERACTIONS = ", ".join([value.value for value in InteractionFilterSchema])
