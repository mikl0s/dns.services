"""Tests for the configuration module."""

import os
import pytest
from pydantic import SecretStr
from dns_services_gateway.config import DNSServicesConfig, AuthType
from dns_services_gateway.exceptions import ConfigurationError
from pathlib import Path
from unittest import mock


@pytest.fixture
def env_vars():
    """Fixture to set and clean up environment variables."""
    original_env = dict(os.environ)
    os.environ.update(
        {
            "DNS_SERVICES_USERNAME": "test_user",
            "DNS_SERVICES_PASSWORD": "test_pass",
            "DNS_SERVICES_BASE_URL": "https://test.dns.services",
            "DNS_SERVICES_TOKEN_PATH": "~/test/token",
            "DNS_SERVICES_VERIFY_SSL": "false",
            "DNS_SERVICES_TIMEOUT": "60",
            "DNS_SERVICES_DEBUG": "true",
        }
    )
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Clear DNS_SERVICES environment variables before each test."""
    for key in list(os.environ.keys()):
        if key.startswith("DNS_SERVICES_"):
            monkeypatch.delenv(key)


def test_config_defaults():
    """Test default configuration values."""
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
    assert config.username == "test"
    assert config.password.get_secret_value() == "test"
    assert config.base_url == "https://dns.services"
    assert config.token_path is None
    assert config.verify_ssl is True
    assert config.timeout == 30
    assert config.debug is False


def test_config_custom_values():
    """Test configuration with custom values."""
    config = DNSServicesConfig(
        username="custom_user",
        password=SecretStr("custom_pass"),
        base_url="https://custom.dns.services",
        token_path=Path("~/custom/token"),
        verify_ssl=False,
        timeout=60,
        debug=True,
        auth_type=AuthType.BASIC,
    )
    assert config.username == "custom_user"
    assert config.password.get_secret_value() == "custom_pass"
    assert config.base_url == "https://custom.dns.services"
    assert config.token_path == Path("~/custom/token")
    assert config.verify_ssl is False
    assert config.timeout == 60
    assert config.debug is True
    assert config.auth_type == AuthType.BASIC


def test_config_from_env(env_vars):
    """Test configuration loading from environment variables."""
    config = DNSServicesConfig.from_env()
    assert config.username == "test_user"
    assert config.password.get_secret_value() == "test_pass"
    assert config.base_url == "https://test.dns.services"
    assert config.token_path == Path("~/test/token")
    assert config.verify_ssl is False
    assert config.timeout == 60
    assert config.debug is True
    assert config.auth_type == AuthType.JWT


def test_config_from_env_file(tmp_path):
    """Test configuration loading from .env file."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        """
DNS_SERVICES_USERNAME=env_user
DNS_SERVICES_PASSWORD=env_pass
DNS_SERVICES_BASE_URL=https://env.dns.services
DNS_SERVICES_TOKEN_PATH=~/env/token
DNS_SERVICES_VERIFY_SSL=false
DNS_SERVICES_TIMEOUT=45
DNS_SERVICES_DEBUG=true
DNS_SERVICES_AUTH_TYPE=BASIC
""".strip()
    )

    config = DNSServicesConfig.from_env(str(env_file))
    assert config.username == "env_user"
    assert config.password.get_secret_value() == "env_pass"
    assert config.base_url == "https://env.dns.services"
    assert config.token_path == Path("~/env/token")
    assert config.verify_ssl is False
    assert config.timeout == 45
    assert config.debug is True
    assert config.auth_type == AuthType.BASIC


def test_config_from_env_missing_required():
    """Test error when required environment variables are missing."""
    with mock.patch.dict(os.environ, {}, clear=True):
        with pytest.raises(
            ConfigurationError, match="Missing required environment variables"
        ):
            DNSServicesConfig.from_env()


def test_config_from_env_invalid_timeout(env_vars):
    """Test error when timeout value is invalid."""
    os.environ["DNS_SERVICES_TIMEOUT"] = "invalid"
    with pytest.raises(ConfigurationError, match="Invalid configuration"):
        DNSServicesConfig.from_env()


def test_config_from_env_file_not_found():
    """Test error when env file doesn't exist."""
    with pytest.raises(ConfigurationError, match="Environment file not found"):
        DNSServicesConfig.from_env("/nonexistent/.env")


def test_get_token_path():
    """Test token path resolution."""
    # Test with no token path
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
    assert config.get_token_path() is None

    # Test with token path
    config = DNSServicesConfig(
        username="test",
        password=SecretStr("test"),
        base_url="https://dns.services",
        token_path=Path("~/test/token"),
        verify_ssl=True,
        timeout=30,
        debug=False,
        auth_type=AuthType.JWT,
    )
    token_path = config.get_token_path()
    assert token_path is not None
    assert token_path.is_absolute()
    assert str(token_path).startswith(str(Path.home()))


def test_get_token_path_creates_dirs(tmp_path):
    """Test that get_token_path creates parent directories."""
    token_path = tmp_path / "nested" / "dirs" / "token"
    config = DNSServicesConfig(
        username="test",
        password=SecretStr("test"),
        base_url="https://dns.services",
        token_path=token_path,
        verify_ssl=True,
        timeout=30,
        debug=False,
        auth_type=AuthType.JWT,
    )

    result = config.get_token_path()
    assert result == token_path.resolve()
    assert token_path.parent.exists()


