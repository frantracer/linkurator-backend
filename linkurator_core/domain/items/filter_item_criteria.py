from dataclasses import dataclass
from typing import Optional


@dataclass
class FilterItemCriteria:
    text: Optional[str] = None
