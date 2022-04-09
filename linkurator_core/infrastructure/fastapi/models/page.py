from typing import Generic, List, Optional, TypeVar

from pydantic import AnyUrl
from pydantic.generics import GenericModel


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

    def __init__(self, elements: List[Element], total_elements: int,
                 page_number: int, page_size: int,
                 previous_page: Optional[AnyUrl], next_page: Optional[AnyUrl]):
        super().__init__(elements=elements, total_elements=total_elements,
                         page_number=page_number, page_size=page_size,
                         previous_page=previous_page, next_page=next_page)
