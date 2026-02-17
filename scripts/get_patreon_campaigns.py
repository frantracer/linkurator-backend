import argparse
import asyncio
import logging
from datetime import timedelta

from linkurator_core.domain.common.utils import datetime_now
from linkurator_core.infrastructure.asyncio_impl.http_client import AsyncHttpClient
from linkurator_core.infrastructure.config.settings import ApplicationSettings
from linkurator_core.infrastructure.logger import configure_logging
from linkurator_core.infrastructure.patreon.patreon_api_client import PatreonApiClient


async def main() -> None:
    """Retrieve all Patreon campaigns for the configured user."""
    parser = argparse.ArgumentParser(description="Get Patreon campaigns for the configured user")
    parser.add_argument("--access-token", required=True, help="Patreon access token")
    parser.add_argument("--days", type=int, default=365, help="Number of days to look back for posts")
    args = parser.parse_args()

    settings = ApplicationSettings.from_file()
    configure_logging(settings.logging)

    if settings.patreon is None:
        logging.error("Patreon settings not configured")
        return

    http_client = AsyncHttpClient(contact_email=settings.google.service_account_email)
    http_client_proxy = http_client
    if settings.vpn.enabled:
        http_client_proxy = AsyncHttpClient(
            proxy_url=f"http://localhost:{settings.vpn.http_proxy_port}",
        )

    client = PatreonApiClient(
        client_id=settings.patreon.client_id,
        client_secret=settings.patreon.client_secret,
        http_client=http_client,
        http_client_proxy=http_client_proxy,
    )

    access_token: str = args.access_token

    # Get campaigns for the user
    memberships = await client.get_current_user_memberships(access_token)

    if len(memberships) == 0:
        logging.info("No campaigns found for this user")
        return

    logging.info("Found %d memberships(s):", len(memberships))
    for membership in memberships:
        campaign = await client.get_campaign(membership.campaign_id)
        if campaign is None:
            logging.error("Failed to fetch campaign details for ID: %s", membership.campaign_id)
            continue

        logging.info("- ID: %s", campaign.id)
        logging.info("  Vanity: %s", campaign.vanity)
        logging.info("  URL: %s", campaign.url)
        logging.info("  Name: %s", campaign.creation_name)
        logging.info("  Summary: %s", campaign.summary)
        logging.info("  Image URL: %s", campaign.avatar_photo_image_urls.default)
        logging.info("")

        posts = await client.get_campaign_posts(campaign.id, datetime_now() - timedelta(days=args.days))

        for post in posts:
            logging.info("  - ID: %s", post.id)
            logging.info("    Title: %s", post.title)
            logging.info("    URL: %s", post.url)
            logging.info("    Published At: %s", str(post.published_at))
            logging.info("    Thumbnail URL: %s", str(post.image_url))
            logging.info("    Duration: %s seconds", str(post.duration_seconds))
            logging.info("")

        logging.info("    Found %d post(s) for this campaign:", len(posts))
        logging.info("")

        if len(posts) > 0:
            first_post = await client.get_post(posts[0].id)
            if first_post is None:
                logging.error("Failed to fetch details for post ID: %s", posts[0].id)
                continue

            logging.info("First post details:")
            logging.info("  - ID: %s", first_post.id)
            logging.info("    Title: %s", first_post.title)
            logging.info("    URL: %s", first_post.url)
            logging.info("    Published At: %s", str(first_post.published_at))
            logging.info("    Thumbnail URL: %s", str(first_post.image_url))
            logging.info("    Duration: %s seconds", str(first_post.duration_seconds))


if __name__ == "__main__":
    asyncio.run(main())
