"""Extended tests for DNS Services Gateway domain operations."""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch

from dns_services_gateway.models import (
    DomainInfo,
    DNSRecord,
    OperationResponse,
    BulkDomainListResponse,
    DomainAvailabilityResponse,
)
from dns_services_gateway.domain import DomainOperations
from dns_services_gateway.exceptions import APIError, ValidationError, DomainError


@pytest.fixture
def mock_client():
    client = Mock()
    # Configure mock to handle async operations
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.put = AsyncMock()
    client.delete = AsyncMock()
    return client


@pytest.fixture
def domain_ops(mock_client):
    return DomainOperations(mock_client)


@pytest.fixture
def domain_info():
    """Create a sample DomainInfo object."""
    return DomainInfo(
        id="domain123",
        name="example.com",
        status="active",
        expires=datetime.now(timezone.utc),
        auto_renew=True,
        nameservers=["ns1.example.com", "ns2.example.com"],
        records=[
            DNSRecord(id="record1", type="A", name="www", content="192.0.2.1", ttl=3600)
        ],
    )


@pytest.mark.asyncio
async def test_create_domain(domain_ops, mock_client):
    # Configure mock response
    mock_response = {
        "id": "domain123",
        "name": "example.com",
        "status": "active",
        "nameservers": ["ns1.example.com"],
        "expires": datetime.now(timezone.utc).isoformat(),
        "auto_renew": True,
    }
    mock_client.post.return_value = mock_response

    result = await domain_ops.create_domain("example.com")
    assert isinstance(result, DomainInfo)
    assert result.name == "example.com"
    assert result.status == "active"


@pytest.mark.asyncio
async def test_create_domain_validation_error(domain_ops, mock_client):
    mock_client.post.side_effect = ValidationError("Invalid domain")

    with pytest.raises(ValidationError):
        await domain_ops.create_domain("invalid@domain")


@pytest.mark.asyncio
async def test_delete_domain(domain_ops, mock_client):
    mock_client.delete.return_value = {"status": "deleted"}

    result = await domain_ops.delete_domain("example.com")
    assert result["status"] == "deleted"


@pytest.mark.asyncio
async def test_get_domain(domain_ops, mock_client):
    mock_response = {
        "domain": "example.com",
        "status": "active",
        "nameservers": ["ns1.example.com"],
        "records": [],
    }
    mock_client.get.return_value = mock_response

    result = await domain_ops.get_domain("example.com")
    assert result["domain"] == "example.com"
    assert result["status"] == "active"


@pytest.mark.asyncio
async def test_get_domain_not_found(domain_ops, mock_client):
    mock_client.get.side_effect = DomainError("Domain not found")

    with pytest.raises(DomainError):
        await domain_ops.get_domain("nonexistent.com")


@pytest.mark.asyncio
async def test_list_domains(domain_ops, mock_client):
    mock_response = {
        "domains": [
            {
                "id": "domain1",
                "name": "example1.com",
                "status": "active",
                "expires_at": datetime.now(timezone.utc).isoformat(),
                "auto_renew": True,
            },
            {
                "id": "domain2",
                "name": "example2.com",
                "status": "pending",
                "expires_at": datetime.now(timezone.utc).isoformat(),
                "auto_renew": False,
            },
        ],
        "total": 2,
        "page": 1,
        "per_page": 20,
        "has_more": False,
    }
    mock_client.get.return_value = mock_response

    result = await domain_ops.list_domains()
    assert isinstance(result, BulkDomainListResponse)
    assert len(result.domains) == 2
    assert result.total == 2
    assert result.page == 1


@pytest.mark.asyncio
async def test_update_domain(domain_ops, mock_client):
    mock_response = {
        "domain": "example.com",
        "status": "active",
        "nameservers": ["ns1.example.com", "ns2.example.com"],
    }
    mock_client.put.return_value = mock_response

    result = await domain_ops.update_domain(
        "example.com", nameservers=["ns1.example.com", "ns2.example.com"]
    )
    assert result["domain"] == "example.com"
    assert len(result["nameservers"]) == 2


@pytest.mark.asyncio
async def test_verify_domain(domain_ops, mock_client):
    mock_response = {"verified": True, "status": "verified", "method": "dns"}
    mock_client.post.return_value = mock_response

    result = await domain_ops.verify_domain("example.com")
    assert result.status == "success"
    assert result.operation == "verify"
    assert result.data["verification_result"]["verified"] is True
    assert result.data["verification_result"]["status"] == "verified"
    assert result.data["verification_result"]["method"] == "dns"
    assert result.metadata["domain_name"] == "example.com"
    assert isinstance(result.timestamp, datetime)


@pytest.mark.asyncio
async def test_get_domain_status(domain_ops, mock_client):
    mock_response = {"status": "active"}
    mock_client.get.return_value = mock_response

    result = await domain_ops.get_domain_status("example.com")
    assert result == "active"


