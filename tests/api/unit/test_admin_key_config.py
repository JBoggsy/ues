"""Tests for admin key configuration: pre-set secrets, key file output, and env vars.

This module tests the automated admin key retrieval features:
- Pre-set admin key via UES_ADMIN_KEY environment variable
- Admin key file output via UES_ADMIN_KEY_FILE environment variable / --admin-key-file CLI flag
- Minimum secret length validation
- Key file format and permissions

Test Organization:
- TestPresetAdminKey: Tests for pre-set admin key secrets in the registry
- TestInitializeRegistryWithSecret: Tests for initialize_api_key_registry(admin_secret=...)
- TestWriteAdminKeyFile: Tests for _write_admin_key_file() helper
- TestLifespanKeyConfig: Tests for lifespan env var handling
"""

import json
import os
import stat
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from ues.api.auth import (
    APIKeyRegistry,
    get_api_key_registry,
    initialize_api_key_registry,
    shutdown_api_key_registry,
)
from ues.main import _write_admin_key_file
from ues.models.api_key import hash_secret


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def registry():
    """Provide a fresh APIKeyRegistry for each test."""
    return APIKeyRegistry()


@pytest.fixture(autouse=True)
def reset_global_registry():
    """Reset the global registry before and after each test."""
    import ues.api.auth as auth_module

    original_registry = auth_module._api_key_registry
    auth_module._api_key_registry = None
    yield
    auth_module._api_key_registry = original_registry


@pytest.fixture
def tmp_key_file(tmp_path):
    """Provide a temporary file path for key output."""
    return str(tmp_path / "admin-key.json")


# =============================================================================
# Pre-set Admin Key Tests
# =============================================================================


class TestPresetAdminKey:
    """Tests for creating an admin key with a pre-set secret."""

    def test_preset_secret_is_used(self, registry):
        """Test that a provided secret is used instead of generating one."""
        preset_secret = "a" * 64  # 64-char hex-like string
        secret, key = registry.create_admin_key(secret=preset_secret)

        assert secret == preset_secret
        assert key.name == "Admin Key"
        assert key.permissions == ["*"]
        assert key.is_active is True
        assert key.key_hash == hash_secret(preset_secret)

    def test_preset_secret_validates_via_registry(self, registry):
        """Test that a preset secret can be used to authenticate."""
        preset_secret = "b" * 64
        _, key = registry.create_admin_key(secret=preset_secret)

        validated = registry.validate_key(preset_secret)
        assert validated is not None
        assert validated.key_id == key.key_id

    def test_random_secret_still_works(self, registry):
        """Test that omitting secret falls back to random generation."""
        secret, key = registry.create_admin_key()

        assert len(secret) == 64  # 32 bytes hex
        assert key.name == "Admin Key"
        assert key.permissions == ["*"]

    def test_preset_secret_minimum_length(self, registry):
        """Test that secrets shorter than 32 chars are rejected."""
        short_secret = "x" * 31

        with pytest.raises(ValueError) as exc_info:
            registry.create_admin_key(secret=short_secret)

        assert "at least" in str(exc_info.value)
        assert "32" in str(exc_info.value)

    def test_preset_secret_exactly_minimum_length(self, registry):
        """Test that a secret of exactly 32 chars is accepted."""
        secret_32 = "y" * 32
        secret, key = registry.create_admin_key(secret=secret_32)

        assert secret == secret_32
        assert key.key_hash == hash_secret(secret_32)

    def test_preset_secret_long_string(self, registry):
        """Test that very long secrets are accepted."""
        long_secret = "z" * 256
        secret, key = registry.create_admin_key(secret=long_secret)

        assert secret == long_secret

    def test_preset_secret_non_hex(self, registry):
        """Test that non-hex secrets are accepted (any string >= 32 chars)."""
        non_hex_secret = "this-is-not-hex-but-long-enough!!"  # 34 chars
        secret, key = registry.create_admin_key(secret=non_hex_secret)

        assert secret == non_hex_secret
        validated = registry.validate_key(non_hex_secret)
        assert validated is not None

    def test_preset_secret_empty_string_rejected(self, registry):
        """Test that an empty string is rejected."""
        with pytest.raises(ValueError):
            registry.create_admin_key(secret="")

    def test_create_admin_key_still_only_once(self, registry):
        """Test that admin key can still only be created once with preset."""
        registry.create_admin_key(secret="a" * 64)

        with pytest.raises(ValueError) as exc_info:
            registry.create_admin_key(secret="b" * 64)

        assert "Admin key already exists" in str(exc_info.value)


