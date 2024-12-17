"""Template management CLI commands."""

import os
from pathlib import Path
import sys
from typing import Optional
import re

import click
from rich.console import Console
from rich.table import Table

from .core.loader import TemplateLoader
from .core.validator import TemplateValidator
from .environments.config import EnvironmentConfigHandler
from .environments.manager import EnvironmentManager, ChangeType
from .safety.backup import BackupManager, BackupSettings
from .safety.rollback import RollbackManager
from .safety.change_management import ChangeManager, ChangeManagementSettings
from .variables.manager import VariableManager
from datetime import datetime
import yaml
import asyncio
from dns_services_gateway.templates.models.base import SingleVariableModel
import json

console = Console()


def get_template_dir() -> Path:
    """Get template directory from environment or default."""
    template_dir = os.getenv("DNS_SERVICES_TEMPLATE_DIR")
    if template_dir:
        return Path(template_dir)
    return Path.home() / ".dns-services" / "templates"


@click.group()
def template():
    """Manage DNS templates."""
    pass


@template.command()
def list():
    """List available templates."""
    template_dir = get_template_dir()
    if not template_dir.exists():
        click.echo("No templates found.")
        return

    table = Table(title="Available Templates")
    table.add_column("Name")
    table.add_column("Description")
    table.add_column("Last Modified")

    for template_file in template_dir.glob("*.yaml"):
        try:
            loader = TemplateLoader(template_file)
            template_data = loader.load()
            table.add_row(
                template_file.stem,
                template_data.get("metadata", {}).get("description", ""),
                template_file.stat().st_mtime.strftime("%Y-%m-%d %H:%M:%S"),
            )
        except Exception as e:
            click.echo(f"Error loading {template_file.name}: {str(e)}", err=True)

    console.print(table)


@template.command()
@click.argument("template_file")
def validate(template_file: str):
    """Validate a template file."""
    try:
        import asyncio

        loader = TemplateLoader(Path(template_file))
        template_data = loader.load()
        validator = TemplateValidator()
        errors = asyncio.run(
            validator.validate_template(
                variables=(
                    template_data.variables.get_variables(flatten_custom_vars=True)
                    if hasattr(template_data.variables, "get_variables")
                    else template_data.variables
                ),
                environments=template_data.environments,
                records=template_data.records,
            )
        )
        if errors:
            for error in errors:
                click.echo(f"Error: {error}", err=True)
            sys.exit(1)
        click.echo("Template is valid.")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@template.command()
@click.argument("template_file")
def export(template_file: str):
    """Export a template to standard output."""
    try:
        loader = TemplateLoader(Path(template_file))
        template_data = loader.load()
        click.echo(loader.dump(template_data))
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@template.command()
@click.argument("template_file")
def backup(template_file: str):
    """Create a backup of a template."""
    try:
        loader = TemplateLoader(Path(template_file))
        template_data = loader.load()
        backup_settings = template_data.settings.get("backup", {})
        if not backup_settings.get("enabled", False):
            click.echo("Backup is not enabled in template settings.")
            sys.exit(1)
        backup_manager = BackupManager(backup_settings)
        backup_manager.create_backup(template_data.model_dump())
        click.echo("Backup created successfully.")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@template.command()
@click.argument("template_file")
def restore(template_file: str):
    """Restore a template from backup."""
    try:
        loader = TemplateLoader(Path(template_file))
        template_data = loader.load()
        backup_settings = template_data.settings.get("backup", {})
        if not backup_settings.get("enabled", False):
            click.echo("Backup is not enabled in template settings.")
            sys.exit(1)
        backup_manager = BackupManager(backup_settings)
        restored_data = backup_manager.restore_latest()
        with open(template_file, "w") as f:
            yaml.dump(restored_data, f)
        click.echo("Template restored successfully.")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@template.command()
@click.argument("template_file")
@click.argument("other_file")
def diff(template_file: str, other_file: str):
    """Show differences between two templates."""
    try:
        loader = TemplateLoader(Path(template_file))
        template_data = loader.load()
        other_loader = TemplateLoader(Path(other_file))
        other_data = other_loader.load()

        # Get change management settings from template
        settings = template_data.settings["change_management"]
        changes_dir = Path(template_file).parent / settings.get(
            "changes_dir", "changes"
        )

        change_manager = ChangeManager(changes_dir=str(changes_dir), settings=settings)
        changes = change_manager.compare_templates(template_data, other_data)
        if changes:
            click.echo("Template differences:")
            for change in changes:
                click.echo(f"- {change}")
        else:
            click.echo("No differences found.")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@template.command()
