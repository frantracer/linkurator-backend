from datetime import datetime
from typing import Annotated

from pydantic import PlainSerializer


def convert_datetime_to_iso_8601_string(date: datetime) -> str:
    return date.isoformat()


Iso8601Datetime = Annotated[
    datetime, PlainSerializer(convert_datetime_to_iso_8601_string, return_type=str, when_used='json')
]
