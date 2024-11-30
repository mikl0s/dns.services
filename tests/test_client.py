"""Tests for DNS Services Gateway client."""

from datetime import datetime, timedelta, timezone
from unittest import mock

import pytest
import json
from pydantic import SecretStr

from dns_services_gateway.client import DNSServicesClient
from dns_services_gateway.config import DNSServicesConfig, AuthType
from dns_services_gateway.exceptions import AuthenticationError
from dns_services_gateway.models import AuthResponse


@pytest.fixture
def config():
    """Create a test configuration."""
    return DNSServicesConfig(
        username="test_user",
        password=SecretStr("test_pass"),
        base_url="https://test.dns.services",
        token_path=None,
        verify_ssl=True,
        timeout=30,
        debug=False,
        auth_type=AuthType.JWT,  # Set default auth type to JWT for all tests
    )


@pytest.fixture
def client(config):
    """Create a test client."""
    return DNSServicesClient(config)


@pytest.fixture
def mock_session(client):
    """Mock session fixture."""
    session = mock.Mock()
    session.post = mock.Mock()
    session.verify = True
    client.session = session
    return session


@pytest.fixture
def auth_response():
    """Create a test authentication response."""
    expires = datetime(2024, 11, 29, 9, 28, 40, tzinfo=timezone.utc)
    expires = expires.replace(
        microsecond=0
    )  # Remove microseconds for consistent comparison
    return {
        "token": "test_token",
        "expiration": expires.isoformat(),
        "refresh_token": "test_refresh_token",
    }


def test_client_init(config):
    """Test client initialization."""
    client = DNSServicesClient(config)
    assert client.config == config
    assert client.session is not None
    assert client.session.verify == config.verify_ssl
    assert client._token is None
    assert client._token_expires is None


def test_client_init_debug_logging(config):
    """Test client initialization with debug logging."""
    with mock.patch("dns_services_gateway.client.logging") as mock_logging:
        mock_logger = mock.Mock()
        mock_logging.getLogger.return_value = mock_logger
        client = DNSServicesClient(config)
        mock_logging.basicConfig.assert_not_called()
        assert client.logger == mock_logger


def test_client_init_no_debug_logging(config):
    """Test client initialization without debug logging."""
    config.debug = False
    with mock.patch("dns_services_gateway.client.logging") as mock_logging:
        mock_logger = mock.Mock()
        mock_logging.getLogger.return_value = mock_logger
        client = DNSServicesClient(config)
        mock_logging.basicConfig.assert_not_called()
        assert client.logger == mock_logger


def test_load_token_success(client, auth_response, tmp_path):
    """Test successful token loading."""
    token_path = tmp_path / "token"
    client.config.token_path = token_path
    token_path.write_text(json.dumps(auth_response))

    auth = client._load_token()
    assert auth is not None
    assert auth.token == auth_response["token"]
    assert auth.expires == datetime.fromisoformat(auth_response["expiration"])
    assert auth.refresh_token == auth_response["refresh_token"]


def test_load_token_no_path(client):
    """Test token loading with no path configured."""
    client.config.token_path = None
    assert client._load_token() is None


def test_load_token_file_not_found(client, tmp_path):
    """Test token loading with nonexistent file."""
    client.config.token_path = tmp_path / "nonexistent"
    assert client._load_token() is None


def test_load_token_invalid_json(client, tmp_path):
    """Test token loading with invalid JSON."""
    token_path = tmp_path / "token"
    client.config.token_path = token_path
    token_path.write_text("invalid json")

    assert client._load_token() is None


def test_load_token_missing_fields(client, tmp_path):
    """Test token loading with missing required fields."""
    token_path = tmp_path / "token"
    client.config.token_path = token_path
    token_path.write_text("{}")

    assert client._load_token() is None


def test_save_token(client, auth_response, tmp_path):
    """Test token saving."""
    token_path = tmp_path / "token"
    client.config.token_path = token_path

    auth = AuthResponse(**auth_response)
    client._save_token(auth)

    assert token_path.exists()
    saved_data = json.loads(token_path.read_text())
    assert saved_data["token"] == auth_response["token"]
    assert saved_data["expiration"] == auth_response["expiration"]
    assert saved_data["refresh_token"] == auth_response["refresh_token"]


