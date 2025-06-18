import argparse
import asyncio
import uuid
from datetime import datetime, timezone

from linkurator_core.domain.users.external_service_credential import ExternalServiceCredential, ExternalServiceType
from linkurator_core.infrastructure.google.youtube_api_key_checker import YoutubeApiKeyChecker


async def main() -> None:
    parser = argparse.ArgumentParser(description="Check youtube api key")
    parser.add_argument("--api-key", type=str, required=True,
                        help="API key that will be used to check if it is valid")
    args = parser.parse_args()

    checker = YoutubeApiKeyChecker()

    credential = ExternalServiceCredential(
        credential_type=ExternalServiceType.YOUTUBE_API_KEY,
        credential_value=args.api_key,
        user_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    is_valid = await checker.check(credential)
    if is_valid:
        pass
    else:
        pass


if __name__ == "__main__":
    asyncio.run(main())
