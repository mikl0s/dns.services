"""Tests for template validator."""

import pytest
from dns_services_gateway.templates.core.validator import TemplateValidator


@pytest.fixture
def basic_variables():
    """Basic valid variables."""
    return {
        "domain": "example.com",
        "ttl": 3600,
        "nameservers": ["ns1.example.com", "ns2.example.com"],
    }


@pytest.fixture
def basic_environment():
    """Basic valid environment."""
    return {
        "description": "Production environment",
        "variables": {
            "ip": "192.168.1.1",
            "subdomain": "www",
        },
    }


@pytest.fixture
def basic_records():
    """Basic valid records."""
    return {
        "A": [
            {
                "name": "www",
                "value": "192.168.1.1",
                "ttl": 300,
                "description": "Web server",
                "type": "A",
            }
        ],
        "CNAME": [
            {
                "name": "blog",
                "value": "www.example.com",
                "ttl": 300,
                "description": "Blog CNAME",
                "type": "CNAME",
            }
        ],
    }


@pytest.mark.asyncio
async def test_validate_template_valid(
    basic_variables, basic_environment, basic_records
):
    """Test validating a valid template."""
    template_data = {
        "metadata": {
            "name": "test-template",
            "version": "1.0.0",
            "description": "Test template",
            "author": "Test Author",
        },
        "variables": basic_variables,
        "environments": {"prod": basic_environment},
        "records": basic_records,
    }
    validator = TemplateValidator(template_data=template_data)
    result = await validator.validate_template()
    assert result.is_valid
    assert not result.errors


@pytest.mark.asyncio
async def test_validate_template_missing_variables(basic_environment, basic_records):
    """Test validating template with missing required variables."""
    template_data = {
        "metadata": {
            "name": "test-template",
            "version": "1.0.0",
            "description": "Test template",
            "author": "Test Author",
        },
        "variables": {},
        "environments": {"prod": basic_environment},
        "records": basic_records,
    }
    validator = TemplateValidator(template_data=template_data)
    result = await validator.validate_template()
    assert not result.is_valid
    assert any("required" in error.lower() for error in result.errors)


@pytest.mark.asyncio
async def test_validate_environment_duplicate(basic_variables, basic_environment):
    """Test validating duplicate environments."""
    template_data = {
        "metadata": {
            "name": "test-template",
            "version": "1.0.0",
            "description": "Test template",
            "author": "Test Author",
        },
        "variables": basic_variables,
        "environments": {
            "prod": basic_environment,
            "staging": basic_environment,
        },
    }
    validator = TemplateValidator(template_data=template_data)
    result = await validator.validate_template()
    assert not result.is_valid
    assert any("duplicate" in error.lower() for error in result.errors)


@pytest.mark.asyncio
async def test_validate_environment_variables_reference(
    basic_variables, basic_environment
):
    """Test validating environment variables with references."""
    env_with_refs = {
        "description": "Environment with references",
        "variables": {
            "ip": "${base_ip}",
            "subdomain": "{{variables.subdomain_prefix}}",
        },
    }
    template_data = {
        "metadata": {
            "name": "test-template",
            "version": "1.0.0",
            "description": "Test template",
            "author": "Test Author",
        },
        "variables": basic_variables,
        "environments": {"prod": env_with_refs},
    }
    validator = TemplateValidator(template_data=template_data)
    result = await validator.validate_template()
    assert not result.is_valid
    assert any("undefined" in error.lower() for error in result.errors)


@pytest.mark.asyncio
async def test_validate_record_invalid_name(basic_variables, basic_environment):
    """Test validating records with invalid names."""
    invalid_records = {
        "A": [
            {
                "name": "invalid..hostname",
                "value": "192.168.1.1",
                "ttl": 300,
                "description": "Invalid hostname",
                "type": "A",
            }
        ],
    }
    template_data = {
        "metadata": {
            "name": "test-template",
            "version": "1.0.0",
            "description": "Test template",
            "author": "Test Author",
        },
        "variables": basic_variables,
        "environments": {"prod": basic_environment},
        "records": invalid_records,
    }
    validator = TemplateValidator(template_data=template_data)
    result = await validator.validate_template()
    assert not result.is_valid
    assert any("invalid hostname" in error.lower() for error in result.errors)


@pytest.mark.asyncio
async def test_validate_record_variable_reference(basic_variables, basic_environment):
    """Test validating records with variable references."""
    records_with_refs = {
        "A": [
            {
                "name": "${hostname}",
                "value": "{{variables.ip}}",
                "ttl": 300,
                "description": "Record with variable references",
                "type": "A",
            }
        ],
    }
    template_data = {
        "metadata": {
            "name": "test-template",
            "version": "1.0.0",
            "description": "Test template",
            "author": "Test Author",
        },
        "variables": basic_variables,
        "environments": {"prod": basic_environment},
        "records": records_with_refs,
    }
    validator = TemplateValidator(template_data=template_data)
    result = await validator.validate_template()
    assert not result.is_valid
    assert any("undefined" in error.lower() for error in result.errors)


def test_find_variable_references():
    """Test finding variable references in strings."""
    validator = TemplateValidator()
    value = "Hello ${name} at {{variables.domain}}"
    refs = validator.find_variable_references(value)
    assert "name" in refs
    assert "domain" in refs


@pytest.mark.parametrize(
    "hostname,valid",
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
def test_is_valid_hostname(hostname: str, valid: bool):
    """Test hostname validation."""
    validator = TemplateValidator()
    assert validator.is_valid_hostname(hostname) == valid
