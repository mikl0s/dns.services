import os
import pytest
from unittest.mock import patch
from pathlib import Path
from click.testing import CliRunner
from dns_services_gateway.templates.cli import template
from dns_services_gateway.templates.core.loader import TemplateLoader
from dns_services_gateway.templates.variables.manager import VariableManager
import yaml


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def example_template(tmp_path):
    template_file = tmp_path / "example.yaml"
    template_content = """
metadata:
  name: example
  description: Example DNS template
  version: 1.0.0
  author: Test User

variables:
  domain: example.com
  ttl: 3600
  _descriptions:
    domain: Domain name
    ttl: Default TTL
  custom_vars:
    ip:
      value: 192.168.1.1
      description: IP address
    nameservers:
      value:
        - ns1.example.com
        - ns2.example.com
      description: List of nameservers

environments:
  production:
    variables:
      ip:
        value: 203.0.113.1
        description: Production IP address
  staging:
    variables:
      ip:
        value: 198.51.100.1
        description: Staging IP address

records:
  A:
    - name: "@"
      type: A
      ttl: 3600
      value: "${ip}"
  CNAME:
    - name: www
      type: CNAME
      ttl: 3600
      value: "${domain}"

settings:
  backup:
    enabled: true
    directory: backups
    retention_days: 30
  rollback:
    enabled: true
    max_changes: 10
  change_management:
    enabled: true
    changes_dir: changes
    require_approval: true
"""
    template_file.write_text(template_content)
    return template_file


@pytest.fixture
def other_template(tmp_path):
    template_file = tmp_path / "other.yaml"
    template_content = """
metadata:
  name: other
  description: Other DNS template
  version: 1.0.0
  author: Test User

variables:
  domain: other.com
  ttl: 3600
  _descriptions:
    domain: Domain name
    ttl: Default TTL
  custom_vars:
    ip:
      value: 192.168.1.2
      description: IP address
    nameservers:
      value:
        - ns1.other.com
        - ns2.other.com
      description: List of nameservers

records:
  A:
    - name: "@"
      type: A
      ttl: 3600
      value: "${ip}"

settings:
  backup:
    enabled: true
    directory: backups
    retention_days: 30
  rollback:
    enabled: true
    max_changes: 10
  change_management:
    enabled: true
    changes_dir: changes
    require_approval: true
"""
    template_file.write_text(template_content)
    return template_file


def test_template_list(runner, example_template):
    os.environ["DNS_SERVICES_TEMPLATE_DIR"] = str(example_template.parent)
    result = runner.invoke(template, ["list"])
    print(f"Output: {result.output}")
    print(f"Exception: {result.exception}")
    assert result.exit_code == 0


@patch("dns_services_gateway.templates.environments.manager.EnvironmentManager")
@patch("dns_services_gateway.templates.records.manager.RecordManager")
def test_template_apply(
    mock_record_manager, mock_env_manager, runner, example_template
):
    # Create mock instances
    mock_env_instance = mock_env_manager.return_value
    mock_record_instance = mock_record_manager.return_value

    # Mock the calculate_changes method to return some changes
    mock_env_instance.calculate_changes.return_value = ([], [])  # (changes, errors)

    # Mock the add_environment method to return no errors
    mock_env_instance.add_environment.return_value = []

    # Mock the apply_changes method to return success
    mock_env_instance.apply_changes.return_value = (True, [])  # (success, errors)

    # Mock record manager methods
    mock_record_instance.add_record.return_value = []  # No errors
    mock_record_instance.validate_record.return_value = []  # No validation errors

    result = runner.invoke(
        template,
        [
            "apply",
            str(example_template),
            "example.com",
            "--env",
            "production",
            "--force",
            "--mode",
            "force",
        ],
    )
    print(f"Output: {result.output}")
    print(f"Exception: {result.exception}")
    assert result.exit_code == 0

    # Verify record manager was called
    mock_record_instance.add_record.assert_called()


