
import pytest

from linkurator_core.infrastructure.config.settings import SpotifySettings


def test_spotify_client_secrets_rejects_empty_list() -> None:
    """Test that empty credential list is rejected."""
    with pytest.raises(ValueError, match="At least one Spotify credential pair must be provided"):
        SpotifySettings(credentials=[])
