from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import aiohttp
from pydantic import AnyUrl, BaseModel


class PatreonImage(BaseModel):
    url: AnyUrl
    height: int
    width: int


class PatreonCampaign(BaseModel):
    id: str
    name: str
    summary: str | None
    image_url: str | None
    url: str
    vanity: str | None  # The creator's username/vanity URL


class PatreonPost(BaseModel):
    id: str
    title: str
    content: str | None
    url: str
    published_at: datetime
    image_url: str | None


class PatreonApiError(Exception):
    pass


class PatreonApiClient:
    """Client for Patreon API v2."""

    BASE_URL = "https://www.patreon.com"

    def __init__(self, client_id: str, client_secret: str, refresh_token: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token

    async def refresh_access_token(self, refresh_token: str) -> tuple[str, str] | None:
        """
        Refresh an access token using a refresh token.

        Returns a tuple of (new_access_token, new_refresh_token) or None on failure.
        """
        token_url = f"{self.BASE_URL}/api/oauth2/token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, data=data) as response:
                if response.status == 200:
                    body = await response.json()
                    return body["access_token"], body["refresh_token"]
                logging.error("Failed to refresh Patreon token: %s -> %s", response.status, await response.text())
                return None

    async def get_campaign(self, campaign_id: str) -> PatreonCampaign | None:
        """Get a campaign by ID."""
        url = f"{self.BASE_URL}/api/oauth2/v2/campaigns/{campaign_id}"
        params = {
            "fields[campaign]": "created_at,creation_name,image_url,is_monthly,patron_count,summary,url,vanity",
        }

        access_token = self.refresh_access_token(self.refresh_token)
        if access_token is None:
            logging.error("Cannot refresh access token to get Patreon campaign")
            return None

        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {access_token}"}
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    body = await response.json()
                    return _map_json_to_campaign(body.get("data", {}))
                if response.status == 404:
                    return None
                logging.error("Failed to get Patreon campaign: %s -> %s", response.status, await response.text())
                return None

    async def get_current_user_campaign(self, access_token: str) -> PatreonCampaign | None:
        """Get the campaign for the current authenticated user (creator)."""
        url = f"{self.BASE_URL}/api/oauth2/v2/campaigns"
        params = {
            "fields[campaign]": "created_at,creation_name,image_url,is_monthly,patron_count,summary,url,vanity",
        }

        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {access_token}"}
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    body = await response.json()
                    campaigns = body.get("data", [])
                    if len(campaigns) > 0:
                        return _map_json_to_campaign(campaigns[0])
                    return None
                logging.error("Failed to get Patreon campaigns: %s -> %s", response.status, await response.text())
                return None

    async def get_campaign_posts(
        self,
        campaign_id: str,
        cursor: str | None = None,
    ) -> tuple[list[PatreonPost], str | None]:
        """
        Get posts for a campaign.

        Returns a tuple of (posts, next_cursor). next_cursor is None if there are no more posts.
        """
        url = f"{self.BASE_URL}/api/oauth2/v2/campaigns/{campaign_id}/posts"
        params: dict[str, str] = {
            "fields[post]": "title,content,is_paid,is_public,published_at,url,image",
            "page[count]": "50",
        }
        if cursor:
            params["page[cursor]"] = cursor

        access_token = self.refresh_access_token(self.refresh_token)
        if access_token is None:
            logging.error("Cannot refresh access token to get Patreon campaign")
            return [], None

        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {access_token}"}
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    body = await response.json()
                    posts_data = body.get("data", [])
                    posts = [_map_json_to_post(post) for post in posts_data]

                    # Get next cursor from pagination
                    next_cursor = body.get("meta", {}).get("pagination", {}).get("cursors", {}).get("next")

                    return posts, next_cursor

                if response.status == 404:
                    return [], None

                logging.error("Failed to get Patreon posts: %s -> %s", response.status, await response.text())
                return [], None

    async def get_post(self, post_id: str) -> PatreonPost | None:
        """Get a single post by ID."""
        url = f"{self.BASE_URL}/api/oauth2/v2/posts/{post_id}"
        params = {
            "fields[post]": "title,content,is_paid,is_public,published_at,url,image",
        }

        access_token = self.refresh_access_token(self.refresh_token)
        if access_token is None:
            logging.error("Cannot refresh access token to get Patreon campaign")
            return None

        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {access_token}"}
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    body = await response.json()
                    return _map_json_to_post(body.get("data", {}))
                if response.status == 404:
                    return None
                logging.error("Failed to get Patreon post: %s -> %s", response.status, await response.text())
                return None


def _map_json_to_campaign(data: dict[str, Any]) -> PatreonCampaign:
    """Map Patreon API response to PatreonCampaign."""
    attributes = data.get("attributes", {})
    campaign_id = data.get("id", "")

    vanity = attributes.get("vanity")
    url = attributes.get("url", f"https://www.patreon.com/c/{campaign_id}")

    return PatreonCampaign(
        id=campaign_id,
        name=attributes.get("creation_name", attributes.get("name", "Unknown")),
        summary=attributes.get("summary"),
        image_url=attributes.get("image_url"),
        url=url,
        vanity=vanity,
    )


def _map_json_to_post(data: dict[str, Any]) -> PatreonPost:
    """Map Patreon API response to PatreonPost."""
    attributes = data.get("attributes", {})
    post_id = data.get("id", "")

    # Parse published_at
    published_str = attributes.get("published_at", "")
    if published_str:
        # Handle ISO 8601 format
        if published_str.endswith("Z"):
            published_str = published_str[:-1] + "+00:00"
        published_at = datetime.fromisoformat(published_str)
    else:
        published_at = datetime.now(timezone.utc)

    # Get image URL from the image attribute
    image = attributes.get("image")
    image_url = None
    if image and isinstance(image, dict):
        image_url = image.get("large_url") or image.get("url")

    return PatreonPost(
        id=post_id,
        title=attributes.get("title", "Untitled"),
        content=attributes.get("content"),
        url=attributes.get("url", f"https://www.patreon.com/posts/{post_id}"),
        published_at=published_at,
        image_url=image_url,
    )
