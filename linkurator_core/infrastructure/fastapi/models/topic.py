from datetime import datetime
from typing import List
from uuid import UUID

from pydantic.main import BaseModel

from linkurator_core.domain.topic import Topic


class NewTopicSchema(BaseModel):
    """
    Input model for topic creation
    """
    uuid: UUID
    name: str
    subscriptions_ids: List[UUID]

    def __init__(self, uuid: UUID, name: str, subscriptions_ids: List[UUID]):
        super().__init__(uuid=uuid, name=name, subscriptions_ids=subscriptions_ids)


class TopicSchema(BaseModel):
    """
    Category that includes different subscriptions
    """
    uuid: UUID
    name: str
    user_id: UUID
    subscriptions_ids: List[UUID]
    created_at: datetime

    def __init__(self,
                 uuid: UUID,
                 user_id: UUID,
                 name: str,
                 subscriptions_ids: List[UUID],
                 created_at: datetime):
        super().__init__(uuid=uuid,
                         user_id=user_id,
                         name=name,
                         subscriptions_ids=subscriptions_ids,
                         created_at=created_at)

    @classmethod
    def from_domain_topic(cls, topic: Topic):
        return cls(uuid=topic.uuid,
                   user_id=topic.user_id,
                   name=topic.name,
                   subscriptions_ids=topic.subscriptions_ids,
                   created_at=topic.created_at)
