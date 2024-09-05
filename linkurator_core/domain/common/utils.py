from datetime import datetime, timezone

from pydantic.networks import AnyUrl


def parse_url(url: str) -> AnyUrl:
    return AnyUrl(url)


def datetime_now() -> datetime:
    return datetime.now(tz=timezone.utc)
