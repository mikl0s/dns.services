"""Extended tests for authentication functionality."""

from datetime import datetime
from unittest.mock import patch, MagicMock
import requests

from dns_services_gateway.auth import TokenManager, DateTimeEncoder
from dns_services_gateway.config import DNSServicesConfig
from dns_services_gateway.exceptions import AuthenticationError


def test_datetime_encoder_non_datetime():
    """Test DateTimeEncoder with non-datetime objects."""
    encoder = DateTimeEncoder()
    result = encoder.default("test")
    assert result == "test"


def test_token_path_creation():
    """Test secure token path creation."""
    config = DNSServicesConfig(
        api_url="https://api.test",
        username="test",
        password="test",
        token_path="~/test/.dns/token",
    )
    manager = TokenManager(config)

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "token": "test_token",
        "expires_at": (datetime.now()).isoformat(),
    }

    with patch("requests.Session.post", return_value=mock_response):
        with patch("pathlib.Path.mkdir") as mock_mkdir:
            with patch("pathlib.Path.write_text"):
                with patch("pathlib.Path.chmod"):
                    token_path = manager.download_token("test", password="test")
                    mock_mkdir.assert_called_with(
                        parents=True, exist_ok=True, mode=0o700
                    )
                    assert token_path is not None
                    assert "test/.dns/token" in str(token_path)


def test_token_path_permissions():
    """Test token file permissions."""
    config = DNSServicesConfig(
        api_url="https://api.test",
        username="test",
        password="test",
        token_path="/tmp/test_token",
    )
    manager = TokenManager(config)

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "token": "test_token",
        "expires_at": (datetime.now()).isoformat(),
    }

    with patch("requests.Session.post", return_value=mock_response):
        with patch("pathlib.Path.chmod") as mock_chmod:
            manager.download_token("test", password="test")
            mock_chmod.assert_called_with(0o600)


def test_token_download_request_exception():
    """Test token download with request exception."""
    config = DNSServicesConfig(
        api_url="https://api.test", username="test", password="test"
    )
    manager = TokenManager(config)

    with patch(
        "requests.Session.post", side_effect=requests.RequestException("Network error")
    ):
        with patch("pathlib.Path.chmod"):
            try:
                manager.download_token("test", password="test")
                assert False, "Expected AuthenticationError"
            except AuthenticationError as exc:
                assert "Failed to download token" in str(exc)
