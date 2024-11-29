"""Extended tests for models to improve coverage."""

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from dns_services_gateway.models import (
    AuthResponse,
    NameserverUpdate,
    DomainInfo,
    TLDInfo,
    TLDListResponse,
)


def test_auth_response_expiration_from_string():
    """Test AuthResponse with string expiration."""
    expiration = "2024-03-20T12:00:00Z"
    response = AuthResponse(token="test_token", expiration=expiration)
    assert isinstance(response.expires, datetime)
    assert response.expiration == expiration


def test_auth_response_expiration_from_datetime():
    """Test AuthResponse with datetime expiration."""
    now = datetime.now(timezone.utc)
    response = AuthResponse(token="test_token", expiration=now)
    assert response.expires == now
    assert response.expiration == now.isoformat()


def test_auth_response_no_expiration():
    """Test AuthResponse without expiration."""
    response = AuthResponse(token="test_token")
    assert response.expires is not None  # Should default to 1 hour from now
    assert response.expiration is None


def test_nameserver_update_validation():
    """Test NameserverUpdate validation."""
    # Valid nameservers
    update = NameserverUpdate(
        domain="example.com", nameservers=["ns1.example.com", "ns2.example.com"]
    )
    assert update.domain == "example.com"
    assert len(update.nameservers) == 2

    # Invalid nameservers
    with pytest.raises(ValidationError):
        NameserverUpdate(domain="example.com", nameservers=["invalid..ns1", "ns2"])


def test_tld_info_with_restrictions():
    """Test TLDInfo with restrictions."""
    tld = TLDInfo(
        name="dev",
        available=True,
        price=15.99,
        currency="USD",
        restrictions="Developer-focused domains",
    )
    assert tld.name == "dev"
    assert tld.restrictions == "Developer-focused domains"


def test_tld_list_response():
    """Test TLDListResponse with multiple TLDs."""
    tlds = [
        TLDInfo(name="com", available=True, price=10.99, currency="USD"),
        TLDInfo(name="net", available=True, price=12.99, currency="USD"),
        TLDInfo(name="org", available=True, price=11.99, currency="USD"),
    ]
    response = TLDListResponse(tlds=tlds, total=3)
    assert len(response.tlds) == 3
    assert response.total == 3
    assert response.timestamp is not None


def test_domain_info_with_records():
    """Test DomainInfo with DNS records."""
    domain = DomainInfo(
        id="domain123",
        name="example.com",
        status="active",
        auto_renew=True,
        nameservers=["ns1.example.com", "ns2.example.com"],
        records=[
            {
                "id": "record1",
                "type": "A",
                "name": "www",
                "content": "192.0.2.1",
                "ttl": 3600,
            },
            {
                "id": "record2",
                "type": "MX",
                "name": "@",
                "content": "mail.example.com",
                "priority": 10,
                "ttl": 3600,
            },
        ],
    )
    assert domain.id == "domain123"
    assert len(domain.records) == 2
    assert domain.records[1].priority == 10
