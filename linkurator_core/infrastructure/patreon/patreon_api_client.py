from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

from pydantic import AnyUrl, BaseModel

from linkurator_core.domain.common.utils import parse_url
from linkurator_core.infrastructure.asyncio_impl.http_client import AsyncHttpClient


class PatreonImage(BaseModel):
    url: AnyUrl
    height: int
    width: int


class PatreonAvatarPhotoImageUrls(BaseModel):
    default: AnyUrl


class PatreonCampaign(BaseModel):
    id: str
    creation_name: str
    summary: str
    url: str
    vanity: str
    avatar_photo_image_urls: PatreonAvatarPhotoImageUrls


class PatreonMembership(BaseModel):
    campaign_id: str


class PatreonUser(BaseModel):
    full_name: str
    vanity: str
    url: str
    image_url: str | None


class PatreonPost(BaseModel):
    id: str
    title: str
    url: str
    published_at: datetime
    image_url: str | None
    duration_seconds: int | None = None


BASE_URL = "https://www.patreon.com"


class PatreonApiClient:
    """Client for Patreon API"""

    def __init__(self, client_id: str, client_secret: str,
                 http_client: AsyncHttpClient = AsyncHttpClient()) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.http_client = http_client

    def authorization_url(self, redirect_uri: str) -> str:
        """Build the Patreon OAuth2 authorization URL."""
        scopes = "identity.memberships"
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": scopes,
        }
        return f"{BASE_URL}/oauth2/authorize?{urlencode(params)}"

    async def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> str | None:
        """Exchange authorization code for an access token. Returns the access token or None on failure."""
        token_url = f"{BASE_URL}/api/oauth2/token"
        data = {
            "code": code,
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": redirect_uri,
        }

        response = await self.http_client.post(token_url, data=data)
        if response.status == 200:
            return response.json["access_token"]
        logging.error("Failed to exchange Patreon code: %s -> %s", response.status, response.json)
        return None

    async def get_current_user_memberships(self, access_token: str) -> list[PatreonMembership]:
        """Get the memberships the current user is a member/patron of."""
        url = f"{BASE_URL}/api/oauth2/v2/identity"
        params = {
            "include": "memberships.campaign",
            "fields[member]": "patron_status",
        }
        headers = {"Authorization": f"Bearer {access_token}"}

        response = await self.http_client.get_json(url, headers=headers, params=params)
        if response.status == 200:
            included = response.json.get("included", [])

            memberships: list[PatreonMembership] = []
            for item in included:
                patron_status = item.get("attributes", {}).get("patron_status", "")
                item_type = item.get("type", "")
                campaign_id = item.get("relationships", {}).get("campaign", {}).get("data", {}).get("id", "")

                if item_type == "member" and patron_status == "active_patron":
                    memberships.append(PatreonMembership(campaign_id=campaign_id))

            return memberships
        logging.error("Failed to get Patreon memberships: %s -> %s", response.status, response.json)
        return []

    async def get_campaign(self, campaign_id: str) -> PatreonCampaign | None:
        """Get a campaign by ID."""
        url = f"{BASE_URL}/api/campaigns/{campaign_id}"
        params = {
            "fields[campaign]": "creation_name,summary,url,vanity,avatar_photo_image_urls",
        }

        response = await self.http_client.get_json(url, params=params)
        if response.status == 200:
            return map_json_to_campaign(response.json.get("data", {}))
        if response.status == 404:
            return None
        logging.error("Failed to get Patreon campaign: %s -> %s", response.status, response.json)
        return None

    async def get_campaign_posts(self, campaign_id: str, from_date: datetime) -> list[PatreonPost]:
        url = f"{BASE_URL}/api/campaigns/{campaign_id}/posts"
        page_size = 100
        all_posts: list[PatreonPost] = []

        params: dict[str, str] = {
            "include": "media",
            "fields[post]": "thumbnail,post_type,published_at,title,video_preview,url,post_metadata",
            "fields[media]": "id,image_urls",
            "page[count]": str(page_size),
            "filter[is_by_creator]": "true",
            "filter[contains_exclusive_posts]": "true",
            "json-api-use-default-includes": "false",
            "sort": "-published_at",
        }

        # cursor is url with query params
        cursor: str = url + "?" + urlencode(params)
        posts_ids: set[str] = set()

        while True:
            response = await self.http_client.get_json(cursor)
            if response.status != 200:
                logging.error("Failed to get Patreon posts: %s -> %s", response.status, response.json)
                break

            posts = map_json_to_posts(response.json)

            filtered_posts = [post for post in posts
                              if post.published_at >= from_date and post.id not in posts_ids]
            all_posts.extend(filtered_posts)

            posts_ids |= {post.id for post in posts}

            if len(filtered_posts) == 0:
                break

            next_cursor = response.json.get("links", {}).get("next")
            if next_cursor is None:
                break
            cursor = next_cursor
            await asyncio.sleep(1)  # Sleep to avoid hitting rate limits

        return all_posts

    async def get_post(self, post_id: str) -> PatreonPost | None:
        """Get a single post by ID."""
        url = f"{BASE_URL}/api/posts/{post_id}"
        params = {
            "include": "media",
            "fields[post]": "thumbnail,post_type,published_at,title,video_preview,url,post_metadata",
            "fields[media]": "id,image_urls",
        }

        response = await self.http_client.get_json(url, params=params)
        if response.status == 200:
            data = response.json.get("data", {})
            included = response.json.get("included", [])
            return map_json_to_post(data, included)
        if response.status == 404:
            return None
        logging.error("Failed to get Patreon post: %s -> %s", response.status, response.json)
        return None


