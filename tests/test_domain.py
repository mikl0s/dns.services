"""Tests for domain operations."""

import pytest
from unittest.mock import AsyncMock
from typing import Dict, Any

from dns_services_gateway import DomainOperations
from dns_services_gateway.models import (
    BulkDomainListResponse,
    OperationResponse,
    DomainAvailabilityResponse,
    TLDListResponse,
)
from dns_services_gateway.exceptions import APIError

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_client():
    """Create a mock client."""
    client = AsyncMock()
    return client


@pytest.fixture
def domain_ops(mock_client):
    """Create a DomainOperations instance with mock client."""
    return DomainOperations(mock_client)


async def test_list_domains(domain_ops, mock_client):
    """Test listing domains."""
    mock_response: Dict[str, Any] = {
        "domains": [
            {
                "id": "domain1",
                "name": "example.com",
                "status": "active",
                "expires_at": "2024-12-31T23:59:59Z",
                "auto_renew": True,
                "nameservers": ["ns1.example.com", "ns2.example.com"],
            }
        ],
        "total": 1,
        "has_more": False,
        "query_time": 0.15,
    }
    mock_client.get.return_value = mock_response

    response = await domain_ops.list_domains(page=1, per_page=20)
    assert response is not None  # Ensure method call

    assert isinstance(response, BulkDomainListResponse)
    assert len(response.domains) == 1
    assert response.total == 1
    assert not response.has_more
    domain = response.domains[0]
    assert domain.id == "domain1"
    assert domain.name == "example.com"
    assert domain.status == "active"

    mock_client.get.assert_called_once_with(
        "/domains/list", params={"page": 1, "per_page": 20, "include_metadata": "1"}
    )


async def test_get_domain_details(domain_ops, mock_client):
    """Test getting domain details."""
    mock_response = {
        "id": "domain1",
        "name": "example.com",
        "status": "active",
        "expires": "2024-12-31T23:59:59Z",
        "auto_renew": True,
        "nameservers": ["ns1.example.com", "ns2.example.com"],
    }
    mock_client.get.return_value = mock_response

    response = await domain_ops.get_domain_details("example.com")
    assert response is not None
    assert isinstance(response, OperationResponse)
    assert response.status == "success"
    assert response.operation == "read"
    domain_data = response.data["domain"]
    assert domain_data["id"] == "domain1"
    assert domain_data["name"] == "example.com"
    assert domain_data["status"] == "active"

    mock_client.get.assert_called_with("/domain/example.com")

    # Test with domain ID
    mock_client.get.reset_mock()
    response = await domain_ops.get_domain_details("domain1")
    assert response.data["domain"]["id"] == "domain1"
    mock_client.get.assert_called_with("/domain/domain1")


async def test_verify_domain(domain_ops, mock_client):
    """Test domain verification."""
    mock_response = {
        "verified": True,
        "checks": {"nameservers": "pass", "dns_propagation": "pass"},
    }
    mock_client.post.return_value = mock_response

    response = await domain_ops.verify_domain("example.com")
    assert response is not None
    assert isinstance(response, OperationResponse)
    assert response.status == "success"
    assert response.operation == "verify"
    assert response.data["verification_result"]["verified"] is True
    assert response.metadata["domain_name"] == "example.com"

    mock_client.post.assert_called_with("/domains/example.com/verify")


async def test_get_domain_metadata(domain_ops, mock_client):
    """Test getting domain metadata."""
    mock_response = {
        "registration_date": "2023-01-01T00:00:00Z",
        "expiration_date": "2024-12-31T23:59:59Z",
        "registrar": "Example Registrar",
        "status": ["clientTransferProhibited"],
    }
    mock_client.get.return_value = mock_response

    response = await domain_ops.get_domain_metadata("example.com")
    assert response is not None
    assert isinstance(response, OperationResponse)
    assert response.status == "success"
    assert response.operation == "read"
    assert response.data["metadata"]["registration_date"] == "2023-01-01T00:00:00Z"
    assert response.metadata["domain_name"] == "example.com"

    mock_client.get.assert_called_with("/domains/example.com/metadata")


