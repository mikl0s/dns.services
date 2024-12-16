"""Tests for the authentication module."""

import os
from unittest import mock
import json
from datetime import datetime, timezone, timedelta
import pytest
import requests
from pydantic import SecretStr
from dns_services_gateway.auth import TokenManager, Token
from dns_services_gateway.exceptions import AuthenticationError, TokenError
from dns_services_gateway.config import DNSServicesConfig, AuthType


@pytest.fixture
def token_manager():
    config = DNSServicesConfig(
        username="test",
        password=SecretStr("test"),
        base_url="https://api.test",
        token_path=None,
        verify_ssl=False,  # Disable SSL verification
        timeout=30,
        debug=False,
        auth_type=AuthType.JWT,
    )
    manager = TokenManager(config)
    manager._session.verify = False  # Explicitly disable SSL verification
    return manager


@pytest.fixture
def mock_response():
    response = mock.Mock(spec=requests.Response)
    response.json.return_value = {"token": "test_token"}
    response.raise_for_status.return_value = None
    response.status_code = 200
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
    """Test successful token download."""
    token_manager._session.request = mock.Mock(return_value=mock_response)
    token_path = tmp_path / "token"
    result = token_manager.download_token(
        username="test_user", password="test_pass", output_path=str(token_path)
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
    assert "created_at" in token_data


def test_download_token_with_password(token_manager, mock_response, tmp_path):
    """Test token download with provided password."""
    token_manager._session.request = mock.Mock(return_value=mock_response)
    token_path = tmp_path / "token"
    result = token_manager.download_token(
        username="test_user", password="test_pass", output_path=str(token_path)
    )

    assert result == str(token_path)
    assert token_path.exists()


def test_download_token_creates_parent_dirs(token_manager, mock_response, tmp_path):
    """Test that parent directories are created if they don't exist."""
    token_manager._session.request = mock.Mock(return_value=mock_response)
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
    mock_resp.status_code = 200

    token_manager._session.request = mock.Mock(return_value=mock_resp)
    with pytest.raises(AuthenticationError, match="No token in response"):
        token_manager.download_token(
            username="test_user",
            password="test_pass",
            output_path=str(tmp_path / "token"),
        )


def test_download_token_failure(token_manager):
    with mock.patch("requests.Session.request") as mock_request:
        mock_request.side_effect = requests.RequestException("Connection error")
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


def test_token_manager_request_methods(token_manager, mock_response):
    """Test TokenManager's HTTP request methods."""
    token_manager._session.request = mock.Mock(return_value=mock_response)

    # Test GET request
    response = token_manager.get("https://api.test/endpoint")
    token_manager._session.request.assert_called_with(
        "GET", "https://api.test/endpoint", headers={}
    )
    assert response == mock_response

    # Test POST request
    data = {"key": "value"}
    response = token_manager.post("https://api.test/endpoint", json=data)
    token_manager._session.request.assert_called_with(
        "POST", "https://api.test/endpoint", json=data, headers={}
    )
    assert response == mock_response


def test_secure_write_token_permission_error(token_manager, tmp_path):
    """Test _secure_write_token handles permission errors."""
    token_path = tmp_path / "token"

    # Create a read-only directory
    token_path.parent.mkdir(mode=0o500, exist_ok=True)

    # Make the directory read-only for the current user
    os.chmod(token_path.parent, 0o444)

    with pytest.raises(TokenError, match="Failed to save token"):
        token_manager._secure_write_token({"token": "test_token"}, token_path)

    # Restore permissions for cleanup
    os.chmod(token_path.parent, 0o755)


def test_token_manager_session_property(token_manager):
    """Test TokenManager's session property."""
    session = token_manager.session
    assert isinstance(session, requests.Session)
    assert session.verify == token_manager.config.verify_ssl


def test_basic_auth_header_generation():
    """Test Basic Authentication header generation."""
    config = DNSServicesConfig(
        username="test",
        password=SecretStr("test"),
        base_url="https://dns.services",
        token_path=None,
        verify_ssl=True,
        timeout=30,
        debug=False,
        auth_type=AuthType.BASIC,
    )
    token_manager = TokenManager(config)
    assert token_manager.get_auth_header() == {"Authorization": "Basic dGVzdDp0ZXN0"}


def test_basic_auth_request():
    """Test that Basic Authentication is used in requests."""
    config = DNSServicesConfig(
        username="test",
        password=SecretStr("test"),
        base_url="https://dns.services",
        token_path=None,
        verify_ssl=True,
        timeout=30,
        debug=False,
        auth_type=AuthType.BASIC,
    )
    token_manager = TokenManager(config)
    with mock.patch("requests.Session.request") as mock_request:
        mock_request.return_value = mock.Mock(status_code=200)
        token_manager.get("https://test.com")  # Use TokenManager's get method
        mock_request.assert_called_once()
        print(f"Mock call args: {mock_request.call_args}")
        assert "headers" in mock_request.call_args[1], "No headers in request"
        assert (
            "Authorization" in mock_request.call_args[1]["headers"]
        ), "No Authorization in headers"
        assert (
            mock_request.call_args[1]["headers"]["Authorization"]
            == "Basic dGVzdDp0ZXN0"
        )


def test_auth_type_switching():
    """Test switching between JWT and Basic auth."""
    config = DNSServicesConfig(
        username="test",
        password=SecretStr("test"),
        base_url="https://dns.services",
        token_path=None,
        verify_ssl=True,
        timeout=30,
        debug=False,
        auth_type=AuthType.JWT,
    )
    token_manager = TokenManager(config)
    assert token_manager.config.auth_type == AuthType.JWT

    config = DNSServicesConfig(
        username="test",
        password=SecretStr("test"),
        base_url="https://dns.services",
        token_path=None,
        verify_ssl=True,
        timeout=30,
        debug=False,
        auth_type=AuthType.BASIC,
    )
    token_manager = TokenManager(config)
    assert token_manager.config.auth_type == AuthType.BASIC