def map_json_to_campaign(data: dict[str, Any]) -> PatreonCampaign:
    """Map Patreon API response to PatreonCampaign."""
    attributes = data.get("attributes", {})
    campaign_id = data.get("id", "")

    vanity = attributes.get("vanity", "")
    url = attributes.get("url", f"https://www.patreon.com/c/{campaign_id}")
    summary = attributes.get("summary", "")
    creation_name = attributes.get("creation_name", "")

    return PatreonCampaign(
        id=campaign_id,
        creation_name=creation_name,
        summary=summary,
        url=url,
        vanity=vanity,
        avatar_photo_image_urls=PatreonAvatarPhotoImageUrls(
            default=parse_url(attributes.get("avatar_photo_image_urls", {}).get("default", "")),
        ),
    )


def map_json_to_posts(body: dict[str, Any]) -> list[PatreonPost]:
    """Map Patreon API response to list of PatreonPost."""
    data = body.get("data", [])
    included = body.get("included", [])

    return [map_json_to_post(post, included) for post in data if post is not None]


def map_json_to_post(data: dict[str, Any], included: list[dict[str, Any]]) -> PatreonPost:
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

    # Get image URL from the thumbnail attribute
    post_metadata = attributes.get("post_metadata", {}) or {}
    image_order = post_metadata.get("image_order", []) or []
    media_id = image_order[0] if len(image_order) > 0 else None
    media_item: dict[str, Any] = {}
    if media_id is not None:
        media_item = next((item for item in included if item.get("id") == media_id), {})

    media_item_attributes = media_item.get("attributes", {}) or {}
    media_item_image_urls = media_item_attributes.get("image_urls", {}) or {}
    image_url: str | None = media_item_image_urls.get("thumbnail", None)
    if not image_url:
        thumbnail = attributes.get("thumbnail", {}) or {}
        image_url = thumbnail.get("default", None)

    # Get video duration if available
    video_preview = attributes.get("video_preview", {}) or {}
    duration_str = str(video_preview.get("full_content_duration", ""))
    duration_seconds = int(float(duration_str)) if duration_str != "" else None

    return PatreonPost(
        id=post_id,
        title=attributes.get("title", "Untitled"),
        url=attributes.get("url", f"https://www.patreon.com/posts/{post_id}"),
        published_at=published_at,
        image_url=image_url,
        duration_seconds=duration_seconds,
    )
