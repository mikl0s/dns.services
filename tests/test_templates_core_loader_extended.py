import pytest
from pathlib import Path
from dns_services_gateway.templates.core.loader import TemplateLoader
from dns_services_gateway.templates.models.base import (
    MetadataModel,
    VariableModel,
    RecordModel,
    EnvironmentModel,
)


@pytest.fixture
def template_loader(tmp_path):
    template_path = tmp_path / "template.yaml"
    template_path.write_text(
        """
    metadata:
      version: 1.0.0
      description: Test template
      author: Test Author
      tags: [test]
    variables:
      domain: example.com
      ttl: 3600
    records:
      A:
        - name: www
          value: 192.0.2.1
          ttl: 3600
    """
    )
    return TemplateLoader(template_path)


def test_load_template_from_file(template_loader, tmp_path):
    template_path = tmp_path / "test_template.yaml"
    template_content = """
    metadata:
      version: 1.0.0
      description: Test template
      author: Test Author
    variables:
      domain: example.com
      ttl: 3600
    records:
      A:
        - name: "@"
          value: "192.168.1.1"
          ttl: 3600
    """
    template_path.write_text(template_content)
    template = template_loader.load_template(template_path)
    assert template.metadata.version == "1.0.0"
    assert template.metadata.description == "Test template"
    assert template.metadata.author == "Test Author"


def test_load_template_from_string(template_loader):
    template_content = """
    metadata:
      version: 1.0.0
      description: Test template from string
      author: Test Author
    variables:
      domain: example.com
      ttl: 3600
    records:
      A:
        - name: "@"
          value: "192.168.1.1"
          ttl: 3600
    """
    template = template_loader.load_template_string(template_content)
    assert template.metadata.version == "1.0.0"
    assert template.metadata.description == "Test template from string"
    assert template.metadata.author == "Test Author"


def test_load_template_with_includes(template_loader, tmp_path):
    base_template = tmp_path / "base.yaml"
    base_template.write_text(
        """
    metadata:
      version: 1.0.0
      description: Base template
      author: Test Author
    variables:
      domain: example.com
      ttl: 3600
    records:
      A:
        - name: "@"
          value: "192.168.1.1"
          ttl: 3600
    """
    )

    include_template = tmp_path / "include.yaml"
    include_template.write_text(
        """
    metadata:
      version: 1.0.0
      description: Include template
      author: Test Author
    records:
      A:
        - name: www
          value: "192.168.1.2"
          ttl: 3600
    """
    )

    template = template_loader.load_template(base_template)
    assert len(template.records.get("A", [])) == 1


def test_load_template_with_variables(template_loader, tmp_path):
    template_path = tmp_path / "template.yaml"
    template_path.write_text(
        """
    metadata:
      version: 1.0.0
      description: Template with variables
      author: Test Author
    variables:
      domain: example.com
      ttl: 3600
      custom_vars:
        custom_var:
          value: test_value
          description: Test variable
    records:
      A:
        - name: "@"
          value: "192.168.1.1"
          ttl: "{{ variables.ttl }}"
    """
    )
    template = template_loader.load_template(template_path)

    # Test non-flattened variables
    variables = template.variables.get_variables(flatten_custom_vars=False)
    assert variables["domain"] == "example.com"
    assert variables["ttl"] == 3600
    assert variables["custom_vars"]["custom_var"]["value"] == "test_value"

    # Test flattened variables
    flattened = template.variables.get_variables(flatten_custom_vars=True)
    assert flattened["domain"] == "example.com"
    assert flattened["ttl"] == 3600
    assert flattened["custom_var"] == "test_value"


def test_load_template_with_environments(template_loader, tmp_path):
    template_path = tmp_path / "template.yaml"
    template_path.write_text(
        """
    metadata:
      version: 1.0.0
      description: Template with environments
      author: Test Author
    variables:
      domain: example.com
      ttl: 3600
    environments:
      production:
        variables:
          ip: 192.168.1.1
      staging:
        variables:
          ip: 192.168.1.2
    records:
      A:
        - name: "@"
          value: "{{ variables.ip }}"
          ttl: "{{ variables.ttl }}"
    """
    )
    template = template_loader.load_template(template_path)
    assert "production" in template.environments
    assert "staging" in template.environments


def test_load_template_with_record_groups(template_loader, tmp_path):
    template_path = tmp_path / "template.yaml"
    template_content = """
    metadata:
      version: 1.0.0
      description: Template with record groups
      author: Test Author
    variables:
      domain: example.com
      ttl: 3600
    record_groups:
      web:
        - type: A
          name: "@"
          value: "192.168.1.1"
          ttl: 3600
      mail:
        - type: MX
          name: "@"
          value: "mail.example.com"
          priority: 10
          ttl: 3600
    """
    template_path.write_text(template_content)
    template = template_loader.load_template(template_path)
    assert "web" in template.record_groups
    assert "mail" in template.record_groups
