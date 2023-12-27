from pydantic.networks import AnyUrl


def parse_url(url: str) -> AnyUrl:
    return AnyUrl(url)