# =============================================================================
# Initialize Registry with Secret Tests
# =============================================================================


class TestInitializeRegistryWithSecret:
    """Tests for initialize_api_key_registry(admin_secret=...)."""

    def test_with_preset_secret(self):
        """Test global initialization with a pre-set secret."""
        preset = "c" * 64
        secret, key = initialize_api_key_registry(admin_secret=preset)

        assert secret == preset
        assert key.permissions == ["*"]

        # Registry should be accessible
        registry = get_api_key_registry()
        validated = registry.validate_key(preset)
        assert validated is not None
        assert validated.key_id == key.key_id

    def test_without_preset_secret(self):
        """Test global initialization without a preset (random generation)."""
        secret, key = initialize_api_key_registry()

        assert len(secret) == 64
        assert key.permissions == ["*"]

    def test_with_too_short_secret_raises(self):
        """Test that short secrets raise ValueError during init."""
        with pytest.raises(ValueError):
            initialize_api_key_registry(admin_secret="short")

    def test_none_secret_is_random(self):
        """Test that None admin_secret generates a random key."""
        secret, key = initialize_api_key_registry(admin_secret=None)

        assert len(secret) == 64
        assert key.name == "Admin Key"


# =============================================================================
# Write Admin Key File Tests
# =============================================================================


class TestWriteAdminKeyFile:
    """Tests for _write_admin_key_file() helper function."""

    def test_writes_valid_json(self, tmp_key_file):
        """Test that key file contains valid JSON with expected fields."""
        result = _write_admin_key_file(
            tmp_key_file, "secret123" + "x" * 50, "ues_abc123"
        )

        assert result is True
        data = json.loads(Path(tmp_key_file).read_text())
        assert data["secret"] == "secret123" + "x" * 50
        assert data["key_id"] == "ues_abc123"

    def test_json_has_only_expected_fields(self, tmp_key_file):
        """Test that key file contains exactly the expected fields."""
        _write_admin_key_file(tmp_key_file, "s" * 64, "ues_id123")

        data = json.loads(Path(tmp_key_file).read_text())
        assert set(data.keys()) == {"secret", "key_id"}

    @pytest.mark.skipif(
        sys.platform == "win32", reason="Unix file permissions"
    )
    def test_file_permissions_unix(self, tmp_key_file):
        """Test that key file has 0600 permissions on Unix."""
        _write_admin_key_file(tmp_key_file, "s" * 64, "ues_id123")

        file_stat = os.stat(tmp_key_file)
        file_mode = stat.S_IMODE(file_stat.st_mode)
        assert file_mode == 0o600

    def test_creates_parent_directories(self, tmp_path):
        """Test that missing parent directories are created."""
        nested_path = str(tmp_path / "deep" / "nested" / "dir" / "key.json")
        result = _write_admin_key_file(nested_path, "s" * 64, "ues_id123")

        assert result is True
        assert Path(nested_path).exists()

    def test_returns_false_on_invalid_path(self):
        """Test that invalid paths return False instead of raising."""
        # /dev/null/impossible is not a valid directory
        result = _write_admin_key_file(
            "/dev/null/impossible/key.json", "s" * 64, "ues_id123"
        )

        assert result is False

    def test_file_ends_with_newline(self, tmp_key_file):
        """Test that the key file ends with a newline."""
        _write_admin_key_file(tmp_key_file, "s" * 64, "ues_id123")

        content = Path(tmp_key_file).read_text()
        assert content.endswith("\n")

    def test_file_is_pretty_printed(self, tmp_key_file):
        """Test that JSON is human-readable (indented)."""
        _write_admin_key_file(tmp_key_file, "s" * 64, "ues_id123")

        content = Path(tmp_key_file).read_text()
        # Pretty-printed JSON has multiple lines
        assert len(content.strip().split("\n")) > 1


