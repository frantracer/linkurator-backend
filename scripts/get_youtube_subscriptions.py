import argparse

import sys

from linkurator_core.infrastructure.config.google_secrets import GoogleClientSecrets
from linkurator_core.infrastructure.google.account_service import GoogleAccountService
from linkurator_core.infrastructure.google.youtube_service import YoutubeService


def main():
    args = argparse.ArgumentParser()
    args.add_argument("--refresh-token", required=True, help="Refresh token of the google account")
    refresh_token = args.parse_args().refresh_token

    secrets = GoogleClientSecrets()

    google_account_service = GoogleAccountService(client_id=secrets.client_id, client_secret=secrets.client_secret)

    access_token = google_account_service.generate_access_token_from_refresh_token(refresh_token=refresh_token)

    if access_token is None:
        print("Refresh token is not valid")
        sys.exit(1)

    subscriptions = YoutubeService.get_youtube_channels(access_token=access_token)
    subscriptions.sort(key=lambda s: s.title)
    for subscription in subscriptions:
        print(f'{subscription.title} -> {subscription.playlist_id} ({subscription.url})')


if __name__ == '__main__':
    main()
