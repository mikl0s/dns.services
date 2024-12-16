"""Extended tests for DNS Services Gateway client."""

import json
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, PropertyMock

import requests
from requests.exceptions import RequestException

from dns_services_gateway.client import DNSServicesClient
from dns_services_gateway.config import DNSServicesConfig, AuthType
from dns_services_gateway.exceptions import AuthenticationError, APIError, RequestError
from dns_services_gateway.models import AuthResponse


@pytest.fixture
def mock_config():
    config = Mock(spec=DNSServicesConfig)
    config.auth_type = AuthType.JWT
    config.verify_ssl = True
    config.debug = False
    config.base_url = "https://api.example.com"
    config.username = "test_user"
    config.password = Mock()
    config.password.get_secret_value.return_value = "test_pass"
    config.token_path = None
    config.timeout = 30
    return config


@pytest.fixture
def mock_session():
    session = Mock(spec=requests.Session)
    session.verify = True
    return session


@pytest.fixture
def client(mock_config, mock_session):
    with patch("requests.Session", return_value=mock_session):
        return DNSServicesClient(mock_config)


def test_init(mock_config, mock_session):
    with patch("requests.Session", return_value=mock_session):
        client = DNSServicesClient(mock_config)
        assert client.config == mock_config
        assert client.session.verify == mock_config.verify_ssl
        assert client._token is None
        assert client._token_expires is None


def test_authenticate_token(client, mock_session):
    # Mock token path to return None to force authentication
    mock_token_path = Mock()
    mock_token_path.exists.return_value = False
    client.config.get_token_path = Mock(return_value=mock_token_path)

    # Mock successful authentication
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    mock_response = Mock(spec=requests.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "token": "new_token",
        "expiration": expires.isoformat(),
    }
    mock_session.post.return_value = mock_response

    client.authenticate()
    assert client._token == "new_token"
    assert isinstance(client._token_expires, datetime)


def test_authenticate_basic(mock_config, mock_session):
    mock_config.auth_type = AuthType.BASIC
    with patch("requests.Session", return_value=mock_session):
        client = DNSServicesClient(mock_config)

        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.text = "Basic auth successful"
        mock_session.post.return_value = mock_response

        client.authenticate()
        assert client._token is None
        assert client._token_expires is None


def test_authenticate_failed(client, mock_session):
    # Mock token path to return None to force authentication
    mock_token_path = Mock()
    mock_token_path.exists.return_value = False
    client.config.get_token_path = Mock(return_value=mock_token_path)

    # Mock failed authentication
    mock_response = Mock(spec=requests.Response)
    mock_response.status_code = 401
    mock_response.text = "Authentication failed"
    mock_session.post.return_value = mock_response

    with pytest.raises(AuthenticationError) as exc_info:
        client.authenticate()
    assert "Authentication failed" in str(exc_info.value)


def test_load_token_not_exists(client, tmp_path):
    mock_token_path = Mock()
    mock_token_path.exists.return_value = False
    client.config.get_token_path = Mock(return_value=mock_token_path)
    assert client._load_token() is None


def test_load_token_invalid_json(client, tmp_path):
    mock_token_path = Mock()
    mock_token_path.exists.return_value = True
    mock_token_path.read_text.return_value = "invalid json"
    client.config.get_token_path = Mock(return_value=mock_token_path)
    assert client._load_token() is None


def test_load_token_success(client, tmp_path):
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    token_data = {
        "token": "test_token",
        "expiration": expires.isoformat(),
    }

    mock_token_path = Mock()
    mock_token_path.exists.return_value = True
    mock_token_path.read_text.return_value = json.dumps(token_data)
    client.config.get_token_path = Mock(return_value=mock_token_path)

    auth = client._load_token()
    assert auth is not None
    assert auth.token == "test_token"
    assert isinstance(auth.expires, datetime)


def test_request_success(client, mock_session):
    # Mock token path to return None to force authentication
    mock_token_path = Mock()
    mock_token_path.exists.return_value = False
    client.config.get_token_path = Mock(return_value=mock_token_path)

    # Mock successful authentication
    auth_response = Mock(spec=requests.Response)
    auth_response.status_code = 200
    auth_response.json.return_value = {
        "token": "test_token",
        "expiration": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    }

    # Mock successful request
    request_response = Mock(spec=requests.Response)
    request_response.status_code = 200
    request_response.json.return_value = {"data": "test"}

    mock_session.post.return_value = auth_response
    mock_session.get.return_value = request_response

    response = client._request("GET", "/test")
    assert response.status_code == 200
    assert response.json() == {"data": "test"}


def test_request_error(client, mock_session):
    # Mock token path to return None to force authentication
    mock_token_path = Mock()
    mock_token_path.exists.return_value = False
    client.config.get_token_path = Mock(return_value=mock_token_path)

    # Mock successful authentication
    auth_response = Mock(spec=requests.Response)
    auth_response.status_code = 200
    auth_response.json.return_value = {
        "token": "test_token",
        "expiration": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    }
    mock_session.post.return_value = auth_response

    # Mock error response
    error_response = Mock(spec=requests.Response)
    error_response.status_code = 500
    error_response.text = "Internal server error"
    error_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "500 Server Error"
    )
    mock_session.get.return_value = error_response

    with pytest.raises(RequestError) as exc_info:
        client._request("GET", "/test")
    assert "500 Server Error" in str(exc_info.value)


def test_request_network_error(client, mock_session):
    # Mock token path to return None to force authentication
    mock_token_path = Mock()
    mock_token_path.exists.return_value = False
    client.config.get_token_path = Mock(return_value=mock_token_path)

    # Mock successful authentication
    auth_response = Mock(spec=requests.Response)
    auth_response.status_code = 200
    auth_response.json.return_value = {
        "token": "test_token",
        "expiration": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    }
    mock_session.post.return_value = auth_response

    # Mock network error
    mock_session.get.side_effect = requests.exceptions.ConnectionError("Network error")

    with pytest.raises(RequestError) as exc_info:
        client._request("GET", "/test")
    assert "Connection failed" in str(exc_info.value)


def test_request_with_retry(client, mock_session):
    # Mock token path to return None to force authentication
    mock_token_path = Mock()
    mock_token_path.exists.return_value = False
    client.config.get_token_path = Mock(return_value=mock_token_path)

    # Mock successful authentication
    auth_response = Mock(spec=requests.Response)
    auth_response.status_code = 200
    auth_response.json.return_value = {
        "token": "test_token",
        "expiration": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    }

    # First request fails with 401
    error_response = Mock(spec=requests.Response)
    error_response.status_code = 401
    error_response.text = "Token expired"
    error_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "401 Unauthorized"
    )

    # Second request succeeds
    success_response = Mock(spec=requests.Response)
    success_response.status_code = 200
    success_response.json.return_value = {"data": "test"}

    # Set up the sequence of responses
    mock_session.post.return_value = auth_response
    mock_session.get.side_effect = [error_response, success_response]

    # First request should fail with 401
    with pytest.raises(RequestError) as exc_info:
        client._request("GET", "/test")
    assert "401 Unauthorized" in str(exc_info.value)