def test_save_token_no_path(client, auth_response):
    """Test token saving with no path configured."""
    client.config.token_path = None
    auth = AuthResponse(**auth_response)
    client._save_token(auth)  # Should not raise


def test_get_headers_with_valid_token(client):
    """Test header generation with valid token."""
    client._token = "test_token"
    client._token_expires = datetime.now(timezone.utc) + timedelta(hours=1)

    headers = client._get_headers()
    assert headers["Authorization"] == "Bearer test_token"
    assert headers["Content-Type"] == "application/json"
    assert headers["Accept"] == "application/json"


def test_get_headers_with_expired_token(client, mock_session, auth_response):
    """Test header generation with expired token."""
    # Set up an expired token
    client._token = "old_token"
    client._token_expires = datetime.now(timezone.utc).replace(
        microsecond=0
    ) - timedelta(hours=1)

    # Mock token loading to return None so we force authentication
    with mock.patch.object(client, "_load_token", return_value=None):
        # Set up mock response
        mock_response = mock.Mock()
        mock_response.json.return_value = auth_response
        mock_response.raise_for_status.return_value = None
        mock_response.status_code = 200
        mock_response.text = json.dumps(auth_response)  # Add text response
        mock_session.post.return_value = mock_response

        # Get headers - this should trigger a new authentication
        headers = client._get_headers()

        # Verify the new token is used
        assert headers["Authorization"] == f"Bearer {auth_response['token']}"
        mock_session.post.assert_called_once_with(
            f"{client.config.base_url}/auth",
            json={
                "username": client.config.username,
                "password": client.config.password.get_secret_value(),
            },
            timeout=client.config.timeout,
        )


def test_get_headers_with_no_token(client, mock_session, auth_response):
    """Test header generation with no token."""
    client._token = None
    client._token_expires = None

    # Mock token loading to return None so we force authentication
    with mock.patch.object(client, "_load_token", return_value=None):
        # Set up mock response
        mock_response = mock.Mock()
        mock_response.json.return_value = auth_response
        mock_response.raise_for_status.return_value = None
        mock_response.status_code = 200
        mock_response.text = json.dumps(auth_response)
        mock_session.post.return_value = mock_response

        # Get headers - this should trigger authentication
        headers = client._get_headers()

        # Verify the new token is used
        assert headers["Authorization"] == f"Bearer {auth_response['token']}"
        mock_session.post.assert_called_once_with(
            f"{client.config.base_url}/auth",
            json={
                "username": client.config.username,
                "password": client.config.password.get_secret_value(),
            },
            timeout=client.config.timeout,
        )


def test_authenticate_success(client, mock_session, auth_response):
    """Test successful authentication."""
    # Mock token loading to return None so we force authentication
    with mock.patch.object(client, "_load_token", return_value=None):
        # Set up mock response
        mock_response = mock.Mock()
        mock_response.json.return_value = auth_response
        mock_response.raise_for_status.return_value = None
        mock_response.status_code = 200
        mock_response.text = json.dumps(auth_response)
        mock_session.post.return_value = mock_response

        # Authenticate
        client.authenticate()

        # Verify token is set correctly
        assert client._token == auth_response["token"]
        expected_expires = datetime.fromisoformat(auth_response["expiration"]).replace(
            microsecond=0
        )
        assert client._token_expires == expected_expires

        # Verify API call
        mock_session.post.assert_called_once_with(
            f"{client.config.base_url}/auth",
            json={
                "username": client.config.username,
                "password": client.config.password.get_secret_value(),
            },
            timeout=client.config.timeout,
        )


