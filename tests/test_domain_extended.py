import pytest
from unittest.mock import AsyncMock, MagicMock
from dns_services_gateway.domain import DomainOperations
from dns_services_gateway.models import (
    DomainInfo,
    OperationResponse,
    DomainAvailabilityResponse,
)


@pytest.fixture
def domain_manager():
    _client = AsyncMock()
    return DomainOperations(_client)


@pytest.mark.asyncio
async def test_register_domain(domain_manager):
    domain = "example.com"
    domain_manager._client.post.return_value = {"domain": {"name": domain}}
    response = await domain_manager.register_domain(domain)
    assert response.status == "success"
    assert response.operation == "register_domain"
    assert response.data["domain"]["name"] == domain


@pytest.mark.asyncio
async def test_register_domain_with_nameservers(domain_manager):
    domain = "example.com"
    nameservers = ["ns1.example.com", "ns2.example.com"]
    domain_manager._client.post.return_value = {"domain": {"name": domain}}
    response = await domain_manager.register_domain(domain, nameservers=nameservers)
    assert response.status == "success"
    assert response.operation == "register_domain"
    assert response.data["domain"]["name"] == domain
    assert response.metadata["nameservers"] == nameservers


@pytest.mark.asyncio
async def test_get_domain_details(domain_manager):
    domain = "example.com"
    mock_response = {
        "id": "123",
        "name": domain,
        "status": "active",
        "expiry_date": "2024-12-31",
        "created_date": "2023-12-31",
        "registrant": "John Doe",
    }
    domain_manager._client.get.return_value = mock_response
    response = await domain_manager.get_domain_details(domain)
    assert response.status == "success"
    assert response.operation == "read"
    assert response.data["domain"]["name"] == domain


@pytest.mark.asyncio
async def test_get_registry_lock_status(domain_manager):
    domain = "example.com"
    domain_manager._client.get.return_value = {"enabled": True}
    response = await domain_manager.get_registry_lock_status(domain)
    assert response.status == "success"
    assert response.operation == "get_registry_lock_status"
    assert response.data["enabled"] is True


@pytest.mark.asyncio
async def test_update_domain_forwarding(domain_manager):
    domain = "example.com"
    target_url = "https://target.com"
    domain_manager._client.put.return_value = {"success": True}
    response = await domain_manager.update_domain_forwarding(domain, target_url)
    assert response.status == "success"
    assert response.operation == "update_domain_forwarding"
    assert response.metadata["target_url"] == target_url


@pytest.mark.asyncio
async def test_check_domain_availability(domain_manager):
    domain = "example.com"
    mock_data = {
        "available": True,
        "price": "10.00",
        "currency": "USD",
        "premium": False,
    }
    domain_manager._client.get.return_value = mock_data
    response = await domain_manager.check_domain_availability(domain)
    assert isinstance(response, DomainAvailabilityResponse)
    assert response.available is True
    assert response.price == 10.00
    assert response.currency == "USD"
    assert response.premium is False
