"""Tests for the CLI module."""

import os
from unittest import mock
import pytest
from click.testing import CliRunner
from dns_services_gateway.cli import cli
from dns_services_gateway.auth import Token
from dns_services_gateway.exceptions import AuthenticationError, TokenError
from datetime import datetime, timezone


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_token_manager():
    """Mock TokenManager."""
    with mock.patch("dns_services_gateway.cli.TokenManager") as mock_tm:
        yield mock_tm


@pytest.fixture
def mock_config():
    """Mock DNSServicesConfig."""
    with mock.patch("dns_services_gateway.cli.DNSServicesConfig") as mock_config:
        mock_config.from_env.return_value.token_path = "~/test/token"
        yield mock_config


@pytest.fixture
def mock_env():
    """Mock environment variables."""
    with mock.patch.dict(
        os.environ,
        {
            "DNS_SERVICES_USERNAME": "test_user",
            "DNS_SERVICES_PASSWORD": "test_pass",
        },
    ):
        yield


def test_cli_help(runner):
    """Test CLI help output."""
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "DNS Services Gateway CLI." in result.output


def test_token_help(runner):
    """Test token command help output."""
    result = runner.invoke(cli, ["token", "--help"])
    assert result.exit_code == 0
    assert "Manage authentication tokens." in result.output


def test_token_download_help(runner):
    """Test token download command help output."""
    result = runner.invoke(cli, ["token", "download", "--help"])
    assert result.exit_code == 0
    assert "Download and save authentication token." in result.output


def test_token_verify_help(runner):
    """Test token verify command help output."""
    result = runner.invoke(cli, ["token", "verify", "--help"])
    assert result.exit_code == 0
    assert "Verify token file exists and is valid." in result.output


def test_token_download_success(runner, mock_token_manager, mock_config, mock_env):
    """Test successful token download."""
    mock_token_manager.return_value.download_token.return_value = "/path/to/token"

    result = runner.invoke(cli, ["token", "download", "-u", "testuser"])
    assert result.exit_code == 0
    assert "Token successfully saved to: /path/to/token" in result.output

    mock_token_manager.return_value.download_token.assert_called_once_with(
        username="testuser",
        output_path=mock_config.from_env.return_value.token_path,
        password=None,
    )


def test_token_download_custom_output(runner, mock_token_manager, mock_env):
    """Test token download with custom output path."""
    mock_token_manager.return_value.download_token.return_value = "/custom/path/token"

    result = runner.invoke(
        cli, ["token", "download", "-u", "testuser", "-o", "/custom/path/token"]
    )
    assert result.exit_code == 0
    assert "Token successfully saved to: /custom/path/token" in result.output

    mock_token_manager.return_value.download_token.assert_called_once_with(
        username="testuser",
        output_path="/custom/path/token",
        password=None,
    )


def test_token_download_auth_error(runner, mock_token_manager, mock_env):
    """Test token download with authentication error."""
    mock_token_manager.return_value.download_token.side_effect = AuthenticationError(
        "Invalid credentials"
    )

    result = runner.invoke(cli, ["token", "download", "-u", "testuser"])
    assert result.exit_code == 1
    assert "Authentication failed: Invalid credentials" in result.output


def test_token_download_token_error(runner, mock_token_manager, mock_env):
    """Test token download with token error."""
    mock_token_manager.return_value.download_token.side_effect = TokenError(
        "Failed to save token"
    )

    result = runner.invoke(cli, ["token", "download", "-u", "testuser"])
    assert result.exit_code == 1
    assert "Token error: Failed to save token" in result.output


def test_token_download_unexpected_error(runner, mock_token_manager, mock_env):
    """Test token download with unexpected error."""
    mock_token_manager.return_value.download_token.side_effect = Exception(
        "Unexpected error"
    )

    result = runner.invoke(cli, ["token", "download", "-u", "testuser"])
    assert result.exit_code == 1
    assert "Unexpected error: Unexpected error" in result.output


def test_token_verify_success(runner, mock_token_manager, mock_config, mock_env):
    """Test successful token verification."""
    mock_token = Token(
        token="test_token",
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc).replace(year=2025),
    )
    mock_token_manager.load_token.return_value = mock_token

    result = runner.invoke(cli, ["token", "verify"])
    assert result.exit_code == 0
    assert "Token verification successful!" in result.output


def test_token_verify_expired(runner, mock_token_manager, mock_config, mock_env):
    """Test verification of expired token."""
    mock_token = Token(
        token="test_token",
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc).replace(year=2020),
    )
    mock_token_manager.load_token.return_value = mock_token

    result = runner.invoke(cli, ["token", "verify"])
    assert result.exit_code == 1
    assert "Token verification successful!" in result.output
    assert "Warning: Token is expired" in result.output


def test_token_verify_custom_path(runner, mock_token_manager, mock_env):
    """Test token verification with custom path."""
    mock_token = Token(
        token="test_token",
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc).replace(year=2025),
    )
    mock_token_manager.load_token.return_value = mock_token

    result = runner.invoke(cli, ["token", "verify", "-p", "/custom/path/token"])
    assert result.exit_code == 0
    assert "Token verification successful!" in result.output

    mock_token_manager.load_token.assert_called_once_with("/custom/path/token")


def test_token_verify_error(runner, mock_token_manager, mock_config, mock_env):
    """Test token verification with error."""
    mock_token_manager.load_token.side_effect = TokenError("Token file not found")

    result = runner.invoke(cli, ["token", "verify"])
    assert result.exit_code == 1
    assert "Token verification failed: Token file not found" in result.output
