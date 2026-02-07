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

    async def refresh_access_token(self, refresh_token: str) -> str | None:
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
            "scope": "identity identity.memberships campaigns campaigns.posts",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, data=data) as response:
                if response.status == 200:
                    body = await response.json()
                    return body["access_token"]
                logging.error("Failed to refresh Patreon token: %s -> %s", response.status, await response.text())
                return None

    async def get_session_cookie(self, username: str, password: str) -> str | None:
        """
        Authenticate with Patreon using username and password to get a session cookie.

        Returns the session_id cookie value or None on failure.
        """
        login_url = f"{self.BASE_URL}/api/login"

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
        }

        payload = {
            "data": {
                "type": "user",
                "attributes": {
                    "email": username,
                    "password": password,
                },
            },
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(login_url, json=payload, headers=headers) as response:
                if response.status == 200:
                    # Extract session_id from cookies
                    session_cookie = response.cookies.get("session_id")
                    if session_cookie:
                        return session_cookie.value
                    logging.error("Login succeeded but no session_id cookie found")
                    return None
                logging.error("Failed to login to Patreon: %s -> %s", response.status, await response.text())
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

    async def get_current_user_memberships(self, access_token: str) -> list[PatreonCampaign]:
        """Get the campaigns the current user is a member/patron of."""
        url = f"{self.BASE_URL}/api/oauth2/v2/identity"
        params = {
            "include": "memberships.campaign",
            "fields[campaign]": "created_at,creation_name,image_url,is_monthly,patron_count,summary,url,vanity",
            "fields[member]": "patron_status",
        }

        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {access_token}"}
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    body = await response.json()
                    included = body.get("included", [])

                    # Extract campaigns from included data (filter by type "campaign")
                    campaigns = [
                        _map_json_to_campaign(item)
                        for item in included
                        if item.get("type") == "campaign"
                    ]
                    return campaigns
                logging.error("Failed to get Patreon memberships: %s -> %s", response.status, await response.text())
                return []

    async def fetch_patreon_posts(self, campaign_id: str) -> list[PatreonPost]:
        url = f"https://www.patreon.com/api/campaigns/{campaign_id}/posts"

        params = {
            "include": "user.campaign.current_user_pledge,access_rules.tier.null,moderator_actions,primary_image",
            "fields[post]": "commenter_count,current_user_can_view,image,thumbnail,insights_last_updated_at,patreon_url,post_type,published_at,title,upgrade_url,view_count,is_preview_blurred",
            "fields[access_rule]": "access_rule_type",
            "fields[reward]": "amount_cents,id",
            "fields[user]": "[]",
            "fields[campaign]": "[]",
            "fields[pledge]": "amount_cents",
            "fields[primary-image]": "image_icon,image_small,image_medium,image_large,primary_image_type,alt_text,image_colors,is_fallback,prefer_alternate_display,id",
            "page[cursor]": "null",
            "page[count]": "11",
            "filter[is_by_creator]": "true",
            "filter[contains_exclusive_posts]": "true",
            "sort": "-published_at",
            "json-api-use-default-includes": "false",
            "json-api-version": "1.0",
        }

        headers = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.7",
            "content-type": "application/vnd.api+json",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                print(f"Status: {response.status}")
                data = await response.json()
                print(data)
                return [_map_json_to_post(post) for post in data.get("data", [])]

    async def get_post(self, post_id: str) -> PatreonPost | None:
        """Get a single post by ID."""
        url = f"{self.BASE_URL}/api/oauth2/v2/posts/{post_id}"
        params = {
            "fields[post]": "title,content,is_paid,is_public,published_at,url,embed_url",
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
    summary = attributes.get("summary", "")
    image_url = attributes.get("embed_url", "")
    name = attributes.get("creation_name", attributes.get("name", "Unknown"))

    return PatreonCampaign(
        id=campaign_id,
        name=name,
        summary=summary,
        image_url=image_url,
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
