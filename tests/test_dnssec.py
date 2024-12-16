"""Tests for DNSSEC management functionality."""

import pytest
from unittest.mock import Mock, AsyncMock

from dns_services_gateway.dnssec import (
    DNSSECKey,
    DNSSECManager,
    DNSSECKeyConfig,
    DNSSECSigningConfig,
    DNSSECStatus,
)
from dns_services_gateway.exceptions import APIError
from dns_services_gateway.client import DNSServicesClient


@pytest.fixture
def mock_client():
    """Return a mock DNS Services client."""
    client = Mock(spec=DNSServicesClient)
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.delete = AsyncMock()
    client.put = AsyncMock()
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


@pytest.fixture
def sample_key_config():
    """Return a sample DNSSEC key configuration for testing."""
    return DNSSECKeyConfig(
        algorithm=13, key_size=2048, rotation_interval=30, signing_practice="KSK"
    )


@pytest.fixture
def sample_signing_config(sample_key_config):
    """Return a sample DNSSEC signing configuration for testing."""
    return DNSSECSigningConfig(
        enabled=True,
        auto_signing=True,
        nsec3=True,
        nsec3_iterations=10,
        nsec3_salt_length=16,
        key_config=sample_key_config,
    )


@pytest.fixture
def sample_status_response(sample_dnssec_key):
    """Return a sample DNSSEC status response for testing."""
    return {
        "domain": "example.com",
        "is_signed": True,
        "keys": [sample_dnssec_key.model_dump()],
        "next_key_event": "2024-12-20T00:00:00Z",
        "ds_records": ["sample DS record"],
        "validation_status": "valid",
        "last_signed": "2024-12-15T02:40:42Z",
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


@pytest.mark.asyncio
async def test_generate_key(
    dnssec_manager, mock_client, sample_dnssec_key, sample_key_config
):
    """Test generating a DNSSEC key."""
    domain = "example.com"
    mock_client.post.return_value = {"key": sample_dnssec_key.model_dump()}

    response = await dnssec_manager.generate_key(domain, sample_key_config)

    assert response.key_tag == sample_dnssec_key.key_tag
    mock_client.post.assert_awaited_once_with(
        "/domain/example.com/dnssec/generate", data=sample_key_config.model_dump()
    )


@pytest.mark.asyncio
async def test_rotate_keys(dnssec_manager, mock_client, sample_dnssec_key):
    """Test rotating DNSSEC keys."""
    domain = "example.com"
    mock_client.post.return_value = {"keys": [sample_dnssec_key.model_dump()]}

    response = await dnssec_manager.rotate_keys(domain)

    assert response.success is True
    assert response.keys is not None
    assert len(response.keys) == 1
    assert response.keys[0].key_tag == sample_dnssec_key.key_tag
    mock_client.post.assert_awaited_once_with("/domain/example.com/dnssec/rotate")


@pytest.mark.asyncio
async def test_manage_ds_records(dnssec_manager, mock_client):
    """Test managing DS records."""
    domain = "example.com"
    operation = "add"
    records = ["sample DS record"]
    mock_client.post.return_value = {}

    response = await dnssec_manager.manage_ds_records(domain, operation, records)

    assert response.success is True
    mock_client.post.assert_awaited_once_with(
        "/domain/example.com/dnssec/ds",
        data={"operation": operation, "records": records},
    )


@pytest.mark.asyncio
async def test_configure_signing(dnssec_manager, mock_client, sample_signing_config):
    """Test configuring DNSSEC signing."""
    domain = "example.com"
    mock_client.put.return_value = {"success": True}

    response = await dnssec_manager.configure_signing(domain, sample_signing_config)

    assert response is True
    mock_client.put.assert_awaited_once_with(
        "/domain/example.com/dnssec/signing", data=sample_signing_config.model_dump()
    )


@pytest.mark.asyncio
async def test_get_status(dnssec_manager, mock_client, sample_status_response):
    """Test getting DNSSEC status."""
    domain = "example.com"
    mock_client.get.return_value = sample_status_response

    status = await dnssec_manager.get_status(domain)

    assert status.domain == "example.com"
    assert status.is_signed is True
    assert len(status.keys) == 1
    assert status.next_key_event == "2024-12-20T00:00:00Z"
    assert status.validation_status == "valid"
    mock_client.get.assert_awaited_once_with("/domain/example.com/dnssec/status")


@pytest.mark.asyncio
async def test_generate_key_error(dnssec_manager, mock_client, sample_key_config):
    """Test error handling when generating a DNSSEC key fails."""
    domain = "example.com"
    mock_client.post.side_effect = APIError("Failed to generate key")

    with pytest.raises(APIError) as exc_info:
        await dnssec_manager.generate_key(domain, sample_key_config)
    assert str(exc_info.value) == "Failed to generate key"


@pytest.mark.asyncio
async def test_rotate_keys_error(dnssec_manager, mock_client):
    """Test error handling when rotating DNSSEC keys fails."""
    domain = "example.com"
    mock_client.post.side_effect = APIError("Failed to rotate keys")

    response = await dnssec_manager.rotate_keys(domain)

    assert response.success is False
    assert "Failed to rotate keys" in response.message
    assert response.keys is None


@pytest.mark.asyncio
async def test_manage_ds_records_error(dnssec_manager, mock_client):
    """Test error handling when managing DS records fails."""
    domain = "example.com"
    mock_client.post.side_effect = APIError("Failed to manage DS records")

    response = await dnssec_manager.manage_ds_records(domain, "add", ["record"])

    assert response.success is False
    assert "Failed to manage DS records" in response.message
    assert response.keys is None


@pytest.mark.asyncio
async def test_configure_signing_error(
    dnssec_manager, mock_client, sample_signing_config
):
    """Test error handling when configuring signing fails."""
    domain = "example.com"
    mock_client.put.side_effect = APIError("Failed to configure signing")

    with pytest.raises(APIError) as exc_info:
        await dnssec_manager.configure_signing(domain, sample_signing_config)
    assert str(exc_info.value) == "Failed to configure signing"


@pytest.mark.asyncio
async def test_get_status_error(dnssec_manager, mock_client):
    """Test error handling when getting status fails."""
    domain = "example.com"
    mock_client.get.side_effect = APIError("Failed to get status")

    with pytest.raises(APIError) as exc_info:
        await dnssec_manager.get_status(domain)

    assert "Failed to get status" in str(exc_info.value)