@click.argument("template_file")
def show(template_file: str):
    """Display template contents."""
    try:
        loader = TemplateLoader(Path(template_file))
        template_data = loader.load()
        click.echo(yaml.dump(template_data.model_dump(), default_flow_style=False))
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@template.command()
@click.argument("template_file")
def init(template_file: str):
    """Initialize a new template."""
    try:
        if Path(template_file).exists():
            click.echo("Template file already exists.")
            sys.exit(1)

        template_data = {
            "metadata": {
                "name": Path(template_file).stem,
                "description": "New DNS template",
                "version": "1.0.0",
                "author": os.getenv("USER", "Unknown"),
                "created": datetime.utcnow().isoformat(),
                "updated": datetime.utcnow().isoformat(),
            },
            "variables": {
                "domain": "example.com",
                "ttl": 3600,
            },
            "environments": {
                "production": {
                    "variables": {},
                },
                "staging": {
                    "variables": {},
                },
            },
            "records": {
                "A": [
                    {
                        "name": "@",
                        "type": "A",
                        "ttl": 3600,
                        "value": "192.168.1.1",
                    }
                ],
            },
            "settings": {
                "backup": {
                    "enabled": True,
                    "directory": "backups",
                    "retention_days": 30,
                },
                "rollback": {
                    "enabled": True,
                    "max_changes": 10,
                },
                "change_management": {
                    "enabled": True,
                    "changes_dir": "changes",
                    "require_approval": True,
                },
            },
            "record_groups": {},
        }

        Path(template_file).parent.mkdir(parents=True, exist_ok=True)
        with open(template_file, "w") as f:
            yaml.dump(template_data, f, default_flow_style=False)
        click.echo("Template initialized successfully.")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@template.command()
@click.argument("name")
@click.option("--description", "-d", help="Template description")
@click.option("--author", "-a", help="Template author")
def create(name: str, description: Optional[str], author: Optional[str]):
    """Create a new template."""
    template_dir = get_template_dir()
    template_path = template_dir / f"{name}.yaml"

    if template_path.exists():
        click.echo(f"Template {name} already exists", err=True)
        sys.exit(1)

    template_content = f"""metadata:
  version: "1.0.0"
  description: "{description or f'DNS template for {name}'}"
  author: "{author or os.getenv('USER', 'Unknown')}"
  created: "{click.get_current_context().obj['timestamp']}"
  updated: "{click.get_current_context().obj['timestamp']}"
  tags: []

variables:
  domain: "example.com"
  ttl: 3600

records:
  web:
    - type: A
      name: "@"
      value: "203.0.113.10"
      ttl: ${{ttl}}
      description: "Main website"

  mail:
    - type: MX
      name: "@"
      value: "mail.${{domain}}"
      priority: 10
      ttl: ${{ttl}}
      description: "Primary mail server"

environments:
  production:
    variables:
      ttl: 3600

  staging:
    variables:
      ttl: 300
      domain: "staging.example.com"

settings:
  backup:
    enabled: true
    retention: 30

  rollback:
    enabled: true
    automatic: true

  change_management:
    require_approval: true
    notify:
      email: []
      slack: []"""

    template_dir.mkdir(parents=True, exist_ok=True)
    template_path.write_text(template_content)
    click.echo(f"Created template: {template_path}")


