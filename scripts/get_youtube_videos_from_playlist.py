import argparse
import asyncio
import logging
from datetime import datetime, timezone

import logfire

from linkurator_core.infrastructure.config.settings import ApplicationSettings
from linkurator_core.infrastructure.google.youtube_api_client import YoutubeApiClient


async def main() -> None:
    args = argparse.ArgumentParser()
    args.add_argument("--playlist-id", required=True, help="Playlist ID of the youtube channel main playlist")
    args.add_argument("--from-date", required=True, help="From date in format YYYY-MM-DD:HH:MM:SSZ",
                      type=lambda s: datetime.strptime(s, "%Y-%m-%d:%H:%M:%S").replace(tzinfo=timezone.utc))
    parsed_args = args.parse_args()
    playlist_id = parsed_args.playlist_id
    from_date = parsed_args.from_date

    settings = ApplicationSettings.from_file()
    logfire.configure(token=settings.logging.logfire.token, scrubbing=False)

    client = YoutubeApiClient()
    videos = await client.get_youtube_videos_from_playlist(
        api_key=settings.google.youtube_api_keys[0],
        playlist_id=playlist_id,
        from_date=from_date)

    if len(videos) == 0:
        logging.info("No videos found in the playlist")
    else:
        for _video in videos:
            logging.info(f"Title: {_video.title}")
            logging.info(f"Description: {_video.description}")
            logging.info(f"ID: {_video.video_id}")
            logging.info(f"Published at: {_video.published_at}")
            logging.info(f"URL: {_video.url}")
            logging.info("-----\n")


if __name__ == "__main__":
    asyncio.run(main())
