"""Tests for the DNS record management module."""

import asyncio
import pytest
from typing import Dict, Any, Optional

from dns_services_gateway.records import (
    RecordType,
    RecordAction,
    ARecord,
    AAAARecord,
    MXRecord,
    CNAMERecord,
    TXTRecord,
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
        def __init__(self):
            self.records = {
                "example.com": [
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
            }

        async def make_request(
            self,
            method: str,
            endpoint: str,
            data: Optional[Dict] = None,
            params: Optional[Dict] = None,
        ):
            if "invalid.com" in endpoint:
                return {"status": "error", "message": "Domain not found"}

            domain = endpoint.split("/")[2]
            if domain not in self.records:
                self.records[domain] = []

            if method == "GET":
                if params:
                    # Filter records by name and type if provided
                    filtered_records = [
                        r
                        for r in self.records[domain]
                        if (not params.get("name") or r["name"] == params["name"])
                        and (not params.get("type") or r["type"] == params["type"])
                    ]
                    return {"status": "success", "data": {"records": filtered_records}}
                return {
                    "status": "success",
                    "data": {"records": self.records[domain]},
                }

            if method == "POST":
                # Create new record
                self.records[domain].append(data)
                return {"status": "success", "data": {"record": data}}

            if method == "PUT":
                # Update existing record
                for i, record in enumerate(self.records[domain]):
                    if (
                        record["name"] == data["name"]
                        and record["type"] == data["type"]
                    ):
                        self.records[domain][i] = data
                        return {"status": "success", "data": {"record": data}}
                return {"status": "error", "message": "Record not found"}

            if method == "DELETE":
                # Delete record
                original_len = len(self.records[domain])
                self.records[domain] = [
                    r
                    for r in self.records[domain]
                    if not (r["name"] == data["name"] and r["type"] == data["type"])
                ]
                if len(self.records[domain]) < original_len:
                    return {"status": "success", "data": {}}
                return {"status": "error", "message": "Record not found"}

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
    assert RecordType.NS == "NS"
    assert RecordType.SRV == "SRV"
    assert RecordType.CAA == "CAA"


def test_a_record_validation():
    """Test A record validation."""
    # Valid A record
    record = ARecord(name="test", value="192.168.1.1")
    assert record.value == "192.168.1.1"
    assert record.ttl == 3600  # Default TTL

    # Invalid IP
    with pytest.raises(ValueError):
        ARecord(name="test", value="256.256.256.256")

    # Invalid TTL
    with pytest.raises(ValueError):
        ARecord(name="test", value="192.168.1.1", ttl=30)  # Less than 60


def test_aaaa_record_validation():
    """Test AAAA record validation."""
    # Valid AAAA record
    record = AAAARecord(name="test", value="2001:db8::1")
    assert record.value == "2001:db8::1"

    # Empty hostname
    with pytest.raises(ValueError):
        AAAARecord(name="", value="2001:db8::1")


def test_cname_record_validation():
    """Test CNAME record validation."""
    # Valid CNAME record
    record = CNAMERecord(name="www", value="example.com")
    assert record.value == "example.com"

    # Root CNAME
    with pytest.raises(ValueError):
        CNAMERecord(name="@", value="example.com")


def test_txt_record_validation():
    """Test TXT record validation."""
    # Valid TXT record
    record = TXTRecord(name="test", value="v=spf1 include:_spf.example.com ~all")
    assert record.value == "v=spf1 include:_spf.example.com ~all"

    # Long TXT record (should be valid)
    long_value = "x" * 500
    record = TXTRecord(name="test", value=long_value)
    assert record.value == long_value


def test_mx_record_validation():
    """Test MX record validation."""
    # Valid MX record
    record = MXRecord(name="@", value="mail.example.com", priority=10)
    assert record.priority == 10

    # Invalid priority (too high)
    with pytest.raises(ValueError):
        MXRecord(name="@", value="mail.example.com", priority=70000)

    # Invalid priority (negative)
    with pytest.raises(ValueError):
        MXRecord(name="@", value="mail.example.com", priority=-1)


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

    # Mock the client to simulate a timeout
    async def mock_request(*args, **kwargs):
        await asyncio.sleep(0.1)  # Add a small delay
        raise asyncio.TimeoutError()

    mocker.patch.object(
        record_manager._client, "make_request", side_effect=mock_request
    )

    # Set a very short timeout to trigger the error
    record_manager._verification_timeout = 0.01
    record_manager._verification_interval = 0.01

    response = await record_manager.batch_manage_records(
        operations=operations,
        domain="example.com",
    )
    assert response.overall_status == "error"
    assert "Operation timed out" in response.failed_operations[0]["error"]


@pytest.mark.asyncio
async def test_manage_record_delete(record_manager):
    """Test record delete operation."""
    # First create a record
    record = ARecord(name="test", value="192.168.1.1")
    await record_manager.manage_record(
        action=RecordAction.CREATE,
        domain="example.com",
        record=record,
    )

    # Then delete it
    response = await record_manager.manage_record(
        action=RecordAction.DELETE,
        domain="example.com",
        record=record,
    )
    assert response.status == "success"
    assert response.operation == RecordAction.DELETE
    assert not response.verified  # Delete operations don't verify


@pytest.mark.asyncio
async def test_manage_record_invalid_data(record_manager):
    """Test handling of invalid record data."""
    # Try to create a record with invalid data
    record = ARecord(name="test", value="192.168.1.1")
    response = await record_manager.manage_record(
        action=RecordAction.CREATE,
        domain="invalid.com",  # This will trigger an error in our mock client
        record=record,
    )
    assert response.status == "error"
    assert not response.verified


@pytest.mark.asyncio
async def test_batch_operation_mixed_types(record_manager):
    """Test batch operation with different record types."""
    operations = [
        RecordOperation(
            action=RecordAction.CREATE,
            record=ARecord(name="test1", value="192.168.1.1"),
        ),
        RecordOperation(
            action=RecordAction.CREATE,
            record=MXRecord(name="@", value="mail.example.com", priority=10),
        ),
        RecordOperation(
            action=RecordAction.CREATE,
            record=TXTRecord(name="txt", value="v=spf1 ~all"),
        ),
    ]

    response = await record_manager.batch_manage_records(
        operations=operations,
        domain="example.com",
    )
    assert response.overall_status == "success"
    assert len(response.operations) == 3
    assert all(op.status == "success" for op in response.operations)
