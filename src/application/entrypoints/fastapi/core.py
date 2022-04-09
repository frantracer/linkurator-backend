"""
Main file of the application
"""
import http
import json
from dataclasses import dataclass
from datetime import datetime
from http import HTTPStatus
from typing import Any, Dict, Generic, List, Optional, TypeVar
from urllib.parse import urlencode
from uuid import UUID, uuid4

import fastapi
import requests
from fastapi.applications import FastAPI
from fastapi.param_functions import Cookie
from fastapi.responses import JSONResponse
from pydantic.generics import GenericModel
from pydantic.main import BaseModel
from pydantic.networks import AnyUrl
from pydantic.tools import parse_obj_as
from pydantic.types import NonNegativeInt, PositiveInt
from requests.auth import HTTPBasicAuth

# FastAPI application
app: FastAPI = FastAPI()

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
    subscriptions_ids: List[UUID]
    created_at: datetime

    def __init__(self, uuid: UUID, name: str, subscriptions_ids: List[UUID],
                 created_at: datetime):
        super().__init__(uuid=uuid, name=name, subscriptions_ids=subscriptions_ids,
                         created_at=created_at)


class SubscriptionSchema(BaseModel):
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


class ItemSchema(BaseModel):
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
@dataclass
class Handlers:
    message: str = "Hello world!"


def create_app(handlers: Handlers) -> FastAPI:
    """
    Create the application
    """

    api = FastAPI()

    with open("client_secret.json", "r", encoding='UTF-8') as secrets_file:
        secrets = json.loads(secrets_file.read())
        client_id = secrets["web"]["client_id"]
        client_secret = secrets["web"]["client_secret"]
    scopes = ['email', 'openid']

    @api.get("/health")
    async def health() -> str:
        """
        Health endpoint returns a 200 if the service is alive
        """
        return handlers.message

    @api.route("/login", methods=["GET", "POST"])
    async def login(request: fastapi.Request) -> Any:
        """
        Login endpoint
        """
        token = request.cookies.get("token")
        if token is not None:
            return JSONResponse(content={"token_login": token})

        google_oauth_url = "https://accounts.google.com/o/oauth2/auth"
        query_params: Dict[str, str] = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": "http://localhost:9000/auth",
            "scope": " ".join(scopes),
            "state": "ETL04Oop9e1yFQQFRM2KpHvbWwtMRV",
            "access_type": "offline",
            "include_granted_scopes": "true"
        }
        authorization_url = f"{google_oauth_url}?{urlencode(query_params)}"
        return fastapi.responses.RedirectResponse(
            authorization_url,
            status_code=http.HTTPStatus.FOUND)

    @api.get("/auth")
    async def auth(code: str = "") -> Any:
        """
        Auth endpoint
        """
        google_oauth_url = "https://oauth2.googleapis.com/token"
        query_params: Dict[str, str] = {
            'grant_type': "authorization_code",
            "code": code,
            "redirect_uri": "http://localhost:9000/auth"
        }
        token_response = requests.post(google_oauth_url, auth=HTTPBasicAuth(client_id, client_secret),
                                       data=query_params)
        token = token_response.json().get("access_token")

        if token is not None:
            response = JSONResponse(content={"token_auth": token})
            response.set_cookie(key="token", value=token)
            return response
        return JSONResponse(content={"error": "Authentication failed"}, status_code=http.HTTPStatus.UNAUTHORIZED)

    @api.get("/logout")
    async def logout() -> Any:
        """
        Logout endpoint
        """
        response = JSONResponse(content={"message": "Logged out successfully"})
        response.delete_cookie(key="token")
        return response

    @api.get("/revoke")
    async def revoke(token: Optional[str] = Cookie(None)) -> Any:
        revoke_response = requests.post('https://oauth2.googleapis.com/revoke',
                                        params={'token': token},
                                        headers={'content-type': 'application/x-www-form-urlencoded'})

        if revoke_response.status_code == HTTPStatus.OK:
            response = JSONResponse(content={"message": "Token revoked"})
            response.delete_cookie(key="token")
            return response
        return JSONResponse(content={"error": "Failed to revoke token"},
                            status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

    @api.get("/subscriptions",
             response_model=Page[SubscriptionSchema])
    async def get_all_subscriptions(page_number: NonNegativeInt = 0, page_size: PositiveInt = 50,
                                    created_before: datetime = datetime.now()) -> Any:
        """
        Get the list of the user subscriptions
        """
        # Initialize dummy subscription
        subscription = SubscriptionSchema(
            uuid=uuid4(),
            name="Dummy",
            url=parse_obj_as(AnyUrl, "https://www.youtube.com/channel/UC-9-kyTW8ZkZNDHQJ6FgpwQ"),
            thumbnail=parse_obj_as(AnyUrl, "https://i.ytimg.com/vi/tntOCGkgt98/maxresdefault.jpg"),
            created_at=created_before,
            scanned_at=datetime.now()
        )

        return Page[SubscriptionSchema](
            elements=[subscription],
            total_elements=1,
            page_number=page_number,
            page_size=page_size,
            previous_page=None,
            next_page=None
        )

    @api.get("/topics/{topic_id}/items",
             response_model=Page[ItemSchema])
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
            created_at=created_before
        )

        return Page[ItemSchema](
            elements=[item],
            total_elements=1,
            page_number=page_number,
            page_size=page_size,
            previous_page=None,
            next_page=None
        )

    @api.get("/topics",
             response_model=Page[TopicSchema])
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

    @api.get("/topics/{topic_id}",
             response_model=TopicSchema)
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

    @api.post("/topics",
              response_model=TopicSchema)
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

    @api.delete("/topics/{topic_id}",
                status_code=HTTPStatus.NO_CONTENT,
                responses={404: {"model": None}})
    async def delete_topic(topic_id: UUID) -> Any:
        """
        Delete a topic
        """
        print(f"deleting topic {topic_id}")
        return

    @api.post("/topics/{topic_id}/subscriptions/{subscription_id}",
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

    @api.delete("/topics/{topic_id}/subscriptions/{subscription_id}",
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

    return api
