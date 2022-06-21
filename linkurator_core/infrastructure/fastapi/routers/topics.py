from datetime import datetime
from http import HTTPStatus
from typing import Any
from uuid import UUID

from fastapi.routing import APIRouter
from pydantic.networks import AnyUrl
from pydantic.tools import parse_obj_as
from pydantic.types import NonNegativeInt, PositiveInt

from linkurator_core.infrastructure.fastapi.models.item import ItemSchema
from linkurator_core.infrastructure.fastapi.models.message import Message
from linkurator_core.infrastructure.fastapi.models.page import Page
from linkurator_core.infrastructure.fastapi.models.topic import NewTopicSchema, TopicSchema


def get_router() -> APIRouter:
    """
    Get the router for the topics
    """

    router = APIRouter()

    @router.get("/{topic_id}/items", response_model=Page[ItemSchema])
    async def items_by_topic(
            topic_id: UUID, page_number: NonNegativeInt = 0, page_size: PositiveInt = 50,
            created_before: datetime = datetime.now()) -> Any:
        """
        Get the items from a topic
        """
        print(f"fetching items for topic {topic_id}")

        item = ItemSchema(
            uuid=UUID("b5badcd0-a187-427c-8583-962cecb002c9"),
            subscription_uuid=UUID("310e66ed-df47-470b-b904-7389d2246a9b"),
            name="Dummy Item",
            url=parse_obj_as(AnyUrl, "https://www.youtube.com/watch?v=tntOCGkgt98"),
            thumbnail=parse_obj_as(AnyUrl, "https://i.ytimg.com/vi/tntOCGkgt98/maxresdefault.jpg"),
            created_at=created_before,
            published_at=datetime.fromtimestamp(0),
            description=""
        )

        return Page[ItemSchema](
            elements=[item],
            total_elements=1,
            page_number=page_number,
            page_size=page_size,
            previous_page=None,
            next_page=None
        )

    @router.get("/", response_model=Page[TopicSchema])
    async def get_all_topics(page_number: NonNegativeInt = 0, page_size: PositiveInt = 50,
                             created_before: datetime = datetime.now()) -> Any:
        """
        Get all the topics from a user
        """
        topic = TopicSchema(
            uuid=UUID("bc2e6ac4-3f23-40c5-84f6-d9f97172936f"),
            name="Dummy Topic",
            subscriptions_ids=[UUID("a9f8f8f8-3f23-40c5-84f6-d9f97172936f")],
            created_at=created_before
        )

        return Page[TopicSchema](
            elements=[topic],
            total_elements=1,
            page_number=page_number,
            page_size=page_size,
            previous_page=None,
            next_page=None
        )

    @router.get("/{topic_id}", response_model=TopicSchema)
    async def get_topic(topic_id: UUID) -> Any:
        """
        Get a topic information from a user
        """
        return TopicSchema(
            uuid=topic_id,
            name="Dummy Topic",
            subscriptions_ids=[UUID("ab81b97f-559d-4c87-9fd7-ef6db4b8b0de")],
            created_at=datetime.now()
        )

    @router.post("/", response_model=TopicSchema)
    async def create_topic(new_topic: NewTopicSchema) -> Any:
        """
        Create a new topic for a user
        """
        return TopicSchema(
            uuid=new_topic.uuid,
            name=new_topic.name,
            subscriptions_ids=new_topic.subscriptions_ids,
            created_at=datetime.now()
        )

    @router.delete("/{topic_id}",
                   status_code=HTTPStatus.NO_CONTENT,
                   responses={404: {"model": None}})
    async def delete_topic(topic_id: UUID) -> Any:
        """
        Delete a topic
        """
        print(f"deleting topic {topic_id}")
        return

    @router.post("/{topic_id}/subscriptions/{subscription_id}",
                 response_model=TopicSchema,
                 responses={404: {"model": Message}})
    async def assign_subscription_to_topic(topic_id: UUID, subscription_id: UUID) -> Any:
        """
        Assign a subscription to a topic
        """
        return TopicSchema(
            uuid=topic_id,
            name="Dummy",
            subscriptions_ids=[subscription_id],
            created_at=datetime.now()
        )

    @router.delete("/{topic_id}/subscriptions/{subscription_id}",
                   response_model=TopicSchema,
                   responses={404: {"model": None}})
    async def remove_subscription_from_topic(topic_id: UUID, subscription_id: UUID) -> Any:
        """
        Remove subscription from topic
        """
        return TopicSchema(
            uuid=topic_id,
            name="Dummy",
            subscriptions_ids=[subscription_id],
            created_at=datetime.now()
        )

    return router
