from datetime import datetime

from linkurator_core.domain.users.external_credentials_checker_service import ExternalCredentialsCheckerService
from linkurator_core.domain.users.external_service_credential import ExternalServiceCredential, ExternalServiceType
from linkurator_core.infrastructure.google.youtube_api_client import YoutubeApiClient


class YoutubeApiKeyChecker(ExternalCredentialsCheckerService):
    async def check(self, credential: ExternalServiceCredential) -> bool:

        if credential.credential_type != ExternalServiceType.YOUTUBE_API_KEY:
            raise ValueError('Invalid credential type')

        try:
            client = YoutubeApiClient()
            videos = await client.get_youtube_videos_from_playlist(
                api_key=credential.credential_value,
                playlist_id='UUYVFW8d1p41UM-ZGzzYYB2w',
                from_date=datetime(2020, 1, 1)
            )
            if len(videos) >= 0:
                return True
            return False
        except Exception as ex:  # pylint: disable=broad-except
            print(ex)
            return False