def test_authenticate_with_existing_token(mock_session, client):
    """Test authentication when a valid token exists."""
    future_date = datetime.now(timezone.utc) + timedelta(days=1)
    client._token = "existing_token"
    client._token_expires = future_date
    mock_load = mock.Mock(
        return_value=AuthResponse(
            token="existing_token", expiration=future_date, refresh_token=None
        )
    )
    client._load_token = mock_load

    client.authenticate()

    mock_load.assert_called_once()
    mock_session.post.assert_not_called()
    assert client._token == "existing_token"
    assert client._token_expires == future_date


def test_authenticate_failure(client, mock_session):
    """Test authentication failure."""
    # Mock failed authentication response
    mock_response = mock.Mock()
    mock_response.status_code = 401
    mock_response.text = "Invalid credentials"
    mock_session.post.return_value = mock_response

    with pytest.raises(AuthenticationError):
        client.authenticate()


def test_request_success(mock_session, client):
    """Test successful request."""
    # Mock authentication response
    mock_auth_response = mock.Mock()
    mock_auth_response.status_code = 200
    mock_auth_response.json.return_value = {
        "token": "test_token",
        "expiration": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
    }
    mock_auth_response.text = "Auth success"

    # Mock request response
    mock_request_response = mock.Mock()
    mock_request_response.status_code = 200
    mock_request_response.json.return_value = {"data": "test"}
    mock_request_response.text = "Request success"

    mock_session.post.return_value = mock_auth_response
    mock_session.get.return_value = mock_request_response

    response = client.get("/test")

    assert response == {"data": "test"}
    expected_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": "Bearer test_token",
    }
    mock_session.get.assert_called_once_with(
        "https://test.dns.services/test", headers=expected_headers, timeout=30
    )


def test_request_with_custom_headers(mock_session, client):
    """Test request with custom headers."""
    # Mock authentication response
    mock_auth_response = mock.Mock()
    mock_auth_response.status_code = 200
    mock_auth_response.json.return_value = {
        "token": "test_token",
        "expiration": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
    }
    mock_auth_response.text = "Auth success"

    # Mock request response
    mock_request_response = mock.Mock()
    mock_request_response.status_code = 200
    mock_request_response.json.return_value = {"data": "test"}
    mock_request_response.text = "Request success"

    mock_session.post.return_value = mock_auth_response
    mock_session.get.return_value = mock_request_response

    custom_headers = {"X-Custom": "test"}
    response = client.get("/test", headers=custom_headers)

    assert response == {"data": "test"}
    expected_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": "Bearer test_token",
        "X-Custom": "test",
    }
    mock_session.get.assert_called_once_with(
        "https://test.dns.services/test", headers=expected_headers, timeout=30
    )


@pytest.mark.parametrize("method", ["get", "post", "put", "delete"])
def test_http_methods(mock_session, client, method):
    """Test all HTTP methods."""
    # Mock authentication response
    mock_auth_response = mock.Mock()
    mock_auth_response.status_code = 200
    mock_auth_response.json.return_value = {
        "token": "test_token",
        "expiration": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
    }
    mock_auth_response.text = "Auth success"

    # Mock request response
    mock_request_response = mock.Mock()
    mock_request_response.status_code = 200
    mock_request_response.json.return_value = {"data": "test"}
    mock_request_response.text = "Request success"

    # For POST method, we need to mock both auth and request responses
    if method == "post":
        mock_session.post.side_effect = [mock_auth_response, mock_request_response]
    else:
        mock_session.post.return_value = mock_auth_response
        getattr(mock_session, method).return_value = mock_request_response

    func = getattr(client, method)
    response = func("/test")

    assert response == {"data": "test"}
    expected_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": "Bearer test_token",
    }
    if method == "post":
        mock_session.post.assert_has_calls(
            [
                mock.call(
                    "https://test.dns.services/auth",
                    json={"username": "test_user", "password": "test_pass"},
                    timeout=30,
                ),
                mock.call(
                    "https://test.dns.services/test",
                    headers=expected_headers,
                    timeout=30,
                ),
            ]
        )
    else:
        getattr(mock_session, method).assert_called_once_with(
            "https://test.dns.services/test", headers=expected_headers, timeout=30
        )
