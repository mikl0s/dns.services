"""Extended tests for template validator."""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, List, Any

from dns_services_gateway.templates.models.base import (
    EnvironmentModel,
    SingleVariableModel,
    RecordModel,
    MetadataModel,
)
from dns_services_gateway.templates.core.validator import TemplateValidator
from dns_services_gateway.exceptions import ValidationError


@pytest.fixture
def validator():
    """Create a TemplateValidator instance for testing."""
    return TemplateValidator(
        {
            "metadata": {
                "name": "test-template",
                "version": "1.0.0",
                "description": "Test template",
                "author": "Test Author",
                "tags": ["test", "example"],
            },
            "variables": {
                "domain": "example.com",
                "ttl": 3600,
                "environment": "production",
                "region": "us-west",
            },
        }
    )


@pytest.fixture
def sample_metadata():
    """Create sample template metadata."""
    return MetadataModel(
        name="test-template",
        version="1.0.0",
        description="Test template",
        author="Test Author",
        tags=["test", "example"],
    )


@pytest.fixture
def sample_variables():
    """Create sample variables for testing."""
    return [
        SingleVariableModel(
            name="domain",
            value="example.com",
            description="Domain name",
        ),
        SingleVariableModel(
            name="ttl",
            value=3600,
            description="Default TTL",
        ),
        SingleVariableModel(
            name="environment",
            value="production",
            description="Environment name",
        ),
        SingleVariableModel(
            name="region",
            value="us-west",
            description="Region name",
        ),
    ]


@pytest.fixture
def sample_records():
    """Create sample DNS records for testing."""
    return {
        "A": [
            RecordModel(type="A", name="www", value="192.0.2.1", ttl=3600),
            RecordModel(type="A", name="api", value="192.0.2.2", ttl=1800),
        ],
        "CNAME": [
            RecordModel(type="CNAME", name="www2", value="www.example.com", ttl=3600)
        ],
    }


@pytest.mark.asyncio
async def test_validate_metadata(validator, sample_metadata):
    """Test metadata validation."""
    result = await validator.validate_metadata(sample_metadata)
    assert result.is_valid
    assert not result.errors


@pytest.mark.asyncio
async def test_validate_metadata_invalid_version(validator, sample_metadata):
    """Test metadata validation with invalid version."""
    sample_metadata.version = "invalid"
    result = await validator.validate_metadata(sample_metadata)
    assert not result.is_valid
    assert any(
        "Version must follow semantic versioning" in error for error in result.errors
    )


@pytest.mark.asyncio
async def test_validate_variables(validator, sample_variables):
    """Test variables validation."""
    variables_dict = {var.name: var.value for var in sample_variables}
    result = await validator.validate_variables(variables_dict)
    assert result.is_valid
    assert not result.errors


@pytest.mark.asyncio
async def test_validate_variables_invalid_ttl(validator, sample_variables):
    """Test variables validation with invalid TTL."""
    sample_variables[1].value = -1
    variables_dict = {var.name: var.value for var in sample_variables}
    result = await validator.validate_variables(variables_dict)
    assert not result.is_valid
    assert any("TTL must be non-negative" in error for error in result.errors)


@pytest.mark.asyncio
async def test_validate_records(validator, sample_records):
    """Test DNS records validation."""
    result = await validator._validate_records(sample_records)
    assert result.is_valid
    assert not result.errors


@pytest.mark.asyncio
async def test_validate_records_invalid_type(validator, sample_records):
    """Test records validation with invalid record type."""
    invalid_records = {"INVALID": [{"name": "test", "value": "invalid", "ttl": 3600}]}
    result = await validator._validate_records(invalid_records)
    assert not result.is_valid
    assert any("Invalid record type: INVALID" in error for error in result.errors)


@pytest.mark.asyncio
async def test_validate_record_name():
    """Test record name validation."""
    validator = TemplateValidator()
    valid_names = ["www", "api", "test-1", "sub.domain"]
    for name in valid_names:
        result = await validator.validate_record_name(name)
        assert result.is_valid is True

    invalid_names = ["", " ", "invalid space", "invalid/char"]
    for name in invalid_names:
        result = await validator.validate_record_name(name)
        assert result.is_valid is False


@pytest.mark.asyncio
async def test_validate_record_value():
    """Test record value validation."""
    validator = TemplateValidator()

    # Test A record validation
    result = await validator.validate_record_value("A", "192.0.2.1")
    assert result.is_valid is True

    result = await validator.validate_record_value("A", "invalid-ip")
    assert result.is_valid is False

    # Test AAAA record validation
    result = await validator.validate_record_value("AAAA", "2001:db8::1")
    assert result.is_valid is True

    result = await validator.validate_record_value("AAAA", "invalid-ip")
    assert result.is_valid is False

    # Test MX record validation
    result = await validator.validate_record_value("MX", "mail.example.com")
    assert result.is_valid is True

    # Test variable reference validation
    result = await validator.validate_record_value("A", "${ip_address}")
    assert result.is_valid is True


@pytest.mark.asyncio
async def test_validate_template(
    validator, sample_metadata, sample_variables, sample_records
):
    """Test complete template validation."""
    result = await validator.validate_template(
        metadata=sample_metadata,
        variables=sample_variables,
        environments={},
        records=sample_records,
    )
    assert result.is_valid
    assert not result.errors


@pytest.mark.asyncio
async def test_validate_variable_references():
    """Test variable reference validation."""
    validator = TemplateValidator()
    validator.variables = {"domain", "ttl", "nameservers"}

    # Test valid references
    references = {"${domain}", "${ttl}", "${nameservers}"}
    result = await validator.validate_variable_references(
        references, validator.variables
    )
    assert result.is_valid is True

    # Test invalid references
    references = {"${nonexistent}", "${invalid}"}
    result = await validator.validate_variable_references(
        references, validator.variables
    )
    assert result.is_valid is False
    assert any("Undefined variable" in error for error in result.errors)
