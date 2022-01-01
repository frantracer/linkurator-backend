"""
Main file of the application
"""
from datetime import datetime
from uuid import UUID, uuid4
from http import HTTPStatus
from typing import List, Any, Generic, TypeVar, Optional
from fastapi import FastAPI
from pydantic import BaseModel, AnyUrl, NonNegativeInt, PositiveInt
from pydantic.generics import GenericModel
from pydantic.tools import parse_obj_as

# Application initialisation
app = FastAPI()

# Type definition
Element = TypeVar("Element")


# Output models
class Page(GenericModel, Generic[Element]):
    """
    Page model
    """
    elements: List[Element]
    next_page: Optional[AnyUrl]
    previous_page: Optional[AnyUrl]
    total_elements: int
    page_size: int
    page_number: int

    def __init__(self, elements: List[Element], total_elements: int,
                 page_number: int, page_size: int,
                 previous_page: Optional[AnyUrl], next_page: Optional[AnyUrl]):
        super().__init__(elements=elements, total_elements=total_elements,
                         page_number=page_number, page_size=page_size,
                         previous_page=previous_page, next_page=next_page)


class NewTopic(BaseModel):
    """
    Input model for topic creation
    """
    uuid: UUID
    name: str
    subscriptions_ids: List[UUID]

    def __init__(self, uuid: UUID, name: str, subscriptions_ids: List[UUID]):
        super().__init__(uuid=uuid, name=name, subscriptions_ids=subscriptions_ids)


class Topic(BaseModel):
    """
    Category that includes different subscriptions
    """
    uuid: UUID
    name: str
    subscriptions_ids: List[UUID]
    created_at: datetime

    def __init__(self, uuid: UUID, name: str, subscriptions_ids: List[UUID],
                 created_at: datetime):
        super().__init__(uuid=uuid, name=name, subscriptions_ids=subscriptions_ids,
                         created_at=created_at)


class Subscription(BaseModel):
    """
    Information about the different channels the user is subscribed to
    """
    uuid: UUID
    name: str
    url: AnyUrl
    thumbnail: AnyUrl
    created_at: datetime
    scanned_at: datetime

    def __init__(self, uuid: UUID, name: str, url: AnyUrl, thumbnail: AnyUrl,
                 created_at: datetime, scanned_at: datetime):
        super().__init__(uuid=uuid, name=name, url=url, thumbnail=thumbnail,
                         created_at=created_at, scanned_at=scanned_at)


class Item(BaseModel):
    """
    Content item that belongs to a subscription
    """
    uuid: UUID
    subscription_uuid: UUID
    name: str
    url: AnyUrl
    thumbnail: AnyUrl
    created_at: datetime

    def __init__(self, uuid: UUID, subscription_uuid: UUID, name: str, url: AnyUrl,
                 thumbnail: AnyUrl, created_at: datetime):
        super().__init__(uuid=uuid, subscription_uuid=subscription_uuid, name=name,
                         url=url, thumbnail=thumbnail, created_at=created_at)


class Message(BaseModel):
    """
    Message with information about the request
    """
    message: str

    def __init__(self, message: str):
        super().__init__(message=message)


# Endpoints definition
@app.get("/health")
async def health() -> None:
    """
    Health endpoint returns a 200 if the service is alive
    """
    return


@app.get("/subscriptions",
         response_model=Page[Subscription])
async def get_all_subscriptions(page_number: NonNegativeInt = 0, page_size: PositiveInt = 50,
                                created_before: datetime = datetime.now()) -> Any:
    """
    Get the list of the user subscriptions
    """
    # Initialize dummy subscription
    subscription = Subscription(
        uuid=uuid4(),
        name="Dummy",
        url=parse_obj_as(AnyUrl, "https://www.youtube.com/channel/UC-9-kyTW8ZkZNDHQJ6FgpwQ"),
        thumbnail=parse_obj_as(AnyUrl, "https://i.ytimg.com/vi/tntOCGkgt98/maxresdefault.jpg"),
        created_at=created_before,
        scanned_at=datetime.now()
    )

    return Page[Subscription](
        elements=[subscription],
        total_elements=1,
        page_number=page_number,
        page_size=page_size,
        previous_page=None,
        next_page=None
    )


