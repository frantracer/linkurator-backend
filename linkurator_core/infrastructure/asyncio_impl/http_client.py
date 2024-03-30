from dataclasses import dataclass

from aiohttp import ClientSession


@dataclass
class HttpResponse:
    text: str
    status: int


class AsyncHttpClient:
    async def get(self, url: str) -> HttpResponse:
        async with ClientSession() as session:
            async with session.get(url) as response:
                text = await response.text()
                return HttpResponse(text=text, status=response.status)
