from pydantic import AnyUrl, parse_obj_as


def parse_url(url: str) -> AnyUrl:
    return parse_obj_as(AnyUrl, url)
