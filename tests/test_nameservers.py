"""Test nameserver management functionality."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock

from dns_services_gateway.nameservers import NameserverManager
from dns_services_gateway.models import NameserverResponse, OperationResponse
from dns_services_gateway.exceptions import ValidationError, DNSServicesError


@pytest.fixture
def client():
    """Create a mock client."""
    return AsyncMock()


@pytest.fixture
def manager(client):
    """Create a nameserver manager instance."""
    return NameserverManager(client)


@pytest.mark.asyncio
async def test_get_nameservers_success(manager, client):
    """Test successful nameserver retrieval."""
    domain = "example.com"
    expected_nameservers = ["ns1.example.com.", "ns2.example.com."]
    client.get.return_value = {"nameservers": expected_nameservers}

    response = await manager.get_nameservers(domain)

    assert isinstance(response, NameserverResponse)
    assert response.domain == domain
    assert response.nameservers == expected_nameservers
    assert response.status == "success"
    assert isinstance(response.updated, datetime)
    client.get.assert_called_once_with(f"domain/{domain}/nameservers")


@pytest.mark.asyncio
async def test_get_nameservers_empty_domain(manager):
    """Test nameserver retrieval with empty domain."""
    with pytest.raises(ValidationError) as exc_info:
        await manager.get_nameservers("")
    assert "Domain name or ID is required" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_nameservers_api_error(manager, client):
    """Test nameserver retrieval with API error."""
    client.get.side_effect = Exception("API Error")

    with pytest.raises(DNSServicesError):
        await manager.get_nameservers("example.com")


@pytest.mark.asyncio
async def test_update_nameservers_success(manager, client):
    """Test successful nameserver update."""
    domain = "example.com"
    nameservers = ["ns1.example.com.", "ns2.example.com."]
    client.put.return_value = {
        "previous_nameservers": ["old.ns1.com.", "old.ns2.com."],
        "verified": True,
    }

    response = await manager.update_nameservers(domain, nameservers)

    assert isinstance(response, OperationResponse)
    assert response.status == "success"
    assert response.operation == "update"
    assert response.data["before"] == ["old.ns1.com.", "old.ns2.com."]
    assert response.data["after"] == nameservers
    assert response.data["verified"] is True
    assert response.metadata["domain"] == domain
    assert response.metadata["nameservers"] == nameservers
    client.put.assert_called_once_with(
        f"domain/{domain}/nameservers", json={"nameservers": nameservers}
    )


@pytest.mark.asyncio
async def test_update_nameservers_validation(manager):
    """Test nameserver update with invalid nameservers."""
    # Test empty nameservers list
    with pytest.raises(ValidationError) as exc_info:
        await manager.update_nameservers("example.com", [])
    assert "At least one nameserver must be provided" in str(exc_info.value)

    # Test empty nameserver string
    with pytest.raises(ValidationError) as exc_info:
        await manager.update_nameservers("example.com", [""])
    assert "Invalid nameserver format" in str(exc_info.value)

    # Test missing domain
    with pytest.raises(ValidationError) as exc_info:
        await manager.update_nameservers("", ["ns1.example.com"])
    assert "Domain name or ID is required" in str(exc_info.value)


@pytest.mark.asyncio
async def test_update_nameservers_api_error(manager, client):
    """Test nameserver update with API error."""
    client.put.side_effect = Exception("API Error")

    with pytest.raises(DNSServicesError):
        await manager.update_nameservers("example.com", ["ns1.example.com."])


@pytest.mark.asyncio
async def test_verify_nameservers_success(manager, client):
    """Test successful nameserver verification."""
    domain = "example.com"
    nameservers = ["ns1.example.com.", "ns2.example.com."]
    client.get.return_value = {"nameservers": nameservers}
    client.post.return_value = {"verified": True}

    result = await manager.verify_nameservers(domain, nameservers)

    assert result is True
    client.post.assert_called_once_with(
        f"domain/{domain}/nameservers/verify", json={"nameservers": nameservers}
    )


@pytest.mark.asyncio
async def test_verify_nameservers_current(manager, client):
    """Test verification of current nameservers."""
    domain = "example.com"
    current_nameservers = ["ns1.example.com.", "ns2.example.com."]
    client.get.return_value = {"nameservers": current_nameservers}
    client.post.return_value = {"verified": True}

    result = await manager.verify_nameservers(domain)

    assert result is True
    client.post.assert_called_once_with(
        f"domain/{domain}/nameservers/verify",
        json={"nameservers": current_nameservers},
    )


@pytest.mark.asyncio
async def test_verify_nameservers_api_error(manager, client):
    """Test nameserver verification with API error."""
    client.post.side_effect = Exception("API Error")

    with pytest.raises(DNSServicesError):
        await manager.verify_nameservers("example.com", ["ns1.example.com."])
