"""Tests for domain operations."""

import pytest
from unittest.mock import AsyncMock

from dns_services_gateway import DomainOperations
from dns_services_gateway.models import OperationResponse
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
    mock_response = {
        "domains": [
            {
                "id": "domain1",
                "name": "example.com",
                "status": "active",
                "expires": "2024-12-31T23:59:59Z",
                "auto_renew": True,
                "nameservers": ["ns1.example.com", "ns2.example.com"],
            }
        ],
        "total": 1,
    }
    mock_client.get.return_value = mock_response

    response = await domain_ops.list_domains(page=1, per_page=20)
    assert response is not None  # Ensure method call

    assert isinstance(response, OperationResponse)
    assert response.status == "success"
    assert response.operation == "read"
    assert len(response.data["domains"]) == 1
    assert response.metadata["total"] == 1
    mock_client.get.assert_called_once_with(
        "/domains", params={"page": 1, "per_page": 20}
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

    # Test with domain name
    response = await domain_ops.get_domain_details("example.com")
    assert response is not None
    assert isinstance(response, OperationResponse)
    assert response.status == "success"
    assert response.operation == "read"
    assert response.data["domain"]["name"] == "example.com"
    assert "domain_identifier" in response.metadata
    assert "retrieved_at" in response.metadata
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
    assert response is not None  # Ensure method call

    assert isinstance(response, OperationResponse)
    assert response.status == "success"
    assert response.operation == "verify"
    assert response.data["verification_result"]["verified"] is True
    mock_client.post.assert_called_once_with("/domains/example.com/verify")


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
    assert response is not None  # Ensure method call

    assert isinstance(response, OperationResponse)
    assert response.status == "success"
    assert response.operation == "read"
    assert "metadata" in response.data
    mock_client.get.assert_called_once_with("/domains/example.com/metadata")


async def test_api_error_handling(domain_ops, mock_client):
    """Test API error handling."""
    mock_client.get.side_effect = Exception("API Error")

    with pytest.raises(APIError):
        await domain_ops.list_domains()


async def test_list_domains_edge_case(domain_ops, mock_client):
    """Test listing domains with edge case."""
    mock_response = {"domains": [], "total": 0}
    mock_client.get.return_value = mock_response

    response = await domain_ops.list_domains(page=1, per_page=0)
    assert response is not None
    assert isinstance(response, OperationResponse)
    assert response.status == "success"
    assert response.operation == "read"
    assert len(response.data["domains"]) == 0
    assert response.metadata["total"] == 0
    mock_client.get.assert_called_once_with(
        "/domains", params={"page": 1, "per_page": 0}
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