@pytest.mark.asyncio
async def test_check_domain_availability(domain_ops, mock_client):
    mock_response = {
        "available": True,
        "domain": "example.com",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "price": None,
        "currency": None,
        "premium": None,
    }
    mock_client.get.return_value = mock_response

    result = await domain_ops.check_domain_availability("example.com")
    assert result.available is True
    assert result.domain == "example.com"
    assert isinstance(result.timestamp, datetime)
    assert result.price is None
    assert result.currency is None
    assert result.premium is None


@pytest.mark.asyncio
async def test_get_domain_nameservers(domain_ops, mock_client):
    mock_response = {"nameservers": ["ns1.example.com", "ns2.example.com"]}
    mock_client.get.return_value = mock_response

    result = await domain_ops.get_domain_nameservers("example.com")
    assert len(result["nameservers"]) == 2
    assert "ns1.example.com" in result["nameservers"]


@pytest.mark.asyncio
async def test_update_domain_nameservers(domain_ops, mock_client):
    new_nameservers = ["ns3.example.com", "ns4.example.com"]
    mock_response = {"nameservers": new_nameservers}
    mock_client.put.return_value = mock_response

    result = await domain_ops.update_domain_nameservers("example.com", new_nameservers)
    assert result["nameservers"] == new_nameservers


@pytest.mark.asyncio
async def test_get_domain_records(domain_ops, mock_client):
    mock_response = {
        "records": [
            {"type": "A", "name": "@", "value": "1.2.3.4"},
            {"type": "MX", "name": "@", "value": "mail.example.com"},
        ]
    }
    mock_client.get.return_value = mock_response

    result = await domain_ops.get_domain_records("example.com")
    assert len(result["records"]) == 2
    assert result["records"][0]["type"] == "A"
    assert result["records"][1]["type"] == "MX"


@pytest.mark.asyncio
async def test_add_domain_record(domain_ops, mock_client):
    record = {"type": "A", "name": "www", "value": "1.2.3.4"}
    mock_response = {"record": record}
    mock_client.post.return_value = mock_response

    result = await domain_ops.add_domain_record("example.com", record)
    assert result["record"]["type"] == "A"
    assert result["record"]["value"] == "1.2.3.4"


@pytest.mark.asyncio
async def test_delete_domain_record(domain_ops, mock_client):
    mock_response = {"status": "deleted"}
    mock_client.delete.return_value = mock_response

    result = await domain_ops.delete_domain_record("example.com", "record_id")
    assert result["status"] == "deleted"


@pytest.mark.asyncio
async def test_get_domain_info(domain_ops, domain_info):
    """Test getting domain information."""
    domain_ops._client.get_domain = AsyncMock(return_value=domain_info)
    result = await domain_ops.get_domain_info("example.com")
    assert isinstance(result, DomainInfo)
    assert result.name == "example.com"
    assert result.status == "active"
    domain_ops._client.get_domain.assert_called_once_with("example.com")


@pytest.mark.asyncio
async def test_get_domain_info_not_found(domain_ops):
    """Test getting information for non-existent domain."""
    domain_ops._client.get_domain = AsyncMock(side_effect=APIError("Domain not found"))
    with pytest.raises(APIError):
        await domain_ops.get_domain_info("nonexistent.com")


@pytest.mark.asyncio
async def test_update_nameservers(domain_ops):
    """Test updating domain nameservers."""
    new_nameservers = ["ns3.example.com", "ns4.example.com"]
    mock_response = {"nameservers": new_nameservers, "status": "success"}
    domain_ops._client.put = AsyncMock(return_value=mock_response)

    result = await domain_ops.update_nameservers("example.com", new_nameservers)
    assert isinstance(result, OperationResponse)
    assert result.status == "success"
    assert result.operation == "update_nameservers"
    assert result.data["nameservers"] == new_nameservers
    domain_ops._client.put.assert_called_once_with(
        "/domain/example.com/nameservers", json={"nameservers": new_nameservers}
    )


@pytest.mark.asyncio
async def test_update_nameservers_invalid(domain_ops):
    """Test updating nameservers with invalid values."""
    invalid_nameservers = []  # Empty nameservers list should raise ValueError
    with pytest.raises(ValueError, match="Nameservers list cannot be empty"):
        await domain_ops.update_nameservers("example.com", invalid_nameservers)


@pytest.mark.asyncio
async def test_add_dns_record(domain_ops):
    """Test adding a DNS record."""
    record = DNSRecord(
        id="record2", type="A", name="api", content="192.0.2.2", ttl=3600
    )
    domain_ops._client.add_record = AsyncMock(return_value=record)

    result = await domain_ops.add_record("example.com", record)
    assert isinstance(result, DNSRecord)
    assert result.name == "api"
    assert result.content == "192.0.2.2"
    domain_ops._client.add_record.assert_called_once_with("example.com", record)


@pytest.mark.asyncio
async def test_delete_dns_record(domain_ops):
    """Test deleting a DNS record."""
    domain_ops._client.delete_record = AsyncMock(return_value=True)

    result = await domain_ops.delete_record("example.com", "record1")
    assert result is True
    domain_ops._client.delete_record.assert_called_once_with("example.com", "record1")
