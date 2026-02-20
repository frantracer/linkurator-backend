import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from aiohttp import ClientSession


@dataclass
class HttpResponse:
    text: str
    status: int


@dataclass
class JsonHttpResponse:
    json: dict[str, Any]
    status: int


_T = TypeVar("_T")


class AsyncHttpClient:
    def __init__(
        self,
        contact_email: str | None = None,
        headers: dict[str, str] | None = None,
        proxy_url: str | None = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        self.headers: dict[str, str] = headers or {}
        self.proxy_url = proxy_url
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        if contact_email is not None:
            self.headers["User-Agent"] = f"RSS Feed Client; +https://linkurator.com; {contact_email}"

    async def _with_retry(self, request_fn: Callable[[], Awaitable[_T]]) -> _T:
        for attempt in range(self.max_retries):
            try:
                return await request_fn()
            except Exception as e:
                logging.warning("HTTP request failed (attempt %d/%d): %s", attempt + 1, self.max_retries + 1, e)
            await asyncio.sleep(self.retry_delay)
        return await request_fn()

    async def get(self, url: str) -> HttpResponse:
        async def _request() -> HttpResponse:
            async with ClientSession() as session, session.get(
                url, headers=self.headers, proxy=self.proxy_url,
            ) as response:
                text = await response.text()
                return HttpResponse(text=text, status=response.status)

        return await self._with_retry(_request)

    async def get_json(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
    ) -> JsonHttpResponse:
        merged_headers = {**self.headers, **(headers or {})}

        async def _request() -> JsonHttpResponse:
            async with ClientSession() as session, session.get(
                url, headers=merged_headers, params=params, proxy=self.proxy_url,
            ) as response:
                json_body = await response.json(content_type=None)
                return JsonHttpResponse(json=json_body, status=response.status)

        return await self._with_retry(_request)

    async def post(
        self,
        url: str,
        data: dict[str, str],
        headers: dict[str, str] | None = None,
    ) -> JsonHttpResponse:
        merged_headers = {**self.headers, **(headers or {})}

        async def _request() -> JsonHttpResponse:
            async with ClientSession() as session, session.post(
                url, data=data, headers=merged_headers, proxy=self.proxy_url,
            ) as response:
                json_body = await response.json(content_type=None)
                return JsonHttpResponse(json=json_body, status=response.status)

        return await self._with_retry(_request)

    async def check(self, url: str) -> int:
        async def _request() -> int:
            async with ClientSession() as session, session.get(url, proxy=self.proxy_url) as response:
                return response.status

        return await self._with_retry(_request)
