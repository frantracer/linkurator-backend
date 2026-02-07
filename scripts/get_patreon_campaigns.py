import asyncio
import logging

from linkurator_core.infrastructure.config.settings import ApplicationSettings
from linkurator_core.infrastructure.logger import configure_logging
from linkurator_core.infrastructure.patreon.patreon_api_client import PatreonApiClient


async def main() -> None:
    """Retrieve all Patreon campaigns for the configured user."""
    settings = ApplicationSettings.from_file()
    configure_logging(settings.logging)

    if settings.patreon is None:
        logging.error("Patreon settings not configured")
        return

    client = PatreonApiClient(
        client_id=settings.patreon.client_id,
        client_secret=settings.patreon.client_secret,
        refresh_token=settings.patreon.refresh_token,
    )

    # Get access token from refresh token
    access_token = ""

    # Get campaigns for the user
    campaigns = await client.get_current_user_memberships(access_token)

    if len(campaigns) == 0:
        logging.info("No campaigns found for this user")
        return

    logging.info("Found %d campaign(s):", len(campaigns))
    for campaign in campaigns:
        logging.info("  - ID: %s", campaign.id)
        logging.info("    Name: %s", campaign.name)
        logging.info("    URL: %s", campaign.url)
        logging.info("    Vanity: %s", campaign.vanity)
        logging.info("    Summary: %s", campaign.summary if campaign.summary else "N/A")
        logging.info("")

        posts = await client.fetch_patreon_posts(campaign.id)

        logging.info("    Found %d post(s) for this campaign:", len(posts))
        for post in posts:
            logging.info("      - ID: %s", post.id)
            logging.info("        Title: %s", post.title)
            logging.info("        URL: %s", post.url)
            logging.info("        Published At: %s", post.published_at if post.published_at else "N/A")
            logging.info("        Thumbnail URL: %s", post.image_url if post.image_url else "N/A")
            logging.info("")

if __name__ == "__main__":
    asyncio.run(main())