@template.command()
@click.argument("template_file")
@click.argument("domain")
@click.option("--env", default="default", help="Environment to apply")
@click.option("--dry-run", is_flag=True, help="Show changes without applying")
@click.option("--force", is_flag=True, help="Force apply changes")
@click.option(
    "--mode",
    type=click.Choice(["force", "create-missing", "update-existing"]),
    default="force",
    help="Apply mode",
)
def apply(
    template_file: str,
    domain: str,
    env: str,
    dry_run: bool,
    force: bool,
    mode: str,
):
    """Apply a template to a domain.

    Modes:
    - force: Create new records and update existing ones (default)
    - create-missing: Only create records that don't exist
    - update-existing: Only update records that already exist
    """
    try:
        # Load and validate template
        loader = TemplateLoader(Path(template_file))
        template_data = loader.load()

        # Initialize environment manager with variables
        variables = {}
        if template_data.variables:
            if hasattr(template_data.variables, "get_variables"):
                variables = template_data.variables.get_variables(
                    flatten_custom_vars=True
                )
            elif isinstance(template_data.variables, dict):
                base_vars = {}

                # Handle root level variables
                for key in ["domain", "ttl"]:
                    if key in template_data.variables:
                        value = template_data.variables[key]
                        description = ""
                        if isinstance(value, dict):
                            description = value.get("description", "")
                            value = value.get("value", "")
                        base_vars[key] = SingleVariableModel(
                            name=key,
                            value=str(value),
                            description=description,
                        )

                # Handle custom variables
                custom_vars = template_data.variables.get("custom_vars", {})
                for name, var in custom_vars.items():
                    if isinstance(var, dict):
                        base_vars[name] = SingleVariableModel(
                            name=name,
                            value=str(var.get("value", "")),
                            description=var.get("description", ""),
                        )
                    else:
                        base_vars[name] = SingleVariableModel(
                            name=name,
                            value=str(var),
                            description="",
                        )

                variables = base_vars
            else:
                variables = template_data.variables.model_dump()

        # Initialize environment manager
        env_manager = EnvironmentManager(
            base_variables=variables,
            base_records=template_data.records if template_data.records else {},
        )

        # Add environment to manager
        if env not in template_data.environments:
            click.echo(f"Environment {env} not found in template.")
            sys.exit(1)

        env_model = template_data.environments[env]
        errors = env_manager.add_environment(env_model)
        if errors:
            click.echo(f"Failed to add environment: {', '.join(errors)}")
            sys.exit(1)

        # Calculate changes
        changes, calc_errors = env_manager.calculate_changes(env, mode)
        if calc_errors:
            click.echo(f"Failed to calculate changes: {', '.join(calc_errors)}")
            sys.exit(1)

        # Filter changes based on mode
        if mode == "create-missing":
            changes = [c for c in changes if c.type == ChangeType.CREATE]
        elif mode == "update-existing":
            changes = [c for c in changes if c.type == ChangeType.UPDATE]

        if not changes:
            click.echo("No changes to apply.")
            return

        if dry_run:
            click.echo("Changes to be applied:")
            for change in changes:
                click.echo(
                    f"- {change.type.value}: {change.record.name} ({change.record.type})"
                )
            return

        # Apply changes
        success, apply_errors = env_manager.apply_changes(env, changes)
        if not success:
            click.echo(f"Failed to apply changes: {', '.join(apply_errors)}")
            sys.exit(1)

        click.echo("Template applied successfully.")
    except Exception as e:
        click.echo(f"Failed to apply template: {str(e)}", err=True)
        sys.exit(1)


def _validate_variable_value(key: str, value: str) -> any:
    """Validate and convert variable value based on its type.

    Args:
        key: Variable name
        value: Variable value

    Returns:
        Validated and converted value

    Raises:
        ValueError: If validation fails
    """
    if key == "ttl":
        try:
            ttl = int(value)
            if ttl <= 0:
                raise ValueError("TTL must be a positive integer")
            return ttl
        except ValueError:
            raise ValueError("TTL must be a valid integer")
    elif key == "domain":
        # Use the same validation as in validator.py
        if not re.match(
            r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$",
            value,
        ):
            raise ValueError("Invalid domain name format. Must be a valid DNS name.")
        return value
    elif key == "nameservers":
        try:
            nameservers = json.loads(value)
            if not isinstance(nameservers, list):
                raise ValueError("Nameservers must be a JSON array")
            for ns in nameservers:
                if not isinstance(ns, str):
                    raise ValueError("Each nameserver must be a string")
                # Validate nameserver hostname format
                if not re.match(
                    r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$",
                    ns,
                ):
                    raise ValueError(f"Invalid nameserver format: {ns}")
            return nameservers
        except json.JSONDecodeError:
            raise ValueError("Nameservers must be a valid JSON array")
    return value


