from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from linkurator_core.infrastructure.asyncio_impl.http_client import AsyncHttpClient, JsonHttpResponse
from linkurator_core.infrastructure.patreon.patreon_api_client import (
    PatreonApiClient,
    map_json_to_campaign,
    map_json_to_post,
    map_json_to_posts,
)

PATREON_JSON_DIR = Path(__file__).parent / "patreon"


def _load_json(filename: str) -> dict[str, Any]:
    return json.loads((PATREON_JSON_DIR / filename).read_text())


# =============================================================================
# Tests for map_json_to_campaign using real JSON example
# =============================================================================

class TestMapJsonToCampaign:
    def test_maps_single_campaign_json(self) -> None:
        body = _load_json("single_campaign_example.json")
        campaign = map_json_to_campaign(body["data"])

        assert campaign.id == "209197"
        assert campaign.vanity == "Pazos64"
        assert campaign.creation_name == "creating Risas con Videojuegos y Monos"
        assert campaign.url == "https://www.patreon.com/Pazos64"
        assert "Pazos64" in campaign.summary
        assert "c10.patreonusercontent.com" in str(campaign.avatar_photo_image_urls.default)


# =============================================================================
# Tests for map_json_to_post using real JSON example
# =============================================================================

class TestMapJsonToPost:
    def test_maps_single_post_json(self) -> None:
        body = _load_json("single_post_example.json")
        data = body["data"]
        included = body.get("included", [])
        post = map_json_to_post(data, included)

        assert post.id == "150496409"
        assert "Consolita" in post.title
        assert post.url == "https://www.patreon.com/posts/consolita-el-mal-150496409"
        assert post.published_at == datetime(2026, 2, 11, 15, 13, 3, tzinfo=timezone.utc)
        assert post.image_url is not None
        assert "patreon.com/media-u" in post.image_url
        assert post.duration_seconds is None

    def test_maps_post_with_video_duration(self) -> None:
        body = _load_json("campaign_posts_example.json")
        data_list = body["data"]
        included = body.get("included", [])

        # Second post has video_preview with full_content_duration
        video_post = data_list[1]
        post = map_json_to_post(video_post, included)

        assert post.id == "149956206"
        assert post.duration_seconds == 3739
        assert "Oye mira 4 cosas" in post.title

    def test_maps_post_with_image_from_metadata_order(self) -> None:
        body = _load_json("campaign_posts_example.json")
        data_list = body["data"]
        included = body.get("included", [])

        # Second post has image_order in post_metadata referencing media "608822750"
        post = map_json_to_post(data_list[1], included)

        assert post.image_url is not None
        assert "c10.patreonusercontent.com" in post.image_url

    def test_maps_post_without_video_preview(self) -> None:
        body = _load_json("campaign_posts_example.json")
        included = body.get("included", [])

        # First post has video_preview = null
        post = map_json_to_post(body["data"][0], included)

        assert post.duration_seconds is None

    def test_maps_post_with_empty_image_order(self) -> None:
        body = _load_json("campaign_posts_example.json")
        included = body.get("included", [])

        # Third post has image_order = []
        post = map_json_to_post(body["data"][2], included)

        assert post.id == "149771848"
        # Falls back to thumbnail.default
        assert post.image_url is not None


# =============================================================================
# Tests for map_json_to_posts using real JSON example
# =============================================================================

class TestMapJsonToPosts:
    def test_maps_campaign_posts_json(self) -> None:
        body = _load_json("campaign_posts_example.json")
        posts = map_json_to_posts(body)

        assert len(posts) == 3
        assert posts[0].id == "150496409"
        assert posts[1].id == "149956206"
        assert posts[2].id == "149771848"


# =============================================================================
# Tests for PatreonApiClient API errors by mocking HTTP client
# =============================================================================

def _make_client(http_client: AsyncMock) -> PatreonApiClient:
    return PatreonApiClient(
        client_id="test_client_id",
        client_secret="test_client_secret",
        http_client=http_client,
    )


class TestExchangeCodeForTokensErrors:
    @pytest.mark.asyncio()
    async def test_returns_none_on_http_error(self) -> None:
        http_client = AsyncMock(spec=AsyncHttpClient)
        http_client.post.return_value = JsonHttpResponse(json={"error": "invalid_grant"}, status=400)

        client = _make_client(http_client)
        result = await client.exchange_code_for_tokens("bad_code", "https://example.com/callback")

        assert result is None

    @pytest.mark.asyncio()
    async def test_returns_token_on_success(self) -> None:
        http_client = AsyncMock(spec=AsyncHttpClient)
        http_client.post.return_value = JsonHttpResponse(json={"access_token": "my_token"}, status=200)

        client = _make_client(http_client)
        result = await client.exchange_code_for_tokens("good_code", "https://example.com/callback")

        assert result == "my_token"

    @pytest.mark.asyncio()
    async def test_returns_none_on_server_error(self) -> None:
        http_client = AsyncMock(spec=AsyncHttpClient)
        http_client.post.return_value = JsonHttpResponse(json={"error": "server_error"}, status=500)

        client = _make_client(http_client)
        result = await client.exchange_code_for_tokens("code", "https://example.com/callback")

        assert result is None


