from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

from linkurator_core.domain.topics.topic import Topic
from linkurator_core.infrastructure.fastapi.models.schema import Iso8601Datetime


class NewTopicSchema(BaseModel):
    """
    Input model for topic creation
    """
    uuid: UUID
    name: str
    subscriptions_ids: List[UUID]


class UpdateTopicSchema(BaseModel):
    """
    Fields that can be updated on a topic
    """
    name: Optional[str]
    subscriptions_ids: Optional[List[UUID]]


class TopicSchema(BaseModel):
    """
    Category that includes different subscriptions
    """
    uuid: UUID
    name: str
    user_id: UUID
    subscriptions_ids: List[UUID]
    created_at: Iso8601Datetime

    @classmethod
    def from_domain_topic(cls, topic: Topic):
        return cls(uuid=topic.uuid,
                   user_id=topic.user_id,
                   name=topic.name,
                   subscriptions_ids=topic.subscriptions_ids,
                   created_at=topic.created_at)
