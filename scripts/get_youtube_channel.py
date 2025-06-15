from __future__ import annotations

import argparse
import asyncio
import sys

from linkurator_core.infrastructure.google.youtube_api_client import YoutubeApiClient, YoutubeChannel


async def main() -> None:
    args = argparse.ArgumentParser()
    args.add_argument("--api-key", required=True, help="API key to access the Youtube API")
    args.add_argument("--name", help="Name of the Youtube channel")
    args.add_argument("--id", help="ID of the Youtube channel")

    api_key = args.parse_args().api_key
    channel_name = args.parse_args().name
    channel_id = args.parse_args().id

    if channel_name is None and channel_id is None:
        sys.exit(1)

    client = YoutubeApiClient()

    channel: YoutubeChannel | None = None
    if channel_name is not None:
        channel = await client.get_youtube_channel_from_name(api_key=api_key, channel_name=channel_name)

    if channel_id is not None:
        channel = await client.get_youtube_channel(api_key=api_key, channel_id=channel_id)

    if channel is None:
        pass
    else:
        pass


if __name__ == "__main__":
    asyncio.run(main())
