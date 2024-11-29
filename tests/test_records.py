"""Tests for the DNS record management module."""

import asyncio
import pytest
from typing import Dict, Any, Optional

from dns_services_gateway.records import (
    RecordType,
    RecordAction,
    ARecord,
    MXRecord,
    RecordOperation,
    DNSRecordManager,
)


class MockResponse:
    """Mock response class for simulating API responses."""

    def __init__(self, status: str, data: Optional[Dict[str, Any]] = None):
        """Initialize the mock response with a status and optional data."""
        self.status = status
        self.data = data or {}

    def json(self):
        return {"status": self.status, "data": self.data}


@pytest.fixture
def dns_client():
    """Mock DNS client fixture."""

    class MockClient:
        async def make_request(
            self,
            method: str,
            endpoint: str,
            data: Optional[Dict] = None,
            params: Optional[Dict] = None,
        ):
            if "invalid.com" in endpoint:
                return {"status": "error", "message": "Domain not found"}

            if endpoint == "/domains/example.com/records":
                if method == "GET":
                    return {
                        "status": "success",
                        "data": {
                            "records": [
                                {
                                    "name": "test",
                                    "type": "A",
                                    "value": "192.168.1.1",
                                    "ttl": 3600,
                                },
                                {
                                    "name": "@",
                                    "type": "MX",
                                    "value": "mail.example.com",
                                    "priority": 10,
                                    "ttl": 3600,
                                },
                            ]
                        },
                    }
                return {"status": "success", "data": {"record": data}}
            return {"status": "error", "message": "Invalid request"}

    return MockClient()


@pytest.fixture
def record_manager(dns_client):
    """DNS record manager fixture."""
    return DNSRecordManager(dns_client)


def test_record_type_enum():
    """Test RecordType enum values."""
    assert RecordType.A == "A"
    assert RecordType.AAAA == "AAAA"
    assert RecordType.CNAME == "CNAME"
    assert RecordType.MX == "MX"
    assert RecordType.TXT == "TXT"


def test_a_record_validation():
    """Test A record validation."""
    # Valid A record
    record = ARecord(name="test", value="192.168.1.1")
    assert record.value == "192.168.1.1"

    # Invalid IP
    with pytest.raises(ValueError):
        ARecord(name="test", value="256.256.256.256")


def test_mx_record_validation():
    """Test MX record validation."""
    # Valid MX record
    record = MXRecord(name="@", value="mail.example.com", priority=10)
    assert record.priority == 10

    # Invalid priority
    with pytest.raises(ValueError):
        MXRecord(name="@", value="mail.example.com", priority=70000)


@pytest.mark.asyncio
async def test_manage_record(record_manager):
    """Test single record management."""
    record = ARecord(name="test", value="192.168.1.1")
    response = await record_manager.manage_record(
        action=RecordAction.CREATE,
        domain="example.com",
        record=record,
    )
    assert response.status == "success"
    assert response.verified


@pytest.mark.asyncio
async def test_batch_manage_records(record_manager):
    """Test batch record management."""
    operations = [
        RecordOperation(
            action=RecordAction.CREATE,
            record=ARecord(name="test1", value="192.168.1.1"),
        ),
        RecordOperation(
            action=RecordAction.CREATE,
            record=MXRecord(name="@", value="mail.example.com", priority=10),
        ),
    ]

    # Use a shorter timeout for testing
    record_manager._verification_timeout = 1
    record_manager._verification_interval = 0.1

    response = await record_manager.batch_manage_records(
        operations=operations,
        domain="example.com",
    )
    assert response.overall_status == "success"
    assert len(response.operations) == 2
    assert len(response.failed_operations) == 0


@pytest.mark.asyncio
async def test_verify_record(record_manager):
    """Test record verification."""
    record = ARecord(name="test", value="192.168.1.1")
    verified = await record_manager.verify_record(
        domain="example.com",
        record=record,
    )
    assert verified


@pytest.mark.asyncio
async def test_failed_batch_operation(record_manager):
    """Test batch operation with failures."""
    operations = [
        RecordOperation(
            action=RecordAction.CREATE,
            record=ARecord(name="test1", value="192.168.1.1"),
        ),
        RecordOperation(
            action=RecordAction.CREATE,
            record=ARecord(name="test2", value="192.168.1.2"),
        ),
    ]

    # Use a shorter timeout for testing
    record_manager._verification_timeout = 1
    record_manager._verification_interval = 0.1

    response = await record_manager.batch_manage_records(
        operations=operations,
        domain="invalid.com",  # This domain will trigger an error in our mock client
    )
    assert response.overall_status == "error"
    assert len(response.failed_operations) == 2
    assert "error" in response.failed_operations[0]


@pytest.mark.asyncio
async def test_record_verification_timeout(record_manager):
    """Test record verification timeout."""
    record = ARecord(name="timeout", value="192.168.1.2")
    verified = await record_manager.verify_record(
        domain="example.com", record=record, timeout=1
    )
    assert not verified


@pytest.mark.asyncio
async def test_batch_operation_partial_success(record_manager, mocker):
    """Test batch operation with partial success."""
    operations = [
        RecordOperation(
            action=RecordAction.CREATE,
            record=ARecord(name="test1", value="192.168.1.1"),
        ),
        RecordOperation(
            action=RecordAction.CREATE,
            record=ARecord(name="test2", value="192.168.1.2"),
        ),
    ]

    # Mock the client to succeed for first operation and fail for second
    async def mock_request(method, endpoint, data=None, params=None):
        if data and data.get("name") == "test2":
            return {"status": "error", "message": "Invalid record"}
        return {"status": "success", "data": {"record": data}}

    mocker.patch.object(
        record_manager._client, "make_request", side_effect=mock_request
    )

    # Use a shorter timeout for testing
    record_manager._verification_timeout = 1
    record_manager._verification_interval = 0.1

    response = await record_manager.batch_manage_records(
        operations=operations,
        domain="example.com",
    )
    assert response.overall_status == "partial"
    assert len(response.failed_operations) == 1
    assert len(response.operations) == 2


@pytest.mark.asyncio
async def test_verify_record_dns_error(record_manager, mocker):
    """Test record verification with DNS lookup error."""
    record = ARecord(name="error", value="192.168.1.1")

    # Mock the DNS lookup to raise an exception
    mocker.patch.object(
        record_manager._client, "make_request", side_effect=Exception("DNS error")
    )

    verified = await record_manager.verify_record(
        domain="example.com", record=record, timeout=1
    )
    assert not verified


@pytest.mark.asyncio
async def test_verify_record_with_mx_priority(record_manager):
    """Test MX record verification with priority check."""
    record = MXRecord(name="@", value="mail.example.com", priority=10)
    verified = await record_manager.verify_record(domain="example.com", record=record)
    assert verified


@pytest.mark.asyncio
async def test_batch_operation_timeout(record_manager, mocker):
    """Test batch operation with timeout."""
    operations = [
        RecordOperation(
            action=RecordAction.CREATE,
            record=ARecord(name="test1", value="192.168.1.1"),
        ),
    ]

    # Mock the operation to timeout
    async def mock_wait_for(*args, **kwargs):
        raise asyncio.TimeoutError()

    mocker.patch("asyncio.wait_for", side_effect=mock_wait_for)

    response = await record_manager.batch_manage_records(
        operations=operations,
        domain="example.com",
    )
    assert response.overall_status == "error"
    assert "Operation timed out" in response.failed_operations[0]["error"]
