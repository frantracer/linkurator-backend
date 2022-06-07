import argparse
from unittest.mock import MagicMock

from linkurator_core.infrastructure.config.google_secrets import GoogleClientSecrets
from linkurator_core.infrastructure.google.account_service import GoogleAccountService
from linkurator_core.infrastructure.google.youtube_service import YoutubeService


def main():
    args = argparse.ArgumentParser()
    args.add_argument("--refresh-token", required=True, help="Refresh token of the google account")
    refresh_token = args.parse_args().refresh_token

    secrets = GoogleClientSecrets()

    google_account_service = GoogleAccountService(client_id=secrets.client_id, client_secret=secrets.client_secret)

    youtube_service = YoutubeService(google_account_service=google_account_service, user_repository=MagicMock())

    subscriptions = youtube_service.get_channels(refresh_token)
    for subscription in subscriptions:
        print(f'{subscription.title} -> {subscription.url}')


if __name__ == '__main__':
    main()
