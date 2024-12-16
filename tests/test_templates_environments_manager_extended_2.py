"""Extended tests for environment manager."""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, List

from dns_services_gateway.templates.models.base import (
    EnvironmentModel,
    VariableModel,
    RecordModel,
    SingleVariableModel,
)
from dns_services_gateway.templates.environments.manager import EnvironmentManager
from dns_services_gateway.exceptions import ValidationError


@pytest.fixture
def env_manager():
    """Create an EnvironmentManager instance for testing."""
    base_variables = VariableModel(
        domain="example.com",
        ttl=3600,
        custom_vars={
            "domain": {"value": "example.com", "description": "Domain name"},
            "ttl": {"value": "3600", "description": "Default TTL"},
        },
    )
    base_records = {
        "A": [{"type": "A", "name": "www", "value": "192.0.2.1", "ttl": 3600}],
        "CNAME": [
            {"type": "CNAME", "name": "www2", "value": "www.example.com", "ttl": 3600}
        ],
    }
    return EnvironmentManager(base_variables, base_records)


@pytest.fixture
def sample_env():
    """Create a sample environment configuration."""
    return EnvironmentModel(
        name="staging",
        variables={
            "domain": SingleVariableModel(
                name="domain", value="staging.example.com", description="Domain name"
            ),
            "ttl": SingleVariableModel(
                name="ttl", value="1800", description="TTL override"
            ),
            "api_endpoint": SingleVariableModel(
                name="api_endpoint",
                value="api.staging.example.com",
                description="API endpoint",
            ),
        },
        records={
            "A": [{"type": "A", "name": "api", "value": "192.0.2.1", "ttl": 1800}]
        },
    )


def test_create_environment(env_manager, sample_env):
    """Test creating a new environment."""
    result = env_manager.add_environment(sample_env)
    assert result == []  # No validation errors
    env = env_manager.get_environment("staging")
    assert env.name == "staging"
    assert env.variables["api_endpoint"].value == "api.staging.example.com"
    assert env.variables["ttl"].value == "1800"
    assert len(env.records["A"]) == 1
    assert env.records["A"][0]["value"] == "192.0.2.1"


def test_create_duplicate_environment(env_manager, sample_env):
    """Test creating a duplicate environment."""
    env_manager.add_environment(sample_env)
    result = env_manager.add_environment(sample_env)
    assert "Environment staging already exists" in result[0]


def test_get_environment(env_manager, sample_env):
    """Test getting an environment."""
    env_manager.add_environment(sample_env)
    result = env_manager.get_environment("staging")
    assert isinstance(result, EnvironmentModel)
    assert result.name == "staging"
    assert result.variables["api_endpoint"].value == "api.staging.example.com"


def test_get_nonexistent_environment(env_manager):
    """Test getting a non-existent environment."""
    result = env_manager.get_environment("nonexistent")
    assert result is None


def test_update_environment(env_manager, sample_env):
    """Test updating an environment."""
    env_manager.add_environment(sample_env)

    updated_vars = {
        "domain": SingleVariableModel(
            name="domain", value="staging.example.com", description="Domain name"
        ),
        "ttl": SingleVariableModel(
            name="ttl", value="900", description="Updated TTL override"
        ),
        "api_endpoint": SingleVariableModel(
            name="api_endpoint",
            value="api.v2.staging.example.com",
            description="Updated API endpoint",
        ),
    }

    result = env_manager.update_environment("staging", updated_vars)
    assert isinstance(result, EnvironmentModel)
    assert result.variables["api_endpoint"].value == "api.v2.staging.example.com"
    assert result.variables["ttl"].value == "900"
    assert result.records["A"][0]["value"] == "192.0.2.1"


def test_delete_environment(env_manager, sample_env):
    """Test deleting an environment."""
    env_manager.add_environment(sample_env)
    env_manager.delete_environment("staging")
    assert env_manager.get_environment("staging") is None


def test_list_environments(env_manager, sample_env):
    """Test listing all environments."""
    env_manager.add_environment(sample_env)

    prod_env = EnvironmentModel(
        name="production",
        variables={
            "domain": SingleVariableModel(
                name="domain", value="example.com", description="Domain name"
            ),
            "ttl": SingleVariableModel(
                name="ttl", value="7200", description="Production TTL"
            ),
            "api_endpoint": SingleVariableModel(
                name="api_endpoint",
                value="api.example.com",
                description="Production API endpoint",
            ),
        },
        records={
            "A": [{"type": "A", "name": "api", "value": "192.0.2.3", "ttl": 7200}]
        },
    )
    env_manager.add_environment(prod_env)

    envs = env_manager.list_environments()
    assert len(envs) == 2
    assert "staging" in envs
    assert "production" in envs
    assert envs["staging"].variables["api_endpoint"].value == "api.staging.example.com"
    assert envs["production"].variables["api_endpoint"].value == "api.example.com"
