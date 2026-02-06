from __future__ import annotations

from enum import Enum
from uuid import UUID

from pydantic import AnyUrl, BaseModel

from linkurator_core.domain.common.units import Seconds
from linkurator_core.domain.items.interaction import Interaction, InteractionType
from linkurator_core.domain.items.item import Item
from linkurator_core.domain.items.item_with_interactions import ItemWithInteractions
from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.domain.users.user import User
from linkurator_core.infrastructure.fastapi.models.schema import Iso8601Datetime
from linkurator_core.infrastructure.fastapi.models.subscription import SubscriptionSchema


class CuratorInfoSchema(BaseModel):
    """Basic curator info for item responses."""

    id: UUID
    username: str
    avatar_url: AnyUrl

    @classmethod
    def from_domain_user(cls, user: User) -> CuratorInfoSchema:
        return cls(
            id=user.uuid,
            username=str(user.username),
            avatar_url=user.avatar_url,
        )


class CuratorInteractionsSchema(BaseModel):
    """Curator with their interactions for an item."""

    curator: CuratorInfoSchema
    interactions: list[InteractionType]

    @classmethod
    def from_domain(cls, curator: User, interactions: list[Interaction]) -> CuratorInteractionsSchema:
        return cls(
            curator=CuratorInfoSchema.from_domain_user(curator),
            interactions=[i.type for i in interactions],
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

    curators: list[CuratorInteractionsSchema]

    @classmethod
    def from_domain_item(
            cls,
            item: Item,
            subscription: Subscription,
            interactions: list[Interaction] | None = None,
            curator_interactions: list[tuple[User, list[Interaction]]] | None = None,
    ) -> ItemSchema:
        recommended = False
        discouraged = False
        viewed = False
        hidden = False
        if interactions is not None:
            recommended = any(reaction.type == InteractionType.RECOMMENDED for reaction in interactions)
            discouraged = any(reaction.type == InteractionType.DISCOURAGED for reaction in interactions)
            viewed = any(reaction.type == InteractionType.VIEWED for reaction in interactions)
            hidden = any(reaction.type == InteractionType.HIDDEN for reaction in interactions)

        curators_list: list[CuratorInteractionsSchema] = []
        if curator_interactions is not None:
            curators_list = [
                CuratorInteractionsSchema.from_domain(curator, curator_ints)
                for curator, curator_ints in curator_interactions
            ]

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
            curators=curators_list,
        )

    @classmethod
    def from_domain(cls, item_with_interactions: ItemWithInteractions) -> ItemSchema:
        curator_interactions: list[tuple[User, list[Interaction]]] = []
        if item_with_interactions.curator is not None:
            curator_interactions = [(item_with_interactions.curator, item_with_interactions.curator_interactions)]

        return cls.from_domain_item(
            item=item_with_interactions.item,
            subscription=item_with_interactions.subscription,
            interactions=item_with_interactions.interactions,
            curator_interactions=curator_interactions,
        )


class InteractionFilterSchema(Enum):
    """Filter items by interaction type."""

    WITHOUT_INTERACTIONS = "without_interactions"
    RECOMMENDED = "recommended"
    DISCOURAGED = "discouraged"
    VIEWED = "viewed"
    HIDDEN = "hidden"


VALID_INTERACTIONS = ", ".join([value.value for value in InteractionFilterSchema])
