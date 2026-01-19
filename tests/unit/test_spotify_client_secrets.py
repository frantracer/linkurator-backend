import json
import tempfile
from pathlib import Path

import pytest

from linkurator_core.infrastructure.config.spotify import SpotifyClientSecrets


def test_spotify_client_secrets_from_file() -> None:
    """Test loading credentials from new multi-credential format."""
    json_file = [
        {"client_id": "id1", "client_secret": "secret1"},
        {"client_id": "id2", "client_secret": "secret2"},
        {"client_id": "id3", "client_secret": "secret3"},
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(json_file, f)
        temp_path = f.name

    try:
        secrets = SpotifyClientSecrets.from_file(file_path=temp_path)
        assert len(secrets.credentials) == 3
        assert secrets.credentials[0].client_id == "id1"
        assert secrets.credentials[0].client_secret == "secret1"
        assert secrets.credentials[1].client_id == "id2"
        assert secrets.credentials[1].client_secret == "secret2"
        assert secrets.credentials[2].client_id == "id3"
        assert secrets.credentials[2].client_secret == "secret3"
    finally:
        Path(temp_path).unlink()


def test_spotify_client_secrets_rejects_empty_list() -> None:
    """Test that empty credential list is rejected."""
    empty_format: list[dict[str, str]] = []

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(empty_format, f)
        temp_path = f.name

    try:
        with pytest.raises(ValueError, match="No Spotify credentials found"):
            SpotifyClientSecrets.from_file(file_path=temp_path)
    finally:
        Path(temp_path).unlink()


def test_spotify_client_secrets_rejects_invalid_format() -> None:
    """Test that invalid format is rejected."""
    invalid_format = "not a json"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(invalid_format, f)
        temp_path = f.name

    try:
        with pytest.raises(TypeError):
            SpotifyClientSecrets.from_file(file_path=temp_path)
    finally:
        Path(temp_path).unlink()
