"""Tests for the authentication module."""

import os
from unittest import mock
import json
from datetime import datetime, timezone, timedelta
import pytest
import requests
from dns_services_gateway.auth import TokenManager, Token
from dns_services_gateway.exceptions import AuthenticationError, TokenError
from dns_services_gateway.config import DNSServicesConfig


@pytest.fixture
def token_manager():
    config = DNSServicesConfig(username="test", password="test")
    return TokenManager(config)


@pytest.fixture
def mock_response():
    response = mock.Mock()
    response.json.return_value = {"token": "test_token"}
    response.raise_for_status.return_value = None
    return response


def test_token_is_expired():
    # Test non-expired token
    token = Token(
        token="test",
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    assert not token.is_expired

    # Test expired token
    token = Token(
        token="test",
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    assert token.is_expired

    # Test token without expiration
    token = Token(token="test", created_at=datetime.now(timezone.utc))
    assert not token.is_expired


def test_download_token_success(token_manager, mock_response, tmp_path):
    with mock.patch("requests.Session.post", return_value=mock_response):
        with mock.patch("getpass.getpass", return_value="password"):
            token_path = tmp_path / "token"
            result = token_manager.download_token(
                username="test_user", output_path=str(token_path)
            )

            assert result == str(token_path)
            assert token_path.exists()

            # Check file permissions
            stat_info = os.stat(token_path)
            assert stat_info.st_mode & 0o777 == 0o600

            # Verify token content
            token_data = json.loads(token_path.read_text())
            assert "token" in token_data
            assert token_data["token"] == "test_token"


def test_download_token_with_password(token_manager, mock_response, tmp_path):
    """Test token download with provided password (no getpass)."""
    with mock.patch("requests.Session.post", return_value=mock_response):
        token_path = tmp_path / "token"
        result = token_manager.download_token(
            username="test_user", password="test_pass", output_path=str(token_path)
        )

        assert result == str(token_path)
        assert token_path.exists()


def test_download_token_creates_parent_dirs(token_manager, mock_response, tmp_path):
    """Test that parent directories are created if they don't exist."""
    with mock.patch("requests.Session.post", return_value=mock_response):
        token_path = tmp_path / "nested" / "dirs" / "token"
        result = token_manager.download_token(
            username="test_user", password="test_pass", output_path=str(token_path)
        )

        assert result == str(token_path)
        assert token_path.exists()
        assert token_path.parent.exists()


def test_download_token_no_token_in_response(token_manager, tmp_path):
    """Test error when API response doesn't contain a token."""
    mock_resp = mock.Mock()
    mock_resp.json.return_value = {"error": "Invalid credentials"}
    mock_resp.raise_for_status.return_value = None

    with mock.patch("requests.Session.post", return_value=mock_resp):
        with pytest.raises(AuthenticationError, match="No token in response"):
            token_manager.download_token(
                username="test_user",
                password="test_pass",
                output_path=str(tmp_path / "token"),
            )


def test_download_token_failure(token_manager):
    with mock.patch("requests.Session.post") as mock_post:
        mock_post.side_effect = requests.RequestException("Connection error")
        with pytest.raises(AuthenticationError):
            token_manager.download_token(username="test_user", password="test_pass")


def test_load_token_success(tmp_path):
    token_path = tmp_path / "token"
    token_data = {
        "token": "test_token",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    token_path.write_text(json.dumps(token_data))
    os.chmod(token_path, 0o600)

    token = TokenManager.load_token(token_path)
    assert isinstance(token, Token)
    assert token.token == "test_token"


def test_load_token_with_expiry(tmp_path):
    """Test loading token with expiration date."""
    token_path = tmp_path / "token"
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    token_data = {
        "token": "test_token",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": expires_at.isoformat(),
    }
    token_path.write_text(json.dumps(token_data))
    os.chmod(token_path, 0o600)

    token = TokenManager.load_token(token_path)
    assert isinstance(token, Token)
    assert token.token == "test_token"
    assert token.expires_at is not None
    assert not token.is_expired


def test_load_token_file_not_found():
    """Test error when token file doesn't exist."""
    with pytest.raises(TokenError, match="Token file not found"):
        TokenManager.load_token("/nonexistent/path")


def test_load_token_invalid_permissions(tmp_path):
    token_path = tmp_path / "token"
    token_data = {
        "token": "test_token",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    token_path.write_text(json.dumps(token_data))
    os.chmod(token_path, 0o644)  # Wrong permissions

    with pytest.raises(TokenError, match="incorrect permissions"):
        TokenManager.load_token(token_path)


def test_load_token_invalid_format(tmp_path):
    token_path = tmp_path / "token"
    token_path.write_text("invalid json")
    os.chmod(token_path, 0o600)

    with pytest.raises(TokenError, match="Invalid token file format"):
        TokenManager.load_token(token_path)
