import argparse
import asyncio
import sys

from linkurator_core.infrastructure.config.google_secrets import GoogleClientSecrets
from linkurator_core.infrastructure.google.account_service import GoogleAccountService
from linkurator_core.infrastructure.google.youtube_service import YoutubeApiClient


async def main():
    args = argparse.ArgumentParser()
    args.add_argument("--refresh-token", required=True, help="Refresh token of the google account")
    args.add_argument("--api-key", required=True, help="API key to access the Youtube API")
    refresh_token = args.parse_args().refresh_token
    api_key = args.parse_args().api_key

    client = YoutubeApiClient()

    secrets = GoogleClientSecrets()

    google_account_service = GoogleAccountService(client_id=secrets.client_id, client_secret=secrets.client_secret)

    access_token = google_account_service.generate_access_token_from_refresh_token(refresh_token=refresh_token)

    if access_token is None:
        print("Refresh token is not valid")
        sys.exit(1)

    subscriptions = await client.get_youtube_subscriptions(access_token=access_token, api_key=api_key)
    subscriptions.sort(key=lambda s: s.title)
    print(f'\nSubscriptions ({len(subscriptions)}):')
    for subscription in subscriptions:
        print(f'{subscription.title} -> {subscription.playlist_id} ({subscription.url})')


if __name__ == '__main__':
    asyncio.run(main())
