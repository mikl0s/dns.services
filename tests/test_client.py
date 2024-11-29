"""Tests for the DNS Services Gateway client."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import pytest
import requests
from pydantic import SecretStr

from dns_services_gateway.client import DNSServicesClient
from dns_services_gateway.config import DNSServicesConfig
from dns_services_gateway.exceptions import AuthenticationError, APIError
from dns_services_gateway.models import AuthResponse


@pytest.fixture
def config():
    """Create a test configuration."""
    return DNSServicesConfig(
        username="test_user",
        password=SecretStr("test_pass"),
        base_url="https://test.dns.services",
        token_path=Path("~/test/token"),
        verify_ssl=True,
        timeout=30,
        debug=True,
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
        mock_logging.basicConfig.assert_called_once_with(level=mock_logging.DEBUG)
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
    # Ensure no token is set
    client._token = None
    client._token_expires = None

    # Mock token loading to return None so we force authentication
    with mock.patch.object(client, "_load_token", return_value=None):
        # Set up mock response
        mock_response = mock.Mock()
        mock_response.json.return_value = auth_response
        mock_response.raise_for_status.return_value = None
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


def test_authenticate_with_existing_token(
    client, mock_session, auth_response, tmp_path
):
    """Test authentication with existing token."""
    # Create a token file
    token_file = tmp_path / "token.json"
    token_file.write_text(
        json.dumps(
            {
                "token": "existing_token",
                "expiration": (
                    datetime.now(timezone.utc) + timedelta(hours=1)
                ).isoformat(),
                "refresh_token": "existing_refresh_token",
            }
        )
    )

    # Set up the token path in the client config
    client.config.token_path = Path(token_file)

    # Set up mock response
    mock_response = mock.Mock()
    mock_response.json.return_value = auth_response
    mock_response.raise_for_status.return_value = None
    mock_session.post.return_value = mock_response

    # Authenticate
    client.authenticate()

    # Verify token is loaded from file and no API call is made
    assert client._token == "existing_token"
    mock_session.post.assert_not_called()

    # Force authentication
    client.authenticate(force=True)

    # Verify token is updated and API call is made
    assert client._token == auth_response["token"]
    mock_session.post.assert_called_once_with(
        f"{client.config.base_url}/auth",
        json={
            "username": client.config.username,
            "password": client.config.password.get_secret_value(),
        },
        timeout=client.config.timeout,
    )


def test_authenticate_failure(client, mock_session):
    """Test authentication failure."""
    # Mock token loading to return None so we force authentication
    with mock.patch.object(client, "_load_token", return_value=None):
        # Set up mock response with error
        mock_response = mock.Mock()
        mock_response.raise_for_status.side_effect = (
            requests.exceptions.RequestException("Connection error")
        )
        mock_session.post.return_value = mock_response

        # Attempt authentication
        with pytest.raises(AuthenticationError) as exc_info:
            client.authenticate()

        # Verify error was raised
        assert "Authentication failed" in str(exc_info.value)
        assert exc_info.value.details["error"] == "Connection error"

        # Verify token was cleared
        assert client._token is None
        assert client._token_expires is None


def test_request_success(client, mock_session):
    """Test successful API request."""
    expected_response = {"key": "value"}
    mock_response = mock.Mock()
    mock_response.json.return_value = expected_response
    mock_response.raise_for_status.return_value = None
    mock_session.request.return_value = mock_response
    client._token = "test_token"
    client._token_expires = datetime.now(timezone.utc) + timedelta(hours=1)

    response = client._request("GET", "/test")
    assert response == expected_response

    mock_session.request.assert_called_once_with(
        "GET",
        f"{client.config.base_url}/test",
        timeout=client.config.timeout,
        headers={
            "Authorization": "Bearer test_token",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )


def test_request_failure(client, mock_session):
    """Test API request failure."""
    mock_response = mock.Mock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = requests.RequestException(
        "API error", response=mock_response
    )
    mock_response.text = json.dumps({"error": "Not found"})
    mock_session.request.return_value = mock_response
    client._token = "test_token"
    client._token_expires = datetime.now(timezone.utc) + timedelta(hours=1)

    with pytest.raises(APIError) as exc_info:
        client._request("GET", "/test")

    # Handle response_body directly as a dictionary
    response_body = exc_info.value.response_body
    assert "Client error" in str(exc_info.value)
    assert exc_info.value.status_code == 404
    assert isinstance(response_body, dict)
    assert response_body["error"] == "Not found"


def test_request_with_custom_headers(client, mock_session):
    """Test API request with custom headers."""
    mock_response = mock.Mock()
    mock_response.json.return_value = {}
    mock_response.raise_for_status.return_value = None
    mock_session.request.return_value = mock_response
    client._token = "test_token"
    client._token_expires = datetime.now(timezone.utc) + timedelta(hours=1)

    client._request("GET", "/test", headers={"Custom": "Header"})

    mock_session.request.assert_called_once()
    headers = mock_session.request.call_args.kwargs["headers"]
    assert headers["Custom"] == "Header"
    assert headers["Authorization"] == "Bearer test_token"


@pytest.mark.parametrize("method", ["get", "post", "put", "delete"])
def test_http_methods(method, client, mock_session):
    """Test all HTTP method wrapper functions."""
    mock_response = mock.Mock()
    mock_response.json.return_value = {}
    mock_response.raise_for_status.return_value = None
    mock_session.request.return_value = mock_response
    client._token = "test_token"
    client._token_expires = datetime.now(timezone.utc) + timedelta(hours=1)

    func = getattr(client, method)
    func("/test", param="value")

    mock_session.request.assert_called_once_with(
        method.upper(),
        f"{client.config.base_url}/test",
        timeout=client.config.timeout,
        headers={
            "Authorization": "Bearer test_token",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        param="value",
    )