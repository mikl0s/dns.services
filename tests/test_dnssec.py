"""Tests for DNSSEC management functionality."""

import pytest
from unittest.mock import Mock, AsyncMock

from dns_services_gateway.dnssec import DNSSECKey, DNSSECManager
from dns_services_gateway.exceptions import APIError
from dns_services_gateway.client import DNSServicesClient


@pytest.fixture
def mock_client():
    """Return a mock DNS Services client."""
    client = Mock(spec=DNSServicesClient)
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.delete = AsyncMock()
    return client


@pytest.fixture
def dnssec_manager(mock_client):
    """Return a DNSSEC manager with mock client."""
    return DNSSECManager(mock_client)


@pytest.fixture
def sample_dnssec_key():
    """Return a sample DNSSEC key for testing."""
    return DNSSECKey(
        key_tag=12345,
        algorithm=13,  # ECDSAP256SHA256
        digest_type=2,  # SHA-256
        digest="abcdef1234567890",
        flags=256,
        protocol=3,
        public_key="sample_public_key_data",
    )


@pytest.fixture
def sample_dnssec_response(sample_dnssec_key):
    """Return a sample DNSSEC response for testing."""
    return {
        "keys": [
            {
                "key_tag": sample_dnssec_key.key_tag,
                "algorithm": sample_dnssec_key.algorithm,
                "digest_type": sample_dnssec_key.digest_type,
                "digest": sample_dnssec_key.digest,
                "flags": sample_dnssec_key.flags,
                "protocol": sample_dnssec_key.protocol,
                "public_key": sample_dnssec_key.public_key,
            }
        ]
    }


@pytest.mark.asyncio
async def test_list_dnssec_keys(dnssec_manager, mock_client, sample_dnssec_response):
    """Test listing DNSSEC keys."""
    domain = "example.com"
    mock_client.get.return_value = sample_dnssec_response

    response = await dnssec_manager.list_keys(domain)

    assert response.success is True
    assert len(response.keys) == 1
    assert response.keys[0].key_tag == 12345
    mock_client.get.assert_awaited_once_with("/domain/example.com/dnssec")


@pytest.mark.asyncio
async def test_add_dnssec_key(dnssec_manager, mock_client, sample_dnssec_key):
    """Test adding a DNSSEC key."""
    domain = "example.com"
    mock_client.post.return_value = {"key": sample_dnssec_key.model_dump()}

    response = await dnssec_manager.add_key(
        domain=domain, algorithm=13, public_key="sample_public_key_data", flags=256
    )

    assert response.success is True
    assert response.keys is not None
    assert len(response.keys) == 1
    assert response.keys[0].key_tag == sample_dnssec_key.key_tag
    mock_client.post.assert_awaited_once_with(
        "/domain/example.com/dnssec",
        data={"algorithm": 13, "public_key": "sample_public_key_data", "flags": 256},
    )


@pytest.mark.asyncio
async def test_remove_dnssec_key(dnssec_manager, mock_client):
    """Test removing a DNSSEC key."""
    domain = "example.com"
    key_tag = 12345
    mock_client.delete.return_value = {}

    response = await dnssec_manager.remove_key(domain, key_tag)

    assert response.success is True
    assert response.keys is None
    mock_client.delete.assert_awaited_once_with("/domain/example.com/dnssec/12345")


@pytest.mark.asyncio
async def test_list_dnssec_keys_error(dnssec_manager, mock_client):
    """Test error handling when listing DNSSEC keys fails."""
    domain = "example.com"
    mock_client.get.side_effect = APIError("Failed to retrieve DNSSEC keys")

    response = await dnssec_manager.list_keys(domain)

    assert response.success is False
    assert "Failed to retrieve DNSSEC keys" in response.message
    assert response.keys is None


@pytest.mark.asyncio
async def test_add_dnssec_key_error(dnssec_manager, mock_client):
    """Test error handling when adding a DNSSEC key fails."""
    domain = "example.com"
    mock_client.post.side_effect = APIError("Failed to add DNSSEC key")

    response = await dnssec_manager.add_key(
        domain=domain, algorithm=13, public_key="sample_public_key_data"
    )

    assert response.success is False
    assert "Failed to add DNSSEC key" in response.message
    assert response.keys is None


@pytest.mark.asyncio
async def test_remove_dnssec_key_error(dnssec_manager, mock_client):
    """Test error handling when removing a DNSSEC key fails."""
    domain = "example.com"
    key_tag = 12345
    mock_client.delete.side_effect = APIError("Failed to remove DNSSEC key")

    response = await dnssec_manager.remove_key(domain, key_tag)

    assert response.success is False
    assert "Failed to remove DNSSEC key" in response.message
    assert response.keys is None
