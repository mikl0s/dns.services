"""Tests for DNS template validator."""

import pytest
from typing import Dict, List, Any

from dns_services_gateway.templates.core.validator import TemplateValidator
from dns_services_gateway.templates.models.base import EnvironmentModel, RecordModel


@pytest.fixture
def basic_template_data() -> Dict[str, Any]:
    """Create basic template data for testing."""
    return {
        "metadata": {
            "name": "test-template",
            "version": "1.0.0",
            "description": "Test template",
            "author": "Test Author",
            "created": "2024-03-20T12:00:00Z",
            "updated": "2024-03-20T12:00:00Z",
            "tags": [],
        },
        "variables": {
            "domain": "example.com",
            "ttl": 3600,
            "nameservers": ["ns1.example.com", "ns2.example.com"],
            "custom_vars": {},
        },
        "environments": {},
        "records": {"A": [], "AAAA": [], "CNAME": [], "MX": [], "TXT": []},
    }


@pytest.mark.asyncio
async def test_validate_template_basic(basic_template_data):
    """Test basic template validation."""
    validator = TemplateValidator(template_data=basic_template_data)
    result = await validator.validate_template()
    assert result.is_valid, result.errors


@pytest.mark.asyncio
async def test_validate_template_missing_required_variables(basic_template_data):
    """Test validation with missing required variables."""
    data = basic_template_data.copy()
    data["variables"] = {
        "domain": "example.com",
        # Missing ttl and nameservers
    }
    validator = TemplateValidator(template_data=data)
    result = await validator.validate_template()
    assert not result.is_valid
    assert any("Field required" in error for error in result.errors)


@pytest.mark.asyncio
async def test_validate_template_duplicate_environment(basic_template_data):
    """Test validation with duplicate environment."""
    data = basic_template_data.copy()
    data["environments"] = {
        "prod": {"name": "production", "variables": {"ttl": 3600}},
        "staging": {"name": "production", "variables": {"ttl": 1800}},  # Duplicate name
    }
    validator = TemplateValidator(template_data=data)
    result = await validator.validate_template()
    assert not result.is_valid
    assert any("Duplicate environment name" in error for error in result.errors)


@pytest.mark.asyncio
async def test_validate_environment_variables(basic_template_data):
    """Test environment variables validation."""
    data = basic_template_data.copy()
    data["environments"] = {
        "prod": {
            "name": "production",
            "variables": {
                "ttl": "${global.ttl}",  # Reference to global variable
                "custom": "${nonexistent}",  # Reference to nonexistent variable
            },
        }
    }
    validator = TemplateValidator(template_data=data)
    result = await validator.validate_template()
    assert not result.is_valid
    assert any("Undefined variable reference" in error for error in result.errors)


@pytest.mark.asyncio
async def test_validate_records_basic(basic_template_data):
    """Test basic record validation."""
    data = basic_template_data.copy()
    data["records"] = {
        "A": [{"name": "www", "type": "A", "ttl": "${ttl}", "value": "192.0.2.1"}]
    }
    validator = TemplateValidator(template_data=data)
    result = await validator.validate_template()
    assert result.is_valid, result.errors


@pytest.mark.asyncio
async def test_validate_records_invalid_hostname(basic_template_data):
    """Test record validation with invalid hostname."""
    data = basic_template_data.copy()
    data["records"] = {
        "A": [
            {
                "name": "-invalid-",  # Invalid hostname
                "type": "A",
                "ttl": "${ttl}",
                "value": "192.0.2.1",
            }
        ]
    }
    validator = TemplateValidator(template_data=data)
    result = await validator.validate_template()
    assert not result.is_valid
    assert any("Invalid hostname" in error for error in result.errors)


@pytest.mark.asyncio
async def test_validate_records_invalid_variable_reference(basic_template_data):
    """Test record validation with invalid variable reference."""
    data = basic_template_data.copy()
    data["records"] = {
        "A": [
            {
                "name": "www",
                "type": "A",
                "ttl": "${invalid_ttl}",  # Reference to nonexistent variable
                "value": "192.0.2.1",
            }
        ]
    }
    validator = TemplateValidator(template_data=data)
    result = await validator.validate_template()
    assert not result.is_valid
    assert any("Undefined variable reference" in error for error in result.errors)


@pytest.mark.asyncio
async def test_validate_cname_conflicts(basic_template_data):
    """Test validation of CNAME record conflicts."""
    data = basic_template_data.copy()
    data["records"] = {
        "CNAME": [
            {"name": "www", "type": "CNAME", "ttl": "${ttl}", "value": "example.com"}
        ],
        "A": [
            {"name": "www", "type": "A", "ttl": "${ttl}", "value": "192.0.2.1"}
        ],  # Conflict with CNAME
    }
    validator = TemplateValidator(template_data=data)
    result = await validator.validate_template()
    assert not result.is_valid
    assert any("CNAME record conflict" in error for error in result.errors)


@pytest.mark.asyncio
async def test_validate_template_complex(basic_template_data):
    """Test complex template validation with multiple environments and records."""
    data = basic_template_data.copy()
    data.update(
        {
            "environments": {
                "prod": {
                    "name": "production",
                    "variables": {"ttl": 3600, "ip": "192.0.2.1"},
                },
                "staging": {
                    "name": "staging",
                    "variables": {"ttl": 1800, "ip": "192.0.2.2"},
                },
            },
            "records": {
                "A": [
                    {"name": "www", "type": "A", "ttl": "${ttl}", "value": "${ip}"},
                    {"name": "api", "type": "A", "ttl": "${ttl}", "value": "${ip}"},
                ],
                "CNAME": [
                    {
                        "name": "app",
                        "type": "CNAME",
                        "ttl": "${ttl}",
                        "value": "www.${domain}",
                    }
                ],
            },
        }
    )
    validator = TemplateValidator(template_data=data)
    result = await validator.validate_template()
    assert result.is_valid, result.errors


@pytest.mark.asyncio
async def test_validate_template_with_invalid_records(basic_template_data):
    """Test template validation with invalid records."""
    data = basic_template_data.copy()
    data["records"] = {
        "A": [
            {
                "name": "www",
                "type": "A",
                "ttl": "${ttl}",
                "value": "invalid-ip",  # Invalid IP address
            }
        ],
        "CNAME": [
            {
                "name": "app",
                "type": "CNAME",
                "ttl": "${ttl}",
                "value": "-invalid-hostname-",  # Invalid hostname
            }
        ],
    }
    validator = TemplateValidator(template_data=data)
    result = await validator.validate_template()
    assert not result.is_valid
    assert any("Invalid IP address" in error for error in result.errors)


@pytest.mark.asyncio
async def test_find_variable_references():
    """Test finding variable references in string."""
    validator = TemplateValidator()
    assert validator.find_variable_references("${var}") == {"var"}
    assert validator.find_variable_references("${a} ${b.c}") == {"a", "b.c"}
    assert validator.find_variable_references("no variables") == set()


@pytest.mark.parametrize(
    "hostname,expected",
    [
        ("@", True),
        ("example.com", True),
        ("sub.example.com", True),
        ("test-1.example.com", True),
        ("", False),
        (".example.com", False),
        ("example..com", False),
        ("-example.com", False),
        ("example-.com", False),
        ("exam*ple.com", False),
    ],
)
def test_is_valid_hostname(hostname: str, expected: bool):
    """Test hostname validation."""
    validator = TemplateValidator()
    assert validator.is_valid_hostname(hostname) == expected
