from dataclasses import dataclass

from aiohttp import ClientSession


@dataclass
class HttpResponse:
    text: str
    status: int


class AsyncHttpClient:
    def __init__(self, contact_email: str | None = None) -> None:
        user_agent: str | None = None
        if contact_email is not None:
            user_agent = f"RSS Feed Client; +https://linkurator.com; {contact_email}"

        self.headers: dict[str, str] = {}
        if user_agent is not None:
            self.headers["User-Agent"] = user_agent

    async def get(self, url: str) -> HttpResponse:
        async with ClientSession() as session, session.get(url, headers=self.headers) as response:
            text = await response.text()
            return HttpResponse(text=text, status=response.status)

    async def check(self, url: str) -> int:
        async with ClientSession() as session, session.get(url) as response:
            return response.status