@template.command(name="set-variable")
@click.argument("template_file")
@click.argument("key_value")
@click.option("--description", "-d", help="Description of the variable")
def set_variable(template_file: str, key_value: str, description: Optional[str] = None):
    """Set a template variable.

    Args:
        template_file: Path to the template file
        key_value: Variable in key=value format
        description: Optional description of the variable
    """
    try:
        if "=" not in key_value:
            click.echo("Invalid key-value format. Use: key=value", err=True)
            sys.exit(1)

        key, value = key_value.split("=", 1)
        key = key.strip()
        value = value.strip()

        # Validate key name
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", key):
            click.echo(
                "Invalid variable name. Use only letters, numbers, and underscores, starting with a letter or underscore",
                err=True,
            )
            sys.exit(1)

        # Load template
        try:
            loader = TemplateLoader(Path(template_file))
            template_data = loader.load()
        except Exception as e:
            click.echo(f"Failed to load template: {str(e)}", err=True)
            sys.exit(1)

        # Initialize variables if needed
        if not template_data.variables:
            template_data.variables = VariableManager()

        # Handle built-in variables and validation
        try:
            validated_value = _validate_variable_value(key, value)
            if not isinstance(template_data.variables, VariableManager):
                template_data.variables = VariableManager(template_data.variables)
            template_data.variables.set_variable(
                SingleVariableModel(
                    name=key,
                    value=validated_value,
                    description=description or "",
                )
            )
        except Exception as e:
            click.echo(f"Failed to set variable: {str(e)}", err=True)
            sys.exit(1)

        # Save template
        try:
            with open(template_file, "w") as f:
                yaml.dump(template_data.model_dump(), f, default_flow_style=False)
            click.echo(f"Variable '{key}' set successfully")
        except Exception as e:
            click.echo(f"Failed to save template: {str(e)}", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@template.command(name="get-variable")
@click.argument("template_file")
@click.argument("key")
def get_variable(template_file: str, key: str):
    """Get a template variable value."""
    try:
        # Load template
        loader = TemplateLoader(Path(template_file))
        template_data = loader.load()

        if not template_data.variables:
            click.echo(f"Variable {key} not found", err=True)
            sys.exit(1)

        if not isinstance(template_data.variables, VariableManager):
            template_data.variables = VariableManager(template_data.variables)
        variable = template_data.variables.get_variable(key)
        if variable:
            click.echo(f"{variable.name}={variable.value}")
        else:
            click.echo(f"Variable {key} not found", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@template.command(name="remove-variable")
@click.argument("template_file")
@click.argument("key")
def remove_variable(template_file: str, key: str):
    """Remove a template variable."""
    try:
        # Load template
        loader = TemplateLoader(Path(template_file))
        template_data = loader.load()

        if not template_data.variables:
            click.echo(f"Variable {key} not found", err=True)
            sys.exit(1)

        if not isinstance(template_data.variables, VariableManager):
            template_data.variables = VariableManager(template_data.variables)
        try:
            template_data.variables.remove_variable(key)

            # Save template
            with open(template_file, "w") as f:
                yaml.dump(template_data.model_dump(), f, default_flow_style=False)
            click.echo(f"Variable '{key}' removed successfully")
        except KeyError:
            click.echo(f"Variable {key} not found", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@template.command()
@click.argument("template_file")
def list_variables(template_file: str):
    """List template variables."""
    try:
        loader = TemplateLoader(Path(template_file))
        template_data = loader.load()
        if not template_data.variables:
            click.echo("No variables found.")
            return

        # Convert to VariableManager if needed
        if not isinstance(template_data.variables, VariableManager):
            template_data.variables = VariableManager(template_data.variables)

        # Get variables in a consistent format
        variables = template_data.variables.get_variables(flatten_custom_vars=True)
        if not variables:
            click.echo("No variables found.")
            return

        # Create table for display
        table = Table(title="Template Variables")
        table.add_column("Name")
        table.add_column("Value")
        table.add_column("Description")

        # Add rows for each variable
        for name, var in variables.items():
            if isinstance(var, SingleVariableModel):
                table.add_row(str(name), str(var.value), str(var.description))
            elif isinstance(var, dict):
                value = var.get("value", "")
                description = var.get("description", "")
                table.add_row(str(name), str(value), str(description))
            else:
                table.add_row(str(name), str(var), "")

        console.print(table)
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@template.group()
def changes():
    """Manage DNS changes."""
    pass
