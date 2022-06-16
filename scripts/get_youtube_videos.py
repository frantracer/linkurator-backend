import argparse
from datetime import datetime
from unittest.mock import MagicMock

from linkurator_core.infrastructure.config.google_secrets import GoogleClientSecrets
from linkurator_core.infrastructure.google.account_service import GoogleAccountService
from linkurator_core.infrastructure.google.youtube_service import YoutubeService


def main():
    args = argparse.ArgumentParser()
    args.add_argument("--refresh-token", required=True, help="Refresh token of the google account")
    args.add_argument("--playlist-id", required=True, help="Playlist ID of the youtube channel main playlist")
    args.add_argument('--from-date', required=True, help='From date in format YYYY-MM-DD:HH:MM:SSZ',
                      type=lambda s: datetime.strptime(s, '%Y-%m-%d:%H:%M:%S'))
    parsed_args = args.parse_args()
    refresh_token = parsed_args.refresh_token
    playlist_id = parsed_args.playlist_id
    from_date = parsed_args.from_date

    secrets = GoogleClientSecrets()

    google_account_service = GoogleAccountService(client_id=secrets.client_id, client_secret=secrets.client_secret)

    youtube_service = YoutubeService(google_account_service=google_account_service, user_repository=MagicMock())

    videos = youtube_service.get_youtube_videos(
        refresh_token=refresh_token,
        playlist_id=playlist_id,
        from_date=from_date)

    for video in videos:
        print(f'[{video.published_at}] {video.title} -> {video.url}')

    print(f"Total {len(videos)} videos")


if __name__ == '__main__':
    main()
