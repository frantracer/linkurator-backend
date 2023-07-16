from pydantic.networks import AnyUrl
from pydantic.tools import parse_obj_as


def parse_url(url: str) -> AnyUrl:
    return parse_obj_as(AnyUrl, url)
