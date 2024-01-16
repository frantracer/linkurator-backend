from __future__ import annotations

from typing import Generic, List, Optional, TypeVar

from pydantic import AnyUrl, BaseModel
from starlette.datastructures import URL

from linkurator_core.domain.common import utils

Element = TypeVar("Element")


class Page(BaseModel, Generic[Element]):
    """
    Page model
    """
    elements: List[Element]
    next_page: Optional[AnyUrl]
    previous_page: Optional[AnyUrl]
    page_size: int
    page_number: int

    @classmethod
    def create(cls, elements: List[Element],
               page_number: int, page_size: int, current_url: URL) -> Page[Element]:
        next_page = None
        if len(elements) == page_size:
            next_page = Page.next_page_url(
                current_url=current_url,
                current_page_number=page_number,
                page_size=page_size)

        previous_page = None
        if page_number > 0:
            previous_page = Page.previous_page_url(
                current_url=current_url,
                current_page_number=page_number,
                page_size=page_size)

        return cls(elements=elements,
                   page_number=page_number,
                   page_size=page_size,
                   next_page=next_page,
                   previous_page=previous_page)

    @staticmethod
    def next_page_url(
            current_url: URL,
            current_page_number: int,
            page_size: int
    ) -> Optional[AnyUrl]:
        base_url = current_url.remove_query_params(["page_number", "page_size"])
        next_page_number = current_page_number + 1
        next_page_url = utils.parse_url(str(base_url.include_query_params(
            page_number=next_page_number,
            page_size=page_size)))
        return next_page_url

    @staticmethod
    def previous_page_url(
            current_url: URL,
            current_page_number: int,
            page_size: int
    ) -> Optional[AnyUrl]:
        base_url = current_url.remove_query_params(["page_number", "page_size"])
        previous_page_number = current_page_number - 1
        previous_page_url = utils.parse_url(str(base_url.include_query_params(
            page_number=previous_page_number,
            page_size=page_size)))
        return previous_page_url