async def test_api_error_handling(domain_ops, mock_client):
    """Test API error handling."""
    mock_client.get.side_effect = Exception("API Error")

    with pytest.raises(APIError):
        await domain_ops.list_domains()


async def test_list_domains_edge_case(domain_ops, mock_client):
    """Test listing domains with edge case."""
    mock_response: Dict[str, Any] = {
        "domains": [],
        "total": 0,
        "has_more": False,
        "query_time": 0.05,
    }
    mock_client.get.return_value = mock_response

    response = await domain_ops.list_domains(page=1, per_page=0)
    assert response is not None
    assert isinstance(response, BulkDomainListResponse)
    assert len(response.domains) == 0
    assert response.total == 0
    assert not response.has_more

    mock_client.get.assert_called_once_with(
        "/domains/list", params={"page": 1, "per_page": 0, "include_metadata": "1"}
    )


async def test_get_domain_details_invalid(domain_ops, mock_client):
    """Test getting domain details with invalid domain name."""
    mock_client.get.side_effect = APIError("Domain not found")

    with pytest.raises(APIError):
        await domain_ops.get_domain_details("invalid.com")
    mock_client.get.assert_called_once_with("/domain/invalid.com")


async def test_verify_domain_failure(domain_ops, mock_client):
    """Test domain verification failure."""
    mock_client.post.side_effect = Exception("Verification failed")

    with pytest.raises(APIError):
        await domain_ops.verify_domain("example.com")
    mock_client.post.assert_called_once_with("/domains/example.com/verify")


async def test_get_domain_metadata_failure(domain_ops, mock_client):
    """Test getting domain metadata failure."""
    mock_client.get.side_effect = Exception("Metadata retrieval failed")

    with pytest.raises(APIError):
        await domain_ops.get_domain_metadata("example.com")
    mock_client.get.assert_called_once_with("/domains/example.com/metadata")


async def test_check_domain_availability(domain_ops, mock_client):
    """Test checking domain availability."""
    mock_response = {
        "available": True,
        "premium": False,
        "price": 10.99,
        "currency": "USD",
    }
    mock_client.get.return_value = mock_response

    response = await domain_ops.check_domain_availability("example.com")
    assert response is not None
    assert isinstance(response, DomainAvailabilityResponse)
    assert response.available is True
    assert response.premium is False
    assert response.price == 10.99
    assert response.currency == "USD"

    mock_client.get.assert_called_with(
        "/domain/check",
        params={"domain": "example.com", "check_premium": "false"},
    )


async def test_check_domain_availability_invalid_domain(domain_ops):
    """Test checking domain availability with invalid domain."""
    with pytest.raises(ValueError):
        await domain_ops.check_domain_availability("")


async def test_check_domain_availability_api_error(domain_ops, mock_client):
    """Test API error handling for domain availability check."""
    mock_client.get.side_effect = Exception("API Error")

    with pytest.raises(APIError) as exc_info:
        await domain_ops.check_domain_availability("example.com")
    assert "Failed to check domain availability" in str(exc_info.value)


async def test_check_domain_availability_unavailable(domain_ops, mock_client):
    """Test checking availability for unavailable domain."""
    mock_response = {
        "available": False,
        "premium": None,
        "price": None,
        "currency": None,
    }
    mock_client.get.return_value = mock_response

    response = await domain_ops.check_domain_availability("taken.com")
    assert response is not None
    assert isinstance(response, DomainAvailabilityResponse)
    assert response.available is False
    assert response.premium is None
    assert response.price is None
    assert response.currency is None

    mock_client.get.assert_called_with(
        "/domain/check",
        params={"domain": "taken.com", "check_premium": "false"},
    )


async def test_list_available_tlds(domain_ops, mock_client):
    """Test listing available TLDs."""
    mock_response = {
        "tlds": [
            {
                "name": "com",
                "available": True,
                "price": 10.99,
                "currency": "USD",
            },
            {
                "name": "net",
                "available": True,
                "price": 9.99,
                "currency": "USD",
            },
            {
                "name": "org",
                "available": True,
                "price": 8.99,
                "currency": "USD",
            },
        ]
    }
    mock_client.get.return_value = mock_response

    response = await domain_ops.list_available_tlds()
    assert response is not None
    assert isinstance(response, TLDListResponse)
    assert len(response.tlds) == 3
    assert response.total == 3
    assert response.tlds[0].name == "com"
    assert response.tlds[0].price == 10.99

    mock_client.get.assert_called_with("/tlds/available")


