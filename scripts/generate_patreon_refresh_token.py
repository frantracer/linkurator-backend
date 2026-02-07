import asyncio
import logging
from urllib.parse import parse_qs, urlencode, urlparse

import aiohttp

from linkurator_core.infrastructure.config.settings import ApplicationSettings
from linkurator_core.infrastructure.logger import configure_logging

PATREON_BASE_URL = "https://www.patreon.com"
REDIRECT_URI = "http://localhost:9000/sync/patreon_auth"


async def exchange_code_for_tokens(
    client_id: str,
    client_secret: str,
    code: str,
) -> tuple[str, str] | None:
    """Exchange authorization code for access and refresh tokens."""
    token_url = f"{PATREON_BASE_URL}/api/oauth2/token"
    data = {
        "code": code,
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(token_url, data=data) as response:
            if response.status == 200:
                body = await response.json()
                return body["access_token"], body["refresh_token"]
            logging.error("Failed to exchange code: %s -> %s", response.status, await response.text())
            return None


async def main() -> None:
    """Generate a new Patreon refresh token through OAuth flow."""
    settings = ApplicationSettings.from_file()
    configure_logging(settings.logging)

    if settings.patreon is None:
        logging.error("Patreon settings not configured")
        return

    client_id = settings.patreon.client_id
    client_secret = settings.patreon.client_secret

    # Build authorization URL
    scopes = "identity identity.memberships campaigns campaigns.posts"
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "scope": scopes,
    }
    auth_url = f"{PATREON_BASE_URL}/oauth2/authorize?{urlencode(params)}"

    print("\n" + "=" * 60)  # noqa: T201
    print("PATREON OAUTH SETUP")  # noqa: T201
    print("=" * 60)  # noqa: T201
    print("\n1. Open this URL in your browser:\n")  # noqa: T201
    print(auth_url)  # noqa: T201
    print("\n2. Authorize the application")  # noqa: T201
    print("\n3. You will be redirected to a URL like:")  # noqa: T201
    print(f"   {REDIRECT_URI}?code=XXXXX")  # noqa: T201
    print("\n4. Copy and paste the FULL redirect URL below:\n")  # noqa: T201

    redirect_url_str = input("Redirect URL: ").strip()

    # Parse the code from the redirect URL
    url = urlparse(redirect_url_str)
    query_params = parse_qs(url.query)

    if "code" not in query_params:
        logging.error("No code found in the redirect URL")
        return

    code = query_params["code"][0]

    # Exchange code for tokens
    result = await exchange_code_for_tokens(client_id, client_secret, code)

    if result is None:
        logging.error("Failed to get tokens")
        return

    access_token, refresh_token = result

    print("\n" + "=" * 60)  # noqa: T201
    print("SUCCESS!")  # noqa: T201
    print("=" * 60)  # noqa: T201
    print(f"\nAccess Token:\n{access_token}")  # noqa: T201
    print(f"\nRefresh Token:\n{refresh_token}")  # noqa: T201
    print("\nUpdate your config with the new refresh_token value above.")  # noqa: T201
    print("=" * 60 + "\n")  # noqa: T201


if __name__ == "__main__":
    asyncio.run(main())
