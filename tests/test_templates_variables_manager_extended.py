"""Extended tests for variables manager."""

import pytest
from dns_services_gateway.templates.models.base import (
    SingleVariableModel,
    VariableModel,
)
from dns_services_gateway.templates.variables.manager import VariableManager
from dns_services_gateway.exceptions import ValidationError


@pytest.fixture
def var_manager():
    """Create a VariableManager instance for testing."""
    manager = VariableManager({"domain": "example.com", "ttl": 3600})

    # Add initial variables
    manager.set_variable(
        SingleVariableModel(
            name="domain", value="example.com", description="Domain name"
        )
    )

    manager.set_variable(
        SingleVariableModel(name="ttl", value="3600", description="Default TTL")
    )

    manager.set_variable(
        SingleVariableModel(
            name="environment", value="production", description="Environment name"
        )
    )

    manager.set_variable(
        SingleVariableModel(name="region", value="us-west", description="Region name")
    )

    manager.set_variable(
        SingleVariableModel(
            name="service_port", value="8080", description="Service port"
        )
    )

    return manager


@pytest.fixture
def sample_variables():
    """Create sample variables for testing."""
    return [
        SingleVariableModel(
            name="domain", value="test.example.com", description="Test domain"
        ),
        SingleVariableModel(name="ttl", value="7200", description="Test TTL"),
        SingleVariableModel(name="api_key", value="secret123", description="API key"),
    ]


def test_variable_manager_initialization():
    # Test empty initialization
    manager = VariableManager()
    assert manager._variables["domain"] == ""
    assert manager._variables["ttl"] == 3600
    assert "custom_vars" not in manager._variables

    # Test initialization with dictionary
    manager = VariableManager(
        {
            "domain": "example.com",
            "ttl": 7200,
            "custom_vars": {
                "test": {"value": "test_value", "description": "test description"}
            },
        }
    )
    assert manager._variables["domain"] == "example.com"
    assert manager._variables["ttl"] == 7200
    assert manager._variables["custom_vars"]["test"]["value"] == "test_value"

    # Test initialization with VariableModel
    model = VariableModel(
        domain="test.com",
        ttl=1800,
        custom_vars={"foo": {"value": "bar", "description": "test var"}},
    )
    manager = VariableManager(model)
    assert manager._variables["domain"] == "test.com"
    assert manager._variables["ttl"] == 1800
    assert manager._variables["custom_vars"]["foo"]["value"] == "bar"


def test_set_get_variable():
    manager = VariableManager({"domain": "example.com", "ttl": 3600})

    # Test setting variable with SingleVariableModel
    var = SingleVariableModel(
        name="test", value="test_value", description="test description"
    )
    manager.set_variable(var)

    # Test getting variable
    retrieved = manager.get_variable("test")
    assert retrieved is not None
    assert retrieved.name == "test"
    assert retrieved.value == "test_value"
    assert retrieved.description == "test description"

    # Test setting variable with dictionary
    manager.set_variable(
        {
            "name": "another",
            "value": "another_value",
            "description": "another description",
        }
    )

    retrieved = manager.get_variable("another")
    assert retrieved is not None
    assert retrieved.name == "another"
    assert retrieved.value == "another_value"
    assert retrieved.description == "another description"


def test_delete_variable():
    manager = VariableManager({"domain": "example.com", "ttl": 3600})

    var = SingleVariableModel(name="test", value="test_value")
    manager.set_variable(var)
    assert manager.get_variable("test") is not None

    manager.delete_variable("test")
    assert manager.get_variable("test") is None


def test_get_all_variables():
    manager = VariableManager({"domain": "example.com", "ttl": 3600})

    # Add some variables
    vars = [
        SingleVariableModel(name="var1", value="value1"),
        SingleVariableModel(name="var2", value="value2", description="desc2"),
        SingleVariableModel(name="var3", value="value3"),
    ]

    for var in vars:
        manager.set_variable(var)

    # Get all variables
    all_vars = manager.get_all_variables()
    assert len(all_vars) == 5  # domain, ttl, and 3 custom variables

    # Check that each variable is present with correct values
    var_dict = {var.name: var for var in all_vars}
    assert "var1" in var_dict
    assert var_dict["var1"].value == "value1"
    assert var_dict["var1"].description == ""

    assert "var2" in var_dict
    assert var_dict["var2"].value == "value2"
    assert var_dict["var2"].description == "desc2"

    assert "var3" in var_dict
    assert var_dict["var3"].value == "value3"
    assert var_dict["var3"].description == ""

    # Check base variables
    assert "domain" in var_dict
    assert var_dict["domain"].value == "example.com"
    assert var_dict["domain"].description == "Domain name"

    assert "ttl" in var_dict
    assert var_dict["ttl"].value == 3600
    assert var_dict["ttl"].description == "Default TTL"


def test_update_variables():
    manager = VariableManager()

    # Update with dictionary
    manager.update(
        {
            "domain": "example.com",
            "ttl": 3600,
            "custom_vars": {
                "test": {"value": "test_value", "description": "test description"}
            },
        }
    )

    assert manager._variables["domain"] == "example.com"
    assert manager._variables["ttl"] == 3600
    assert manager.get_variable("test") is not None

    # Update with VariableModel
    new_model = VariableModel(
        domain="new.com", ttl=7200, custom_vars={"another": {"value": "another_value"}}
    )
    manager.update(new_model)

    assert manager._variables["domain"] == "new.com"
    assert manager._variables["ttl"] == 7200
    assert manager.get_variable("another") is not None
    assert manager.get_variable("test") is None  # Old variable should be gone


def test_variable_resolution():
    manager = VariableManager({"domain": "example.com", "ttl": 3600})

    manager.set_variable(SingleVariableModel(name="host", value="web"))

    manager.set_variable(SingleVariableModel(name="fqdn", value="${host}.example.com"))

    # Test simple variable resolution
    text = "Server at ${host}"
    resolved = manager.resolve_nested_variables(text)
    assert resolved == "Server at web"

    # Test nested variable resolution
    text = "FQDN: ${fqdn}"
    resolved = manager.resolve_nested_variables(text)
    assert resolved == "FQDN: web.example.com"


def test_resolve_nonexistent_variable():
    manager = VariableManager({"domain": "example.com", "ttl": 3600})

    # Test resolving non-existent variable
    text = "Missing: ${nonexistent}"
    resolved = manager.resolve_nested_variables(text)
    assert (
        resolved == "Missing: ${nonexistent}"
    )  # Should leave unresolved variable as is


def test_clear_variables():
    manager = VariableManager({"domain": "example.com", "ttl": 3600})

    manager.set_variable(SingleVariableModel(name="test", value="test_value"))
    assert manager.get_variable("test") is not None

    manager.clear_variables()
    all_vars = manager.get_all_variables()
    assert len(all_vars) == 2  # Only domain and ttl should remain
    assert all(var.name in ["domain", "ttl"] for var in all_vars)
