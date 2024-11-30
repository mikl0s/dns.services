"""Template management CLI commands."""

import os
from pathlib import Path
import sys
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from .core.loader import TemplateLoader
from .core.validator import TemplateValidator
from .environments.config import EnvironmentConfigHandler
from .environments.manager import EnvironmentManager
from .safety.backup import BackupManager
from .safety.rollback import RollbackManager
from .safety.change_management import ChangeManager

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
def validate(template_file: str):
    """Validate a template file."""
    try:
        loader = TemplateLoader(template_file)
        template_data = loader.load()

        validator = TemplateValidator()
        errors = validator.validate_template(
            template_data["variables"],
            template_data["environments"],
            template_data["records"],
        )

        if errors:
            table = Table(title="Template Validation Errors")
            table.add_column("Error")
            for error in errors:
                table.add_row(error)
            console.print(table)
            sys.exit(1)
        else:
            click.echo("Template validation successful!")

    except Exception as e:
        click.echo(f"Validation failed: {str(e)}", err=True)
        sys.exit(1)


@template.command()
@click.argument("template_file")
@click.option("--domain", "-d", required=True, help="Domain to apply template to")
@click.option("--env", "-e", default="production", help="Environment to use")
@click.option("--dry-run", is_flag=True, help="Perform dry run without making changes")
@click.option("--force", "-f", is_flag=True, help="Skip approval process")
@click.option(
    "--mode",
    "-m",
    type=click.Choice(["force", "create-missing", "update-existing"]),
    default="force",
    help=(
        "Application mode: force (update/create all), create-missing (only create new "
        "records), update-existing (only update existing records)"
    ),
)
def apply(
    template_file: str, domain: str, env: str, dry_run: bool, force: bool, mode: str
):
    """Apply a template to a domain.

    Modes:
    - force: Create new records and update existing ones (default)
    - create-missing: Only create records that don't exist
    - update-existing: Only update records that already exist
    """
    try:
        # Load template
        loader = TemplateLoader(template_file)
        template_data = loader.load()

        # Set up environment
        env_config = EnvironmentConfigHandler()
        env_manager = EnvironmentManager(
            template_data["variables"], template_data["records"]
        )

        # Get environment configuration
        environment = loader.get_environment(template_data, env)
        if not environment:
            click.echo(f"Environment {env} not found in template", err=True)
            sys.exit(1)

        # Apply environment config
        environment = env_config.apply_environment_config(
            environment, template_data["variables"]
        )

        # Set up safety systems
        backup_manager = BackupManager(
            str(get_template_dir() / "backups"), template_data["settings"]["backup"]
        )

        rollback_manager = RollbackManager(str(get_template_dir() / "rollbacks"))

        # Initialize change manager but don't use it yet - will be used in future PR
        _ = ChangeManager(
            str(get_template_dir() / "changes"),
            template_data["settings"]["change_management"],
        )

        # Create backup
        if not dry_run:
            backup_manager.create_backup(domain, [], env)

        # Calculate changes
        changes, errors = env_manager.calculate_changes(env)
        if errors:
            click.echo("Failed to calculate changes:", err=True)
            for error in errors:
                click.echo(f"  {error}", err=True)
            sys.exit(1)

        if not changes:
            click.echo("No changes required")
            return

        # Show changes
        table = Table(title="Proposed Changes")
        table.add_column("Type")
        table.add_column("Record")
        table.add_column("Value")
        table.add_column("TTL")

        for change in changes:
            table.add_row(
                change.type.value,
                change.record.name,
                change.record.value,
                str(getattr(change.record, "ttl", "") or ""),
            )

        console.print(table)

        if dry_run:
            return

        # Get approval if required
        if (
            not force
            and template_data["settings"]["change_management"]["require_approval"]
        ):
            if not click.confirm("Do you want to apply these changes?"):
                click.echo("Changes cancelled")
                return

        # Apply changes
        try:
            success, errors = env_manager.apply_changes(env, changes)
            if not success:
                click.echo("Failed to apply changes:", err=True)
                for error in errors:
                    click.echo(f"  {error}", err=True)
                if template_data["settings"]["rollback"]["automatic"]:
                    click.echo("Rolling back changes...")
                    rollback_manager.rollback_change(changes[0].id)
                sys.exit(1)
            click.echo("Changes applied successfully")
        except Exception as e:
            click.echo(f"Failed to apply changes: {str(e)}", err=True)
            if template_data["settings"]["rollback"]["automatic"]:
                click.echo("Rolling back changes...")
                rollback_manager.rollback_change(changes[0].id)
            sys.exit(1)

    except Exception as e:
        click.echo(f"Failed to apply template: {str(e)}", err=True)
        sys.exit(1)


@template.group()
def changes():
    """Manage DNS changes."""
    pass
