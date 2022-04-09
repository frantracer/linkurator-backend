from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi.routing import APIRouter
from pydantic.networks import AnyUrl
from pydantic.tools import parse_obj_as
from pydantic.types import NonNegativeInt, PositiveInt

from linkurator_core.infrastructure.fastapi.models.page import Page
from linkurator_core.infrastructure.fastapi.models.subscription import SubscriptionSchema


def get_router() -> APIRouter:
    router = APIRouter()

    @router.get("/", response_model=Page[SubscriptionSchema])
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

    return router
