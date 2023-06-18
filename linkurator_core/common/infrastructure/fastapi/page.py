from __future__ import annotations

import math
from typing import Generic, List, Optional, TypeVar

from pydantic import AnyUrl
from pydantic.generics import GenericModel
from starlette.datastructures import URL

from linkurator_core.common import utils

Element = TypeVar("Element")


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

    @classmethod
    def create(cls, elements: List[Element], total_elements: int,
               page_number: int, page_size: int, current_url: URL) -> Page[Element]:
        next_page = Page.next_page_url(
            current_url=current_url,
            current_page_number=page_number,
            page_size=page_size,
            total_items=total_elements)

        previous_page = Page.previous_page_url(
            current_url=current_url,
            current_page_number=page_number,
            page_size=page_size,
            total_items=total_elements)

        return cls(elements=elements,
                   total_elements=total_elements,
                   page_number=page_number,
                   page_size=page_size,
                   next_page=next_page,
                   previous_page=previous_page)

    @staticmethod
    def next_page_url(
            current_url: URL,
            current_page_number: int,
            total_items: int,
            page_size: int
    ) -> Optional[AnyUrl]:
        base_url = current_url.remove_query_params(["page_number", "page_size"])
        next_page_url = None
        next_page_number = current_page_number + 1
        if math.ceil(total_items / page_size) > next_page_number >= 0:
            next_page_url = utils.parse_url(str(base_url.include_query_params(
                page_number=next_page_number,
                page_size=page_size)))
        return next_page_url

    @staticmethod
    def previous_page_url(
            current_url: URL,
            current_page_number: int,
            total_items: int,
            page_size: int
    ) -> Optional[AnyUrl]:
        base_url = current_url.remove_query_params(["page_number", "page_size"])
        previous_page_url = None
        previous_page_number = current_page_number - 1
        if math.ceil(total_items / page_size) > previous_page_number >= 0:
            previous_page_url = utils.parse_url(str(base_url.include_query_params(
                page_number=previous_page_number,
                page_size=page_size)))
        return previous_page_url
