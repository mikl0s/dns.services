"""Command-line interface for DNS Services Gateway."""

import sys
from datetime import datetime, timezone
import click
from typing import Optional
from .auth import TokenManager
from .exceptions import AuthenticationError, TokenError
from .config import DNSServicesConfig
from .templates.cli import template as template_cli


@click.group()
@click.pass_context
def cli(ctx):
    """DNS Services Gateway CLI.

    This is the main entry point for the DNS Services Gateway command-line interface.
    It initializes the CLI context and sets up the current timestamp in UTC.

    Args:
        ctx: Click context object for managing CLI state
    """
    ctx.ensure_object(dict)
    ctx.obj["timestamp"] = datetime.now(timezone.utc).isoformat()


cli.add_command(template_cli)


@cli.group()
def token():
    """Manage authentication tokens."""
    pass


@token.command()
@click.option("--username", "-u", required=True, help="DNS.services username")
@click.option("--password", "-p", help="Account password (will prompt if not provided)")
@click.option(
    "--output",
    "-o",
    help="Output path for token file",
    default=lambda: DNSServicesConfig.from_env().token_path,
)
def download(username: str, password: Optional[str], output: Optional[str]) -> None:
    """Download and save authentication token.

    Authenticates with DNS.services using provided credentials and saves
    the authentication token to the specified output path.

    Args:
        username: DNS.services account username
        password: Account password (will prompt if not provided)
        output: Path where token should be saved (defaults to config path)

    Example:
        $ dns-services token download -u myuser@example.com
        $ dns-services token download -u myuser@example.com -o /custom/path/token
    """
    config = DNSServicesConfig.from_env()
    token_manager = TokenManager(config=config)
    try:
        token_path = token_manager.download_token(
            username=username,
            output_path=output,
            password=password if password else None,
        )
        click.echo(f"Token successfully saved to: {token_path}")
    except AuthenticationError as e:
        click.echo(f"Authentication failed: {str(e)}", err=True)
        sys.exit(1)
    except TokenError as e:
        click.echo(f"Token error: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {str(e)}", err=True)
        sys.exit(1)


@token.command()
@click.option(
    "--path",
    "-p",
    help="Path to token file",
    default=lambda: DNSServicesConfig.from_env().token_path,
)
def verify(path: str):
    """Verify token file exists and is valid.

    Checks if the token file exists at the specified path and validates
    its contents, including expiration status.

    Args:
        path: Path to the token file to verify

    Example:
        $ dns-services token verify
        $ dns-services token verify -p /custom/path/token
    """
    try:
        token = TokenManager.load_token(path)
        click.echo("Token verification successful!")
        if token.is_expired:
            click.echo("Warning: Token is expired", err=True)
            sys.exit(1)
    except TokenError as e:
        click.echo(f"Token verification failed: {str(e)}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
