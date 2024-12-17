import pytest
from dns_services_gateway.templates.environments.manager import EnvironmentManager
from dns_services_gateway.templates.models.base import (
    EnvironmentModel,
    RecordModel,
    VariableModel,
)


@pytest.fixture
def environment_manager():
    # Create base variables as a VariableModel
    base_variables = VariableModel(
        domain="example.com",
        ttl=3600,
        custom_vars={
            "domain": {"value": "example.com", "description": "Domain name"},
            "ttl": {"value": "3600", "description": "Default TTL"},
            "env": {"value": "base", "description": "Environment name"},
        },
    )

    # Create base records
    record = RecordModel(type="A", name="www", value="192.168.1.1", ttl=3600)
    base_records = {"A": [record.model_dump()]}

    manager = EnvironmentManager(base_variables, base_records)

    # Create production environment with required variables
    prod_record = RecordModel(type="A", name="www", value="10.0.0.1", ttl=3600)
    prod_env = EnvironmentModel(
        name="production",
        variables={
            "domain": {"value": "example.com", "description": "Domain name"},
            "ttl": {"value": "3600", "description": "Default TTL"},
            "env": {"value": "prod", "description": "Production environment"},
        },
        records={"A": [prod_record.model_dump()]},
    )
    errors = manager.add_environment(prod_env)
    if errors:
        raise ValueError(f"Failed to add production environment: {errors}")
    return manager


def test_get_environment(environment_manager):
    env = environment_manager.get_environment("production")
    assert env.name == "production"
    assert env.variables["env"].value == "prod"


def test_list_environments(environment_manager):
    envs = environment_manager.list_environments()
    assert len(envs) == 1
    assert "production" in envs


def test_create_environment(environment_manager):
    env = environment_manager.create_environment(
        "development",
        variables={
            "domain": {"value": "example.com", "description": "Domain name"},
            "ttl": {"value": "3600", "description": "Default TTL"},
            "env": {"value": "dev", "description": "Development environment"},
        },
    )
    assert env.name == "development"
    assert env.variables["env"].value == "dev"


def test_update_environment(environment_manager):
    env = environment_manager.update_environment(
        "production",
        variables={
            "domain": {"value": "example.com", "description": "Domain name"},
            "ttl": {"value": "3600", "description": "Default TTL"},
            "env": {
                "value": "new-prod",
                "description": "Updated production environment",
            },
        },
    )
    assert env.variables["env"].value == "new-prod"


def test_delete_environment(environment_manager):
    environment_manager.delete_environment("production")
    assert "production" not in environment_manager.list_environments()


def test_get_environment_variables(environment_manager):
    variables = environment_manager.get_environment_variables("production")
    assert variables["env"].value == "prod"


def test_set_environment_variable(environment_manager):
    environment_manager.set_environment_variable(
        "production",
        {
            "name": "api_key",
            "value": "secret",
            "description": "API key",
        },
    )
    variables = environment_manager.get_environment_variables("production")
    assert variables["api_key"].value == "secret"


def test_remove_environment_variable(environment_manager):
    environment_manager.set_environment_variable(
        "production",
        VariableModel(
            domain="example.com",
            ttl=3600,
            name="temp",
            value="value",
            description="Temporary variable",
        ),
    )
    environment_manager.remove_environment_variable("production", "temp")
    variables = environment_manager.get_environment_variables("production")
    assert "temp" not in variables


def test_clone_environment(environment_manager):
    env = environment_manager.clone_environment("production", "prod-clone")
    assert env.name == "prod-clone"
    assert (
        env.variables["env"].value
        == environment_manager.get_environment("production").variables["env"].value
    )


def test_merge_environments(environment_manager):
    environment_manager.set_environment_variable(
        "production",
        {
            "name": "api_url",
            "value": "prod-api",
            "description": "API URL",
        },
    )
    merged = environment_manager.merge_environments(["production"])
    assert merged["api_url"].value == "prod-api"


def test_validate_environment(environment_manager):
    errors = environment_manager.validate_environment("production")
    assert len(errors) == 0


async def test_apply_environment(environment_manager):
    # Calculate changes first
    changes, errors = await environment_manager.calculate_changes("production")
    assert not errors, f"Unexpected errors during change calculation: {errors}"

    # Apply the changes
    success, errors = await environment_manager.apply_changes(changes)
    assert success, f"Failed to apply changes: {errors}"
    assert not errors, f"Unexpected errors during apply: {errors}"


def test_export_environment(environment_manager):
    exported = environment_manager.export_environment("production")
    assert exported["name"] == "production"
    assert "variables" in exported


def test_import_environment(environment_manager):
    env_data = {
        "name": "imported",
        "variables": {
            "domain": {
                "value": "imported.example.com",
                "description": "Imported domain",
            },
            "ttl": {"value": "3600", "description": "Default TTL"},
        },
    }
    env = environment_manager.import_environment(env_data)
    assert env.name == "imported"
    assert env.variables["domain"].value == "imported.example.com"