@app.get("/topics/{topic_id}/items",
         response_model=Page[Item])
async def items_by_topic(
        topic_id: UUID, page_number: NonNegativeInt = 0, page_size: PositiveInt = 50,
        created_before: datetime = datetime.now()) -> Any:
    """
    Get the items from a topic
    """
    print(f"fetching items for topic {topic_id}")

    item = Item(
        uuid=UUID("b5badcd0-a187-427c-8583-962cecb002c9"),
        subscription_uuid=UUID("310e66ed-df47-470b-b904-7389d2246a9b"),
        name="Dummy Item",
        url=parse_obj_as(AnyUrl, "https://www.youtube.com/watch?v=tntOCGkgt98"),
        thumbnail=parse_obj_as(AnyUrl, "https://i.ytimg.com/vi/tntOCGkgt98/maxresdefault.jpg"),
        created_at=created_before
    )

    return Page[Item](
        elements=[item],
        total_elements=1,
        page_number=page_number,
        page_size=page_size,
        previous_page=None,
        next_page=None
    )


@app.get("/topics",
         response_model=Page[Topic])
async def get_all_topics(page_number: NonNegativeInt = 0, page_size: PositiveInt = 50,
                         created_before: datetime = datetime.now()) -> Any:
    """
    Get all the topics from a user
    """
    topic = Topic(
        uuid=UUID("bc2e6ac4-3f23-40c5-84f6-d9f97172936f"),
        name="Dummy Topic",
        subscriptions_ids=[UUID("a9f8f8f8-3f23-40c5-84f6-d9f97172936f")],
        created_at=created_before
    )

    return Page[Topic](
        elements=[topic],
        total_elements=1,
        page_number=page_number,
        page_size=page_size,
        previous_page=None,
        next_page=None
    )


@app.get("/topics/{topic_id}",
         response_model=Topic)
async def get_topic(topic_id: UUID) -> Any:
    """
    Get a topic information from a user
    """
    return Topic(
        uuid=topic_id,
        name="Dummy Topic",
        subscriptions_ids=[UUID("ab81b97f-559d-4c87-9fd7-ef6db4b8b0de")],
        created_at=datetime.now()
    )


@app.post("/topics",
          response_model=Topic)
async def create_topic(new_topic: NewTopic) -> Any:
    """
    Create a new topic for a user
    """
    return Topic(
        uuid=new_topic.uuid,
        name=new_topic.name,
        subscriptions_ids=new_topic.subscriptions_ids,
        created_at=datetime.now()
    )


@app.delete("/topics/{topic_id}",
            status_code=HTTPStatus.NO_CONTENT,
            responses={404: {"model": None}})
async def delete_topic(topic_id: UUID) -> Any:
    """
    Delete a topic
    """
    print(f"deleting topic {topic_id}")
    return


@app.post("/topics/{topic_id}/subscriptions/{subscription_id}",
          response_model=Topic,
          responses={404: {"model": Message}})
async def assign_subscription_to_topic(topic_id: UUID, subscription_id: UUID) -> Any:
    """
    Assign a subscription to a topic
    """
    return Topic(
        uuid=topic_id,
        name="Dummy",
        subscriptions_ids=[subscription_id],
        created_at=datetime.now()
    )


@app.delete("/topics/{topic_id}/subscriptions/{subscription_id}",
            response_model=Topic,
            responses={404: {"model": None}})
async def remove_subscription_from_topic(topic_id: UUID, subscription_id: UUID) -> Any:
    """
    Remove subscription from topic
    """
    return Topic(
        uuid=topic_id,
        name="Dummy",
        subscriptions_ids=[subscription_id],
        created_at=datetime.now()
    )
