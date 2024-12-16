"""Tests for data models."""

from datetime import datetime, timezone, timedelta
import pytest
from pydantic import ValidationError
from dns_services_gateway.models import (
    DNSRecord,
    OperationResponse,
    DomainInfo,
    AuthResponse,
    NameserverUpdate,
    NameserverResponse,
    DomainAvailabilityRequest,
    DomainAvailabilityResponse,
    TLDInfo,
    TLDListResponse,
    BulkDomainListResponse,
)


def test_dns_record():
    """Test DNSRecord model."""
    # Test valid record
    record = DNSRecord(
        id="123",
        type="A",
        name="example.com",
        content="192.168.1.1",
        ttl=3600,
        priority=10,
        proxied=True,
    )
    assert record.id == "123"
    assert record.type == "A"
    assert record.name == "example.com"
    assert record.content == "192.168.1.1"
    assert record.ttl == 3600
    assert record.priority == 10
    assert record.proxied is True

    # Test optional fields
    record = DNSRecord(
        id="123",
        type="A",
        name="example.com",
        content="192.168.1.1",
    )
    assert record.ttl == 3600  # default
    assert record.priority is None
    assert record.proxied is False  # default


def test_operation_response():
    """Test OperationResponse model."""
    # Test with minimal fields
    response = OperationResponse(
        status="success",
        operation="create",
    )
    assert response.status == "success"
    assert response.operation == "create"
    assert isinstance(response.timestamp, datetime)
    assert response.data == {}
    assert response.metadata == {}

    # Test with all fields
    now = datetime.now(timezone.utc)
    response = OperationResponse(
        status="error",
        operation="delete",
        timestamp=now,
        data={"error": "Not found"},
        metadata={"domain": "example.com"},
    )
    assert response.status == "error"
    assert response.operation == "delete"
    assert response.timestamp == now
    assert response.data == {"error": "Not found"}
    assert response.metadata == {"domain": "example.com"}


def test_domain_info():
    """Test DomainInfo model."""
    expires = datetime.now(timezone.utc) + timedelta(days=365)
    domain = DomainInfo(
        id="123",
        name="example.com",
        status="active",
        expires=expires,
        auto_renew=True,
        nameservers=["ns1.example.com", "ns2.example.com"],
        records=[
            DNSRecord(
                id="1",
                type="A",
                name="example.com",
                content="192.168.1.1",
            )
        ],
    )
    assert domain.id == "123"
    assert domain.name == "example.com"
    assert domain.status == "active"
    assert domain.expires == expires
    assert domain.auto_renew is True
    assert len(domain.nameservers) == 2
    assert len(domain.records) == 1
    assert isinstance(domain.records[0], DNSRecord)


def test_auth_response():
    """Test AuthResponse model."""
    # Test with token string
    response = AuthResponse(token="test_token")
    assert response.token == "test_token"
    assert isinstance(response.expires, datetime)
    assert response.refresh_token is None

    # Test with expiration string
    expiration = datetime.now(timezone.utc) + timedelta(hours=1)
    response = AuthResponse(
        token="test_token",
        expiration=expiration.isoformat(),
    )
    assert response.token == "test_token"
    assert response.expires == expiration
    assert response.expiration == expiration.isoformat()

    # Test with datetime expiration
    response = AuthResponse(
        token="test_token",
        expiration=expiration,
    )
    assert response.token == "test_token"
    assert response.expires == expiration
    assert response.expiration == expiration.isoformat()


def test_nameserver_update():
    """Test NameserverUpdate model."""
    # Test valid nameservers
    update = NameserverUpdate(
        domain="example.com",
        nameservers=["ns1.example.com", "ns2.example.com"],
    )
    assert update.domain == "example.com"
    assert len(update.nameservers) == 2

    # Test invalid nameservers
    with pytest.raises(ValidationError):
        NameserverUpdate(domain="example.com", nameservers=[])

    with pytest.raises(ValidationError):
        NameserverUpdate(domain="example.com", nameservers=["invalid..ns"])

    # Test invalid domain
    with pytest.raises(ValidationError):
        NameserverUpdate(domain="", nameservers=["ns1.example.com"])


def test_nameserver_response():
    """Test NameserverResponse model."""
    response = NameserverResponse(
        domain="example.com",
        nameservers=["ns1.example.com", "ns2.example.com"],
        status="success",
    )
    assert response.domain == "example.com"
    assert len(response.nameservers) == 2
    assert response.status == "success"
    assert isinstance(response.updated, datetime)


def test_domain_availability_request():
    """Test DomainAvailabilityRequest model."""
    # Test valid request
    request = DomainAvailabilityRequest(domain="example.com")
    assert request.domain == "example.com"
    assert request.check_premium is False

    # Test domain validation
    with pytest.raises(ValidationError):
        DomainAvailabilityRequest(domain="")

    # Test case normalization
    request = DomainAvailabilityRequest(domain="EXAMPLE.COM")
    assert request.domain == "example.com"


def test_domain_availability_response():
    """Test DomainAvailabilityResponse model."""
    response = DomainAvailabilityResponse(
        domain="example.com",
        available=True,
        premium=True,
        price=29.99,
        currency="USD",
    )
    assert response.domain == "example.com"
    assert response.available is True
    assert response.premium is True
    assert response.price == 29.99
    assert response.currency == "USD"
    assert isinstance(response.timestamp, datetime)


def test_tld_info():
    """Test TLDInfo model."""
    tld = TLDInfo(
        name="com",
        available=True,
        price=10.99,
        currency="USD",
        restrictions="None",
    )
    assert tld.name == "com"
    assert tld.available is True
    assert tld.price == 10.99
    assert tld.currency == "USD"
    assert tld.restrictions == "None"


def test_tld_list_response():
    """Test TLDListResponse model."""
    response = TLDListResponse(
        tlds=[
            TLDInfo(name="com", available=True),
            TLDInfo(name="net", available=True),
        ],
        total=2,
    )
    assert len(response.tlds) == 2
    assert response.total == 2
    assert isinstance(response.timestamp, datetime)


def test_bulk_domain_list_response():
    """Test BulkDomainListResponse model."""
    response = BulkDomainListResponse(
        domains=[
            DomainInfo(id="1", name="example.com", status="active"),
            DomainInfo(id="2", name="example.net", status="active"),
        ],
        total=2,
        page=1,
        per_page=20,
        has_more=False,
        metadata={"filter": "active"},
    )
    assert len(response.domains) == 2
    assert response.total == 2
    assert response.page == 1
    assert response.per_page == 20
    assert response.has_more is False
    assert response.metadata == {"filter": "active"}
    assert isinstance(response.timestamp, datetime)