async def test_list_available_tlds_empty(domain_ops, mock_client):
    """Test listing available TLDs when none are available."""
    mock_response = {"tlds": []}
    mock_client.get.return_value = mock_response

    response = await domain_ops.list_available_tlds()
    assert response is not None
    assert isinstance(response, TLDListResponse)
    assert len(response.tlds) == 0
    assert response.total == 0

    mock_client.get.assert_called_with("/tlds/available")


async def test_list_available_tlds_api_error(domain_ops, mock_client):
    """Test API error handling for TLD listing."""
    mock_client.get.side_effect = Exception("API Error")

    with pytest.raises(APIError) as exc_info:
        await domain_ops.list_available_tlds()
    assert "Failed to list available TLDs" in str(exc_info.value)


async def test_list_domains_bulk(domain_ops, mock_client):
    """Test bulk domain listing with metadata."""
    # Mock response data
    mock_response: Dict[str, Any] = {
        "domains": [
            {
                "id": "domain1",
                "name": "example.com",
                "status": "active",
                "expires_at": "2024-12-31T23:59:59+00:00",
                "metadata": {
                    "registrar": "Example Registrar",
                    "created_at": "2020-01-01T00:00:00+00:00",
                },
            },
            {
                "id": "domain2",
                "name": "example.org",
                "status": "active",
                "expires_at": "2024-06-30T23:59:59+00:00",
                "metadata": {
                    "registrar": "Another Registrar",
                    "created_at": "2021-01-01T00:00:00+00:00",
                },
            },
        ],
        "total": 2,
        "has_more": False,
        "query_time": 0.15,
    }

    mock_client.get.return_value = mock_response

    response = await domain_ops.list_domains(
        page=1, per_page=10, include_metadata=True, filters={"status": "active"}
    )

    assert isinstance(response, BulkDomainListResponse)
    assert len(response.domains) == 2
    assert response.total == 2
    assert response.page == 1
    assert response.per_page == 10
    assert not response.has_more

    # Check first domain
    domain1 = response.domains[0]
    assert domain1.id == "domain1"
    assert domain1.name == "example.com"
    assert domain1.status == "active"
    if domain1.expires:
        assert domain1.expires.isoformat() == "2024-12-31T23:59:59+00:00"

    # Verify metadata was properly merged
    assert hasattr(domain1, "registrar")
    assert domain1.registrar == "Example Registrar"

    # Verify API call
    mock_client.get.assert_called_once_with(
        "/domains/list",
        params={"page": 1, "per_page": 10, "include_metadata": "1", "status": "active"},
    )


async def test_list_domains_bulk_without_metadata(domain_ops, mock_client):
    """Test bulk domain listing without metadata."""
    # Mock response data
    mock_response: Dict[str, Any] = {
        "domains": [
            {
                "id": "domain1",
                "name": "example.com",
                "status": "active",
                "expires_at": "2024-12-31T23:59:59+00:00",
            }
        ],
        "total": 1,
        "has_more": False,
        "query_time": 0.05,
    }

    mock_client.get.return_value = mock_response

    response = await domain_ops.list_domains(include_metadata=False)

    assert isinstance(response, BulkDomainListResponse)
    assert len(response.domains) == 1
    assert response.total == 1
    assert not response.has_more

    # Check domain
    domain = response.domains[0]
    assert domain.id == "domain1"
    assert domain.name == "example.com"
    assert domain.status == "active"
    if domain.expires:
        assert domain.expires.isoformat() == "2024-12-31T23:59:59+00:00"

    # Verify API call
    mock_client.get.assert_called_once_with(
        "/domains/list",
        params={"page": 1, "per_page": 20, "include_metadata": "0"},
    )
