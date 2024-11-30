"""Extended tests for authentication functionality."""

from datetime import datetime, timedelta
import os
import pytest
import requests
from dateutil import tz  # type: ignore
from dns_services_gateway.auth import TokenManager, DateTimeEncoder
from dns_services_gateway.config import DNSServicesConfig, AuthType
from dns_services_gateway.exceptions import AuthenticationError, TokenError
from mock import Mock  # type: ignore


def test_datetime_encoder_non_datetime():
    """Test DateTimeEncoder with non-datetime objects."""
    encoder = DateTimeEncoder()
    result = encoder.default("test")
    assert result == "test"


@pytest.fixture
def mock_response():
    response = Mock()  # type: ignore
    token_data = {
        "token": "test_token",
        "expires_at": (datetime.now(tz=tz.tzutc()) + timedelta(hours=1)).isoformat(),
    }
    response.json = lambda: token_data
    response.raise_for_status = Mock(return_value=None)  # type: ignore
    response.status_code = 200
    return response


@pytest.fixture
def token_manager():
    config = DNSServicesConfig(
        username="test",
        password="test",
        base_url="https://api.test",
        token_path=None,
        verify_ssl=False,
        timeout=30,
        debug=False,
        auth_type=AuthType.JWT,
    )
    manager = TokenManager(config)
    manager._session = Mock(spec=requests.Session)  # type: ignore
    return manager


def test_token_path_creation(token_manager, mock_response):
    """Test token path creation with mocked requests."""
    token_manager._session.request.return_value = mock_response
    token_path = token_manager.download_token("test", password="test")
    assert token_path is None  # No path provided or configured


def test_token_path_permissions(token_manager, mock_response, tmp_path):
    """Test token path permissions with mocked requests."""
    token_manager._session.request.return_value = mock_response

    # Test with a path we don't have permissions for
    with pytest.raises(TokenError) as exc_info:
        token_manager.download_token("test", password="test", output_path="/root/token")
    assert "Failed to save token" in str(exc_info.value)

    # Test with a valid path
    token_path = tmp_path / "token"
    result = token_manager.download_token(
        "test", password="test", output_path=str(token_path)
    )
    assert result == str(token_path)
    assert token_path.exists()
    # Check file permissions
    stat_info = os.stat(token_path)
    assert stat_info.st_mode & 0o777 == 0o600


def test_token_download_request_exception(token_manager):
    """Test handling of request exceptions during token download."""
    token_manager._session.request.side_effect = requests.RequestException("Test error")
    with pytest.raises(AuthenticationError) as exc_info:
        token_manager.download_token("test", password="test")
    assert "Failed to download token" in str(exc_info.value)


def test_token_expiration(token_manager, mock_response, tmp_path):
    """Test token expiration checking."""
    # Use valid token first
    token_manager._session.request.return_value = mock_response
    token_path = tmp_path / "test_token"
    token_manager.download_token("test", password="test", output_path=str(token_path))
    token = TokenManager.load_token(token_path)
    assert not token.is_expired

    # Test with expired token
    expired_response = Mock()  # type: ignore
    expired_token_data = {
        "token": "test_token",
        "expires_at": (datetime.now(tz=tz.tzutc()) - timedelta(hours=1)).isoformat(),
    }
    expired_response.json = lambda: expired_token_data
    expired_response.raise_for_status = Mock(return_value=None)  # type: ignore
    expired_response.status_code = 200

    token_manager._session.request.return_value = expired_response
    token_manager.download_token("test", password="test", output_path=str(token_path))
    token = TokenManager.load_token(token_path)
    assert token.is_expired


def test_invalid_token_response(token_manager):
    """Test handling of invalid token responses."""
    invalid_response = Mock()  # type: ignore
    invalid_response.json = lambda: {"error": "Invalid credentials"}
    invalid_response.raise_for_status = Mock(
        side_effect=requests.exceptions.HTTPError("401 Client Error")
    )
    invalid_response.status_code = 401

    token_manager._session.request.return_value = invalid_response
    with pytest.raises(AuthenticationError) as exc_info:
        token_manager.download_token("test", password="test")
    assert "401 Client Error" in str(exc_info.value)


def test_malformed_token_response(token_manager):
    """Test handling of malformed token responses."""
    malformed_response = Mock()  # type: ignore
    malformed_response.json = lambda: {"not_a_token": "test"}
    malformed_response.raise_for_status = Mock(return_value=None)  # type: ignore
    malformed_response.status_code = 200

    token_manager._session.request.return_value = malformed_response
    with pytest.raises(AuthenticationError) as exc_info:
        token_manager.download_token("test", password="test")
    assert "No token in response" in str(exc_info.value)
