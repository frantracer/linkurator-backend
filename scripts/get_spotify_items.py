import argparse
import asyncio
from dataclasses import dataclass

from linkurator_core.infrastructure.spotify.spotify_api_client import SpotifyApiClient


@dataclass
class Arguments:
    client_id: str
    client_secret: str
    show: str


def parse_arguments() -> Arguments:
    parser = argparse.ArgumentParser(description="Generate a Google refresh token")
    parser.add_argument("--client-id", required=True, help="Google client id")
    parser.add_argument("--client-secret", required=True, help="Google client secret")
    parser.add_argument("--show", required=True, help="Show name")

    args = parser.parse_args()
    return Arguments(client_id=args.client_id,
                     client_secret=args.client_secret,
                     show=args.show)


async def main() -> None:
    args = parse_arguments()

    client = SpotifyApiClient(client_id=args.client_id, client_secret=args.client_secret)

    show = await client.find_show(args.show)
    if show is None:
        return

    shows = await client.get_shows(show_ids=[show.id])
    assert show == shows[0]

    if show is not None:
        limit = 50
        offset = 0
        while offset < show.total_episodes:
            response = await client.get_show_episodes(show_id=show.id, offset=offset, limit=limit)
            for _episode in response.items:
                pass
            offset += limit

            same_response = await client.get_episodes(episode_ids=[episode.id for episode in response.items])
            assert response.items == same_response


if __name__ == "__main__":
    asyncio.run(main())
