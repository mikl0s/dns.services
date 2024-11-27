"""Test configuration management."""

import os
import pytest
from pathlib import Path
from dns_services_gateway.config import DNSServicesConfig
from dns_services_gateway.exceptions import ConfigurationError


def test_config_from_env(monkeypatch):
    """Test configuration from environment variables."""
    monkeypatch.setenv("DNS_SERVICES_USERNAME", "testuser")
    monkeypatch.setenv("DNS_SERVICES_PASSWORD", "testpass")
    monkeypatch.setenv("DNS_SERVICES_BASE_URL", "https://test.dns.services")
    monkeypatch.setenv("DNS_SERVICES_TOKEN_PATH", "~/.dns-services/token")
    monkeypatch.setenv("DNS_SERVICES_VERIFY_SSL", "false")
    monkeypatch.setenv("DNS_SERVICES_TIMEOUT", "60")
    monkeypatch.setenv("DNS_SERVICES_DEBUG", "true")

    config = DNSServicesConfig.from_env()
    assert config.username == "testuser"
    assert config.password.get_secret_value() == "testpass"
    assert config.base_url == "https://test.dns.services"
    assert config.token_path == Path("~/.dns-services/token")
    assert config.verify_ssl is False
    assert config.timeout == 60
    assert config.debug is True


def test_config_missing_required(monkeypatch):
    """Test configuration with missing required variables."""
    monkeypatch.delenv("DNS_SERVICES_USERNAME", raising=False)
    monkeypatch.delenv("DNS_SERVICES_PASSWORD", raising=False)

    with pytest.raises(ConfigurationError):
        DNSServicesConfig.from_env()


def test_config_invalid_timeout(monkeypatch):
    """Test configuration with invalid timeout."""
    monkeypatch.setenv("DNS_SERVICES_USERNAME", "testuser")
    monkeypatch.setenv("DNS_SERVICES_PASSWORD", "testpass")
    monkeypatch.setenv("DNS_SERVICES_TIMEOUT", "invalid")

    with pytest.raises(ConfigurationError):
        DNSServicesConfig.from_env()


def test_config_defaults(monkeypatch):
    """Test configuration defaults."""
    monkeypatch.setenv("DNS_SERVICES_USERNAME", "testuser")
    monkeypatch.setenv("DNS_SERVICES_PASSWORD", "testpass")

    config = DNSServicesConfig.from_env()
    assert config.base_url == "https://dns.services"
    assert config.token_path is None
    assert config.verify_ssl is True
    assert config.timeout == 30
    assert config.debug is False


def test_token_path_expansion(monkeypatch, tmp_path):
    """Test token path expansion."""
    monkeypatch.setenv("DNS_SERVICES_USERNAME", "testuser")
    monkeypatch.setenv("DNS_SERVICES_PASSWORD", "testpass")
    monkeypatch.setenv("DNS_SERVICES_TOKEN_PATH", str(tmp_path / "token"))

    config = DNSServicesConfig.from_env()
    path = config.get_token_path()
    assert path is not None
    assert path.is_absolute()
    assert path.parent.exists()