def test_config_timeout_validation():
    """Test timeout validation."""
    # Test valid timeouts
    for timeout in [1, 30, 300]:
        config = DNSServicesConfig(
            username="test",
            password=SecretStr("test"),
            base_url="https://dns.services",
            token_path=None,
            verify_ssl=True,
            timeout=timeout,
            debug=False,
            auth_type=AuthType.JWT,
        )
        assert config.timeout == timeout

    # Test invalid timeouts
    for timeout in [0, -1, 301]:
        with pytest.raises(ValueError):
            DNSServicesConfig(
                username="test",
                password=SecretStr("test"),
                base_url="https://dns.services",
                token_path=None,
                verify_ssl=True,
                timeout=timeout,
                debug=False,
                auth_type=AuthType.JWT,
            )


@pytest.fixture
def env_file(tmp_path):
    """Create a temporary .env file."""
    env_path = tmp_path / ".env"
    env_path.write_text(
        "DNS_SERVICES_USERNAME=test_user\n"
        "DNS_SERVICES_PASSWORD=test_pass\n"
        "DNS_SERVICES_BASE_URL=https://test.dns.services\n"
        "DNS_SERVICES_TOKEN_PATH=/tmp/token\n"
        "DNS_SERVICES_VERIFY_SSL=false\n"
        "DNS_SERVICES_TIMEOUT=60\n"
        "DNS_SERVICES_DEBUG=true\n"
        "DNS_SERVICES_AUTH_TYPE=BASIC\n"
    )
    return str(env_path)


"""def test_config_from_env(env_file, monkeypatch):
    Test configuration creation from environment variables.
    # Clear any existing env vars
    for key in os.environ.keys():
        if key.startswith("DNS_SERVICES_"):
            monkeypatch.delenv(key)

    config = DNSServicesConfig.from_env(env_file)
    assert config.username == "test_user"
    assert config.password.get_secret_value() == "test_pass"
    assert config.base_url == "https://test.dns.services"
    assert config.token_path == Path("/tmp/token")
    assert not config.verify_ssl
    assert config.timeout == 60
    assert config.debug
    assert config.auth_type == AuthType.BASIC"""


def test_config_from_env_minimal(monkeypatch):
    """Test configuration with only required fields."""
    # Clear any existing env vars
    for key in os.environ.keys():
        if key.startswith("DNS_SERVICES_"):
            monkeypatch.delenv(key)

    monkeypatch.setenv("DNS_SERVICES_USERNAME", "test_user")
    monkeypatch.setenv("DNS_SERVICES_PASSWORD", "test_pass")

    config = DNSServicesConfig.from_env()
    assert config.username == "test_user"
    assert config.password.get_secret_value() == "test_pass"
    assert config.base_url == "https://dns.services"  # default
    assert config.token_path is None
    assert config.verify_ssl  # default
    assert config.timeout == 30  # default
    assert not config.debug  # default
    assert config.auth_type == AuthType.JWT  # default


def test_config_missing_required_env(monkeypatch):
    """Test error when required environment variables are missing."""
    # Clear any existing env vars
    for key in os.environ.keys():
        if key.startswith("DNS_SERVICES_"):
            monkeypatch.delenv(key)

    with pytest.raises(
        ConfigurationError, match="Missing required environment variables"
    ):
        DNSServicesConfig.from_env()


def test_config_invalid_env_file():
    """Test error when env file doesn't exist."""
    with pytest.raises(ConfigurationError, match="Environment file not found"):
        DNSServicesConfig.from_env("/nonexistent/.env")


def test_config_invalid_timeout(monkeypatch):
    """Test error with invalid timeout value."""
    # Clear any existing env vars
    for key in os.environ.keys():
        if key.startswith("DNS_SERVICES_"):
            monkeypatch.delenv(key)

    monkeypatch.setenv("DNS_SERVICES_USERNAME", "test_user")
    monkeypatch.setenv("DNS_SERVICES_PASSWORD", "test_pass")
    monkeypatch.setenv("DNS_SERVICES_TIMEOUT", "invalid")

    with pytest.raises(ConfigurationError, match="Invalid configuration"):
        DNSServicesConfig.from_env()


def test_config_invalid_auth_type(monkeypatch):
    """Test error with invalid auth type."""
    # Clear any existing env vars
    for key in os.environ.keys():
        if key.startswith("DNS_SERVICES_"):
            monkeypatch.delenv(key)

    monkeypatch.setenv("DNS_SERVICES_USERNAME", "test_user")
    monkeypatch.setenv("DNS_SERVICES_PASSWORD", "test_pass")
    monkeypatch.setenv("DNS_SERVICES_AUTH_TYPE", "INVALID")

    with pytest.raises(ConfigurationError, match="Invalid configuration"):
        DNSServicesConfig.from_env()


"""def test_get_token_path(tmp_path):
    " Test token path resolution.
    config = DNSServicesConfig(
        username="test",
        password=SecretStr("test"),
        token_path=tmp_path / "nested" / "token",
    )

    path = config.get_token_path()
    assert path is not None
    assert path.is_absolute()
    assert path.parent.exists()
    assert str(path).endswith("nested/token")"""


def test_get_token_path_none():
    """Test get_token_path when token_path is None."""
    config = DNSServicesConfig(username="test", password=SecretStr("test"))
    assert config.get_token_path() is None


"""def test_config_timeout_validation():
    " Test timeout validation.
    # Valid timeout
    config = DNSServicesConfig(username="test", password=SecretStr("test"), timeout=30)
    assert config.timeout == 30

    # Invalid timeout (too low)
    with pytest.raises(ValueError):
        DNSServicesConfig(username="test", password=SecretStr("test"), timeout=0)

    # Invalid timeout (too high)
    with pytest.raises(ValueError):
        DNSServicesConfig(username="test", password=SecretStr("test"), timeout=301)"""
