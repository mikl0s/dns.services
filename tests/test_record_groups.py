"""Tests for record groups functionality."""

import pytest
from typing import List, cast
from dns_services_gateway.templates.models.base import RecordModel
from dns_services_gateway.templates.records.groups import (
    ARecord,
    AAAARecord,
    CNAMERecord,
    MXRecord,
    TXTRecord,
    CAARecord,
    RecordGroup,
    RecordGroupManager,
)
from pydantic import ValidationError


def test_a_record_validation():
    """Test A record validation."""
    # Valid IPv4
    record = ARecord(
        name="test", value="192.168.1.1", ttl=300, description="Valid A record"
    )
    assert record.value == "192.168.1.1"

    # Invalid IPv4
    with pytest.raises(ValidationError) as exc_info:
        ARecord(name="test", value="invalid", ttl=300, description="Invalid A record")
    assert "Value error, Expected 4 octets in 'invalid'" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        ARecord(
            name="test",
            value="256.256.256.256",
            ttl=300,
            description="Invalid A record",
        )
    assert "Value error, Octet 256 (> 255) not permitted in '256.256.256.256'" in str(
        exc_info.value
    )


def test_aaaa_record_validation():
    """Test AAAA record validation."""
    # Valid IPv6
    record = AAAARecord(
        name="test", value="2001:db8::1", ttl=300, description="Valid AAAA record"
    )
    assert record.value == "2001:db8::1"

    # Invalid IPv6
    with pytest.raises(ValidationError) as exc_info:
        AAAARecord(
            name="test", value="invalid", ttl=300, description="Invalid AAAA record"
        )
    assert "Value error, At least 3 parts expected in 'invalid'" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        AAAARecord(
            name="test", value="2001:zz8::1", ttl=300, description="Invalid AAAA record"
        )
    assert "Value error, Only hex digits permitted in 'zz8' in '2001:zz8::1'" in str(
        exc_info.value
    )


def test_cname_record_validation():
    """Test CNAME record validation."""
    # Valid hostname
    record = CNAMERecord(
        name="test", value="example.com", ttl=300, description="Test CNAME record"
    )
    assert record.value == "example.com"

    # Invalid hostname (too long)
    with pytest.raises(ValidationError, match="Domain name exceeds maximum length"):
        CNAMERecord(
            name="test", value="a" * 256, ttl=300, description="Invalid CNAME record"
        )


def test_mx_record_validation():
    """Test MX record validation."""
    # Valid MX record
    record = MXRecord(
        name="test",
        value="mail.example.com",
        priority=10,
        ttl=300,
        description="Test MX record",
    )
    assert record.value == "mail.example.com"
    assert record.priority == 10

    # Invalid priority
    with pytest.raises(ValueError):
        MXRecord(
            name="test",
            value="mail.example.com",
            priority=70000,
            ttl=300,
            description="Invalid MX record",
        )

    # Invalid hostname
    long_hostname = "a" * 256
    with pytest.raises(ValidationError) as exc_info:
        MXRecord(
            name="test",
            value=long_hostname,
            priority=10,
            ttl=300,
            description="Invalid MX record",
        )
    assert "Value error, Domain name exceeds maximum length" in str(exc_info.value)


def test_txt_record_validation():
    """Test TXT record validation."""
    # Valid TXT record
    record = TXTRecord(
        name="test",
        value="v=spf1 include:_spf.example.com ~all",
        ttl=300,
        description="Test TXT record",
    )
    assert record.value == "v=spf1 include:_spf.example.com ~all"

    # Test with quotes
    record = TXTRecord(
        name="test",
        value='"quoted text"',
        ttl=300,
        description="Test TXT record with quotes",
    )
    assert record.value == '"quoted text"'


def test_caa_record_validation():
    """Test CAA record validation."""
    # Valid CAA record
    record = CAARecord(
        name="test",
        value='"letsencrypt.org"',  # Value must be quoted
        flags=0,
        tag="issue",
        ttl=300,
        description="Test CAA record",
    )
    assert record.value == '"letsencrypt.org"'
    assert record.flags == 0
    assert record.tag == "issue"

    # Invalid flags
    with pytest.raises(ValueError):
        CAARecord(
            name="test",
            value='"letsencrypt.org"',  # Value must be quoted
            flags=256,
            tag="issue",
            ttl=300,
            description="Invalid CAA record",
        )

    # Invalid tag
    with pytest.raises(ValueError):
        CAARecord(
            name="test",
            value='"letsencrypt.org"',  # Value must be quoted
            flags=0,
            tag="invalid",
            ttl=300,
            description="Invalid CAA record",
        )


def test_record_group_creation():
    """Test record group creation and validation."""
    records: List[RecordModel] = [
        cast(
            RecordModel,
            ARecord(
                name="www",
                value="192.168.1.1",
                ttl=300,
                description="Web server A record",
            ),
        ),
        cast(
            RecordModel,
            CNAMERecord(
                name="blog",
                value="www.example.com",
                ttl=300,
                description="Blog CNAME record",
            ),
        ),
    ]

    group = RecordGroup(
        name="web", description="Web server records", enabled=True, records=records
    )

    assert group.name == "web"
    assert group.description == "Web server records"
    assert group.enabled is True
    assert len(group.records) == 2


def test_record_group_manager():
    """Test record group manager functionality."""
    manager = RecordGroupManager()

    # Add groups
    web_group = RecordGroup(
        name="web",
        description="Web server records",
        records=[
            cast(
                RecordModel,
                ARecord(
                    name="www",
                    value="192.168.1.1",
                    ttl=300,
                    description="Web server A record",
                ),
            )
        ],
    )
    mail_group = RecordGroup(
        name="mail",
        description="Mail server records",
        records=[
            cast(
                RecordModel,
                MXRecord(
                    name="@",
                    value="mail.example.com",
                    priority=10,
                    ttl=300,
                    description="Mail server MX record",
                ),
            ),
            cast(
                RecordModel,
                TXTRecord(
                    name="@", value="v=spf1 mx ~all", ttl=300, description="SPF record"
                ),
            ),
        ],
    )

    manager.add_group(web_group)
    manager.add_group(mail_group)

    # Test get_group
    assert manager.get_group("web") == web_group
    assert manager.get_group("nonexistent") is None

    # Test list_groups
    groups = manager.list_groups()
    assert set(groups) == {"web", "mail"}

    # Test merge_groups
    merged = manager.merge_groups(["web", "mail"])
    assert len(merged) == 3  # Total records from both groups

    # Test merge with nonexistent group
    with pytest.raises(KeyError, match="Record group not found: nonexistent"):
        manager.merge_groups(["web", "nonexistent"])


def test_record_group_disabled():
    """Test disabled record group behavior."""
    manager = RecordGroupManager()

    # Add a disabled group
    disabled_group = RecordGroup(
        name="disabled",
        description="Disabled records",
        enabled=False,
        records=[
            cast(
                RecordModel,
                ARecord(
                    name="test",
                    value="192.168.1.1",
                    ttl=300,
                    description="Disabled A record",
                ),
            )
        ],
    )
    manager.add_group(disabled_group)

    # Verify the group exists but returns no records when merging
    assert manager.get_group("disabled") is not None
    merged = manager.merge_groups(["disabled"])
    assert len(merged) == 0  # No records because group is disabled