# =============================================================================
# Lifespan Environment Variable Tests
# =============================================================================


class TestLifespanKeyConfig:
    """Tests for lifespan handling of UES_ADMIN_KEY and UES_ADMIN_KEY_FILE env vars.

    These tests exercise the lifespan context manager indirectly by running
    the FastAPI app with a test client and verifying the admin key behavior.
    """

    def test_preset_key_via_env_var(self, monkeypatch):
        """Test that UES_ADMIN_KEY env var is read and used."""
        from fastapi.testclient import TestClient

        from ues.main import app

        preset_secret = "env_var_preset_key_" + "a" * 45  # > 32 chars
        monkeypatch.setenv("UES_ADMIN_KEY", preset_secret)

        with TestClient(app) as client:
            # The preset secret should authenticate successfully
            response = client.get(
                "/simulation/status",
                headers={"X-API-Key": preset_secret},
            )
            assert response.status_code == 200

    def test_random_key_when_no_env_var(self, monkeypatch):
        """Test that without UES_ADMIN_KEY, a random key is generated."""
        monkeypatch.delenv("UES_ADMIN_KEY", raising=False)
        monkeypatch.delenv("UES_ADMIN_KEY_FILE", raising=False)

        from fastapi.testclient import TestClient

        from ues.main import app

        with TestClient(app) as client:
            # A hardcoded string should NOT work
            response = client.get(
                "/simulation/status",
                headers={"X-API-Key": "this_is_not_the_key"},
            )
            assert response.status_code == 401

    def test_key_file_written_via_env_var(self, monkeypatch, tmp_key_file):
        """Test that UES_ADMIN_KEY_FILE env var triggers file output."""
        monkeypatch.delenv("UES_ADMIN_KEY", raising=False)
        monkeypatch.setenv("UES_ADMIN_KEY_FILE", tmp_key_file)

        from fastapi.testclient import TestClient

        from ues.main import app

        with TestClient(app):
            pass  # Lifespan runs on enter

        # Verify the key file was written
        assert Path(tmp_key_file).exists()
        data = json.loads(Path(tmp_key_file).read_text())
        assert "secret" in data
        assert "key_id" in data
        assert len(data["secret"]) == 64  # random key

    def test_key_file_with_preset_key(self, monkeypatch, tmp_key_file):
        """Test that both UES_ADMIN_KEY and UES_ADMIN_KEY_FILE work together.
        
        When both are set, the preset key is used and *not* written to file
        (since the caller already knows the key).
        """
        preset_secret = "d" * 64
        monkeypatch.setenv("UES_ADMIN_KEY", preset_secret)
        monkeypatch.setenv("UES_ADMIN_KEY_FILE", tmp_key_file)

        from fastapi.testclient import TestClient

        from ues.main import app

        with TestClient(app) as client:
            response = client.get(
                "/simulation/status",
                headers={"X-API-Key": preset_secret},
            )
            assert response.status_code == 200

        # When UES_ADMIN_KEY is set, the key file should NOT be written
        # (the caller already has the key)
        assert not Path(tmp_key_file).exists()

    def test_key_file_secret_authenticates(self, monkeypatch, tmp_key_file):
        """Test that the secret written to the key file actually works."""
        monkeypatch.delenv("UES_ADMIN_KEY", raising=False)
        monkeypatch.setenv("UES_ADMIN_KEY_FILE", tmp_key_file)

        from fastapi.testclient import TestClient

        from ues.main import app

        with TestClient(app) as client:
            # Read the file and use the secret
            data = json.loads(Path(tmp_key_file).read_text())
            response = client.get(
                "/simulation/status",
                headers={"X-API-Key": data["secret"]},
            )
            assert response.status_code == 200
