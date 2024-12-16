"""Tests for DNS forwarding functionality."""

import pytest
from unittest.mock import Mock, AsyncMock

from dns_services_gateway.forwarding import (
    ForwardingTarget,
    ForwardingRule,
    ForwardingManager,
    ForwardingResponse,
)
from dns_services_gateway.exceptions import APIError
from dns_services_gateway.client import DNSServicesClient


@pytest.fixture
def mock_client():
    """Return a mock DNS Services client."""
    client = Mock(spec=DNSServicesClient)
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.put = AsyncMock()
    client.delete = AsyncMock()
    return client


@pytest.fixture
def forwarding_manager(mock_client):
    """Return a forwarding manager with mock client."""
    return ForwardingManager(mock_client)


@pytest.fixture
def sample_target():
    """Return a sample forwarding target for testing."""
    return ForwardingTarget(
        address="8.8.8.8",
        port=53,
        protocol="udp",
        tls=False,
    )


@pytest.fixture
def sample_rule(sample_target):
    """Return a sample forwarding rule for testing."""
    return ForwardingRule(
        domain="example.com",
        targets=[sample_target],
        enabled=True,
        priority=10,
        description="Test forwarding rule",
    )


@pytest.fixture
def sample_forwarding_response(sample_rule):
    """Return a sample forwarding response for testing."""
    return {
        "rules": [
            {
                "domain": sample_rule.domain,
                "targets": [t.model_dump() for t in sample_rule.targets],
                "enabled": sample_rule.enabled,
                "priority": sample_rule.priority,
                "description": sample_rule.description,
            }
        ]
    }


@pytest.mark.asyncio
async def test_list_rules(forwarding_manager, mock_client, sample_forwarding_response):
    """Test listing forwarding rules."""
    mock_client.get.return_value = sample_forwarding_response

    response = await forwarding_manager.list_rules()

    assert response.success is True
    assert len(response.rules) == 1
    assert response.rules[0].domain == "example.com"
    mock_client.get.assert_awaited_once_with("/forwarding/rules")


@pytest.mark.asyncio
async def test_add_rule(forwarding_manager, mock_client, sample_rule):
    """Test adding a forwarding rule."""
    mock_client.post.return_value = {"rule": sample_rule.model_dump()}

    response = await forwarding_manager.add_rule(sample_rule)

    assert response == sample_rule
    mock_client.post.assert_awaited_once_with(
        "/forwarding/rules", data=sample_rule.model_dump()
    )


@pytest.mark.asyncio
async def test_update_rule(forwarding_manager, mock_client, sample_rule):
    """Test updating a forwarding rule."""
    mock_client.put.return_value = {"rule": sample_rule.model_dump()}

    response = await forwarding_manager.update_rule(sample_rule.domain, sample_rule)

    assert response == sample_rule
    mock_client.put.assert_awaited_once_with(
        f"/forwarding/rules/{sample_rule.domain}", data=sample_rule.model_dump()
    )


@pytest.mark.asyncio
async def test_delete_rule(forwarding_manager, mock_client):
    """Test deleting a forwarding rule."""
    domain = "example.com"
    mock_client.delete.return_value = {}

    response = await forwarding_manager.delete_rule(domain)

    assert response.success is True
    mock_client.delete.assert_awaited_once_with("/forwarding/rules/example.com")


@pytest.mark.asyncio
async def test_validate_rule(forwarding_manager, mock_client, sample_rule):
    """Test validating a forwarding rule."""
    mock_client.post.return_value = {}

    response = await forwarding_manager.validate_rule(sample_rule)

    assert response.success is True
    mock_client.post.assert_awaited_once_with(
        "/forwarding/validate", data=sample_rule.model_dump()
    )


@pytest.mark.asyncio
async def test_list_rules_error(forwarding_manager, mock_client):
    """Test error handling when listing rules fails."""
    mock_client.get.side_effect = APIError("Failed to list rules")

    with pytest.raises(APIError) as exc_info:
        await forwarding_manager.list_rules()
    assert str(exc_info.value) == "Failed to list rules"


@pytest.mark.asyncio
async def test_add_rule_error(forwarding_manager, mock_client, sample_rule):
    """Test error handling when adding a rule fails."""
    mock_client.post.side_effect = APIError("Failed to add rule")

    with pytest.raises(APIError) as exc_info:
        await forwarding_manager.add_rule(sample_rule)
    assert str(exc_info.value) == "Failed to add rule"


@pytest.mark.asyncio
async def test_update_rule_error(forwarding_manager, mock_client, sample_rule):
    """Test error handling when updating a rule fails."""
    mock_client.put.side_effect = APIError("Failed to update rule")

    with pytest.raises(APIError) as exc_info:
        await forwarding_manager.update_rule(sample_rule.domain, sample_rule)
    assert str(exc_info.value) == "Failed to update rule"


@pytest.mark.asyncio
async def test_delete_rule_error(forwarding_manager, mock_client):
    """Test error handling when deleting a rule fails."""
    domain = "example.com"
    mock_client.delete.side_effect = APIError("Failed to delete rule")

    with pytest.raises(APIError) as exc_info:
        await forwarding_manager.delete_rule(domain)
    assert str(exc_info.value) == "Failed to delete rule"


@pytest.mark.asyncio
async def test_validate_rule_error(forwarding_manager, mock_client, sample_rule):
    """Test error handling when validating a rule fails."""
    mock_client.post.side_effect = APIError("Failed to validate rule")

    with pytest.raises(APIError) as exc_info:
        await forwarding_manager.validate_rule(sample_rule)
    assert str(exc_info.value) == "Failed to validate rule"


def test_forwarding_target_validation():
    """Test ForwardingTarget validation."""
    # Test valid target
    target = ForwardingTarget(
        address="8.8.8.8",
        port=53,
        protocol="udp",
        tls=False,
    )
    assert target.address == "8.8.8.8"

    # Test invalid IP address
    with pytest.raises(ValueError, match="Invalid IP address format"):
        ForwardingTarget(
            address="invalid",
            port=53,
            protocol="udp",
        )

    # Test invalid port
    with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
        ForwardingTarget(
            address="8.8.8.8",
            port=0,
            protocol="udp",
        )

    # Test invalid protocol
    with pytest.raises(ValueError, match="Protocol must be either 'udp' or 'tcp'"):
        ForwardingTarget(
            address="8.8.8.8",
            port=53,
            protocol="invalid",
        )


def test_forwarding_rule_validation():
    """Test ForwardingRule validation."""
    target = ForwardingTarget(
        address="8.8.8.8",
        port=53,
        protocol="udp",
    )

    # Test valid rule
    rule = ForwardingRule(
        domain="example.com",
        targets=[target],
        enabled=True,
        priority=10,
    )
    assert rule.domain == "example.com"

    # Test invalid domain
    with pytest.raises(ValueError, match="Domain pattern cannot start with a dot"):
        ForwardingRule(
            domain=".example.com",
            targets=[target],
        )

    # Test empty domain
    with pytest.raises(ValueError, match="Domain pattern must be a non-empty string"):
        ForwardingRule(
            domain="",
            targets=[target],
        )
