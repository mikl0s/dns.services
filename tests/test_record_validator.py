"""Tests for DNS record validator."""

import pytest
from pydantic_core import ValidationError
from dns_services_gateway.templates.records.validator import RecordValidator
from dns_services_gateway.templates.models.base import RecordModel
from dns_services_gateway.templates.records.groups import RecordGroup, MXRecord


@pytest.fixture
def validator():
    """Create a record validator instance."""
    return RecordValidator("example.com")


@pytest.fixture
def basic_record():
    """Create a basic valid record."""
    return RecordModel(
        name="test", type="A", value="192.168.1.1", ttl=300, description="Test record"
    )


def test_normalize_name(validator):
    """Test record name normalization."""
    assert validator._normalize_name("test") == "test.example.com"
    assert validator._normalize_name("test.") == "test.example.com"
    assert validator._normalize_name("@") == "example.com"


def test_validate_groups_duplicate_names(validator):
    """Test validation of duplicate record names across groups."""
    records = [
        RecordModel(name="test", type="A", value="192.168.1.1", ttl=300),
        RecordModel(name="test", type="A", value="192.168.1.2", ttl=300),
    ]
    group = RecordGroup(name="group1", description="Test group")
    group.records = records

    errors = validator.validate_groups({"group1": records})
    assert len(errors) == 1
    assert "Duplicate record name" in errors[0]


def test_validate_groups_cname_conflicts(validator):
    """Test validation of CNAME conflicts."""
    records = [
        RecordModel(name="test", type="CNAME", value="example.com", ttl=300),
        RecordModel(name="test", type="A", value="192.168.1.1", ttl=300),
    ]
    group = RecordGroup(name="group1", description="Test group")
    group.records = records

    errors = validator.validate_groups({"group1": records})
    assert len(errors) == 1
    assert "CNAME record" in errors[0]
    assert "conflicts with A record" in errors[0]


def test_validate_groups_mx_priority(validator):
    """Test validation of MX record priorities."""
    records = [
        MXRecord(name="mail1", value="mail1.example.com", priority=10, ttl=300),
        MXRecord(name="mail2", value="mail2.example.com", priority=10, ttl=300),
    ]
    group = RecordGroup(name="group1", description="Test group")
    group.records = records

    errors = validator.validate_groups({"group1": records})
    assert len(errors) == 1
    assert "Duplicate MX priority" in errors[0]


def test_validate_groups_mx_missing_priority(validator):
    """Test validation of MX records without priority."""
    with pytest.raises(ValidationError) as exc_info:
        MXRecord(name="mail", value="mail.example.com", ttl=300)
    assert "Field required" in str(exc_info.value)


def test_validate_record_missing_fields(validator):
    """Test validation of record with missing required fields."""
    with pytest.raises(ValidationError) as exc_info:
        RecordModel(name="test", type="A")
    assert "Field required" in str(exc_info.value)


def test_validate_record_mx_priority(validator):
    """Test validation of MX record priority."""
    # Test missing priority (should be caught by Pydantic validation)
    with pytest.raises(ValidationError) as exc_info:
        MXRecord(name="mail", value="mail.example.com", ttl=300)
    assert "Field required" in str(exc_info.value)

    # Test invalid priority type (should be caught by Pydantic validation)
    with pytest.raises(ValidationError) as exc_info:
        MXRecord(name="mail", value="mail.example.com", priority="10", ttl=300)
    assert "Priority must be an integer" in str(exc_info.value)

    # Test invalid priority value (should be caught by Pydantic validation)
    with pytest.raises(ValidationError) as exc_info:
        MXRecord(name="mail", value="mail.example.com", priority=-1, ttl=300)
    assert "Priority must be non-negative" in str(exc_info.value)

    # Test valid priority
    MXRecord(name="mail", value="mail.example.com", priority=10, ttl=300)
