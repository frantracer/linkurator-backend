from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.users.user import User
from linkurator_core.infrastructure.fastapi.models.curator import CuratorSchema
from linkurator_core.infrastructure.fastapi.models.schema import Iso8601Datetime


class NewTopicSchema(BaseModel):
    """Input model for topic creation."""

    uuid: UUID
    name: str
    subscriptions_ids: list[UUID]


class UpdateTopicSchema(BaseModel):
    """Fields that can be updated on a topic."""

    name: str | None
    subscriptions_ids: list[UUID] | None


class TopicSchema(BaseModel):
    """Category that includes different subscriptions."""

    uuid: UUID
    name: str
    user_id: UUID
    subscriptions_ids: list[UUID]
    is_owner: bool
    followed: bool
    is_favorite: bool
    created_at: Iso8601Datetime
    curator: CuratorSchema

    @classmethod
    def from_domain_topic(cls, topic: Topic,
                          curator: User,
                          user: User | None) -> TopicSchema:
        if topic.user_id != curator.uuid:
            msg = "Curator and topic user must be the same"
            raise ValueError(msg)

        is_owner = False if user is None else user.uuid == topic.user_id
        followed = False if user is None else topic.uuid in user.get_followed_topics()
        is_favorite = False if user is None else topic.uuid in user.get_favorite_topics()
        curator_followed = False if user is None else topic.user_id in user.curators

        return cls(
            uuid=topic.uuid,
            user_id=topic.user_id,
            name=topic.name,
            subscriptions_ids=topic.subscriptions_ids,
            is_owner=is_owner,
            followed=followed,
            is_favorite=is_favorite,
            created_at=topic.created_at,
            curator=CuratorSchema.from_domain_user(curator, curator_followed),
        )
