from datetime import datetime, timezone

from pydantic import AnyUrl


def parse_url(url: str) -> AnyUrl:
    return AnyUrl(url)


def datetime_now() -> datetime:
    return datetime.now(tz=timezone.utc)
