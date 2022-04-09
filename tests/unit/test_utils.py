import pytest
from pydantic.networks import AnyUrl

from linkurator_core.common.utils import parse_url


def test_convert_string_to_url():
    url: AnyUrl = parse_url('https://www.google.com')
    assert url.scheme == 'https'
    assert url.host == 'www.google.com'


def test_convert_invalid_string_to_url_raises_an_exception():
    with pytest.raises(ValueError):
        parse_url('Invalid URL')
