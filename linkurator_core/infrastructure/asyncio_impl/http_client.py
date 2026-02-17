from dataclasses import dataclass
from typing import Any

from aiohttp import ClientSession


@dataclass
class HttpResponse:
    text: str
    status: int


@dataclass
class JsonHttpResponse:
    json: dict[str, Any]
    status: int


class AsyncHttpClient:
    def __init__(self, contact_email: str | None = None, headers: dict[str, str] | None = None,
                 proxy_url: str | None = None) -> None:
        self.headers: dict[str, str] = headers or {}
        self.proxy_url = proxy_url
        if contact_email is not None:
            self.headers["User-Agent"] = f"RSS Feed Client; +https://linkurator.com; {contact_email}"

    async def get(self, url: str) -> HttpResponse:
        async with ClientSession() as session, session.get(url, headers=self.headers, proxy=self.proxy_url) as response:
            text = await response.text()
            return HttpResponse(text=text, status=response.status)

    async def get_json(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
    ) -> JsonHttpResponse:
        merged_headers = {**self.headers, **(headers or {})}
        async with ClientSession() as session, \
                session.get(url, headers=merged_headers, params=params, proxy=self.proxy_url) as response:
            json_body = await response.json(content_type=None)
            return JsonHttpResponse(json=json_body, status=response.status)

    async def post(
        self,
        url: str,
        data: dict[str, str],
        headers: dict[str, str] | None = None,
    ) -> JsonHttpResponse:
        merged_headers = {**self.headers, **(headers or {})}
        async with ClientSession() as session, \
                session.post(url, data=data, headers=merged_headers, proxy=self.proxy_url) as response:
            json_body = await response.json(content_type=None)
            return JsonHttpResponse(json=json_body, status=response.status)

    async def check(self, url: str) -> int:
        async with ClientSession() as session, session.get(url, proxy=self.proxy_url) as response:
            return response.status