def test_template_validate(runner, example_template):
    result = runner.invoke(template, ["validate", str(example_template)])
    print(f"Output: {result.output}")
    print(f"Exception: {result.exception}")
    assert result.exit_code == 0


def test_template_export(runner, example_template):
    result = runner.invoke(template, ["export", str(example_template)])
    print(f"Output: {result.output}")
    print(f"Exception: {result.exception}")
    assert result.exit_code == 0


def test_template_backup(runner, example_template):
    result = runner.invoke(template, ["backup", str(example_template)])
    print(f"Output: {result.output}")
    print(f"Exception: {result.exception}")
    assert result.exit_code == 0


def test_template_restore(runner, example_template):
    # First create a backup
    runner.invoke(template, ["backup", str(example_template)])
    result = runner.invoke(template, ["restore", str(example_template)])
    print(f"Output: {result.output}")
    print(f"Exception: {result.exception}")
    assert result.exit_code == 0


def test_template_diff(runner, example_template, other_template):
    result = runner.invoke(
        template, ["diff", str(example_template), str(other_template)]
    )
    print(f"Output: {result.output}")
    print(f"Exception: {result.exception}")
    assert result.exit_code == 0


def test_template_show(runner, example_template):
    result = runner.invoke(template, ["show", str(example_template)])
    print(f"Output: {result.output}")
    print(f"Exception: {result.exception}")
    assert result.exit_code == 0


def test_template_init(runner, tmp_path):
    new_template = tmp_path / "new_template.yaml"
    result = runner.invoke(template, ["init", str(new_template)])
    print(f"Output: {result.output}")
    print(f"Exception: {result.exception}")
    assert result.exit_code == 0


def test_template_list_variables(runner, example_template):
    # First set up a variable with proper structure
    result = runner.invoke(
        template,
        [
            "set-variable",
            str(example_template),
            "test_var=test_value",
            "--description",
            "Test variable",
        ],
    )
    assert result.exit_code == 0

    # Now list the variables
    result = runner.invoke(template, ["list-variables", str(example_template)])
    print(f"Output: {result.output}")
    print(f"Exception: {result.exception}")
    assert result.exit_code == 0
    assert "test_var" in result.output
    assert "test_value" in result.output


def test_template_set_variable(runner, example_template):
    result = runner.invoke(
        template, ["set-variable", str(example_template), "test_var=test_value"]
    )
    print(f"Output: {result.output}")
    print(f"Exception: {result.exception}")
    assert result.exit_code == 0

    # Load template to verify
    with open(example_template) as f:
        template_data = yaml.safe_load(f)
    assert (
        template_data["variables"]["custom_vars"]["test_var"]["value"] == "test_value"
    )
    assert template_data["variables"]["custom_vars"]["test_var"]["description"] == ""

    # Test setting a built-in variable
    result = runner.invoke(
        template, ["set-variable", str(example_template), "domain=test.com"]
    )
    assert result.exit_code == 0

    # Verify built-in variable
    with open(example_template) as f:
        template_data = yaml.safe_load(f)
    assert template_data["variables"]["domain"] == "test.com"


def test_template_get_variable(runner, example_template):
    # First set a variable
    result = runner.invoke(
        template, ["set-variable", str(example_template), "test_var=test_value"]
    )
    assert result.exit_code == 0

    # Then get it
    result = runner.invoke(
        template, ["get-variable", str(example_template), "test_var"]
    )
    print(f"Output: {result.output}")
    print(f"Exception: {result.exception}")
    assert result.exit_code == 0
    assert "test_var=test_value" in result.output


def test_template_remove_variable(runner, example_template):
    # First set a variable
    runner.invoke(
        template, ["set-variable", str(example_template), "test_var=test_value"]
    )
    result = runner.invoke(
        template, ["remove-variable", str(example_template), "test_var"]
    )
    print(f"Output: {result.output}")
    print(f"Exception: {result.exception}")
    assert result.exit_code == 0
    # Verify the variable was removed
    loader = TemplateLoader(Path(example_template))
    template_data = loader.load()
    assert "test_var" not in template_data.variables
