import argparse
import asyncio
from datetime import datetime

from linkurator_core.infrastructure.config.google_secrets import GoogleClientSecrets
from linkurator_core.infrastructure.google.youtube_api_client import YoutubeApiClient


async def main() -> None:
    args = argparse.ArgumentParser()
    args.add_argument("--playlist-id", required=True, help="Playlist ID of the youtube channel main playlist")
    args.add_argument("--from-date", required=True, help="From date in format YYYY-MM-DD:HH:MM:SSZ",
                      type=lambda s: datetime.strptime(s, "%Y-%m-%d:%H:%M:%S"))
    parsed_args = args.parse_args()
    playlist_id = parsed_args.playlist_id
    from_date = parsed_args.from_date

    secrets = GoogleClientSecrets()

    client = YoutubeApiClient()
    videos = await client.get_youtube_videos_from_playlist(
        api_key=secrets.api_keys[0],
        playlist_id=playlist_id,
        from_date=from_date)

    for _video in videos:
        pass



if __name__ == "__main__":
    asyncio.run(main())