class TestGetCurrentUserMembershipsErrors:
    @pytest.mark.asyncio()
    async def test_returns_empty_list_on_unauthorized(self) -> None:
        http_client = AsyncMock(spec=AsyncHttpClient)
        http_client.get_json.return_value = JsonHttpResponse(json={"error": "unauthorized"}, status=401)

        client = _make_client(http_client)
        result = await client.get_current_user_memberships("bad_token")

        assert result == []

    @pytest.mark.asyncio()
    async def test_returns_empty_list_on_server_error(self) -> None:
        http_client = AsyncMock(spec=AsyncHttpClient)
        http_client.get_json.return_value = JsonHttpResponse(json={"error": "server_error"}, status=500)

        client = _make_client(http_client)
        result = await client.get_current_user_memberships("token")

        assert result == []


class TestGetCampaignErrors:
    @pytest.mark.asyncio()
    async def test_returns_none_on_404(self) -> None:
        http_client = AsyncMock(spec=AsyncHttpClient)
        http_client.get_json.return_value = JsonHttpResponse(json={}, status=404)

        client = _make_client(http_client)
        result = await client.get_campaign("nonexistent")

        assert result is None

    @pytest.mark.asyncio()
    async def test_returns_none_on_server_error(self) -> None:
        http_client = AsyncMock(spec=AsyncHttpClient)
        http_client.get_json.return_value = JsonHttpResponse(json={"error": "internal"}, status=500)

        client = _make_client(http_client)
        result = await client.get_campaign("123")

        assert result is None

    @pytest.mark.asyncio()
    async def test_returns_campaign_on_success(self) -> None:
        http_client = AsyncMock(spec=AsyncHttpClient)
        body = _load_json("single_campaign_example.json")
        http_client.get_json.return_value = JsonHttpResponse(json=body, status=200)

        client = _make_client(http_client)
        result = await client.get_campaign("209197")

        assert result is not None
        assert result.id == "209197"
        assert result.vanity == "Pazos64"


class TestGetCampaignPostsErrors:
    @pytest.mark.asyncio()
    async def test_returns_empty_list_on_http_error(self) -> None:
        http_client = AsyncMock(spec=AsyncHttpClient)
        http_client.get_json.return_value = JsonHttpResponse(json={"error": "forbidden"}, status=403)

        client = _make_client(http_client)
        result = await client.get_campaign_posts("123", datetime(2024, 1, 1, tzinfo=timezone.utc))

        assert result == []

    @pytest.mark.asyncio()
    async def test_returns_posts_on_success(self) -> None:
        http_client = AsyncMock(spec=AsyncHttpClient)
        body = _load_json("campaign_posts_example.json")
        # Remove pagination link to avoid a second request
        body["links"] = {}
        http_client.get_json.return_value = JsonHttpResponse(json=body, status=200)

        client = _make_client(http_client)
        result = await client.get_campaign_posts("209197", datetime(2020, 1, 1, tzinfo=timezone.utc))

        assert len(result) == 3


class TestGetPostErrors:
    @pytest.mark.asyncio()
    async def test_returns_none_on_404(self) -> None:
        http_client = AsyncMock(spec=AsyncHttpClient)
        http_client.get_json.return_value = JsonHttpResponse(json={}, status=404)

        client = _make_client(http_client)
        result = await client.get_post("nonexistent")

        assert result is None

    @pytest.mark.asyncio()
    async def test_returns_none_on_server_error(self) -> None:
        http_client = AsyncMock(spec=AsyncHttpClient)
        http_client.get_json.return_value = JsonHttpResponse(json={"error": "internal"}, status=500)

        client = _make_client(http_client)
        result = await client.get_post("123")

        assert result is None

    @pytest.mark.asyncio()
    async def test_returns_post_on_success(self) -> None:
        http_client = AsyncMock(spec=AsyncHttpClient)
        body = _load_json("single_post_example.json")
        http_client.get_json.return_value = JsonHttpResponse(json=body, status=200)

        client = _make_client(http_client)
        result = await client.get_post("150496409")

        assert result is not None
        assert result.id == "150496409"
        assert "Consolita" in result.title


# =============================================================================
# Tests for PatreonApiClient.get_campaign_id_from_vanity
# =============================================================================

class TestGetCampaignIdFromVanity:
    @pytest.mark.asyncio()
    async def test_returns_campaign_id_on_success(self) -> None:
        http_client = AsyncMock(spec=AsyncHttpClient)
        body = _load_json("single_campaign_id_example.json")
        http_client.get_json.return_value = JsonHttpResponse(json=body, status=200)

        client = _make_client(http_client)
        result = await client.get_campaign_id_from_vanity("dayo")

        assert result == "146262"

    @pytest.mark.asyncio()
    async def test_returns_none_when_data_is_empty(self) -> None:
        http_client = AsyncMock(spec=AsyncHttpClient)
        http_client.get_json.return_value = JsonHttpResponse(json={"data": []}, status=200)

        client = _make_client(http_client)
        result = await client.get_campaign_id_from_vanity("nonexistent")

        assert result is None

    @pytest.mark.asyncio()
    async def test_returns_none_on_http_error(self) -> None:
        http_client = AsyncMock(spec=AsyncHttpClient)
        http_client.get_json.return_value = JsonHttpResponse(json={"error": "forbidden"}, status=403)

        client = _make_client(http_client)
        result = await client.get_campaign_id_from_vanity("dayo")

        assert result is None

    @pytest.mark.asyncio()
    async def test_returns_none_on_server_error(self) -> None:
        http_client = AsyncMock(spec=AsyncHttpClient)
        http_client.get_json.return_value = JsonHttpResponse(json={"error": "internal"}, status=500)

        client = _make_client(http_client)
        result = await client.get_campaign_id_from_vanity("dayo")

        assert result is None
