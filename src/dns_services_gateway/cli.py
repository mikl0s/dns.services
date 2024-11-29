"""Command-line interface for DNS Services Gateway."""

import sys
import click
from typing import Optional
from .auth import TokenManager
from .exceptions import AuthenticationError, TokenError
from .config import DNSServicesConfig


@click.group()
def cli():
    """DNS Services Gateway CLI."""
    pass


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
    """Download and save authentication token."""
    config = DNSServicesConfig.from_env()
    token_manager = TokenManager(config=config)
    try:
        token_manager.download_token(
            username=username,
            output_path=output,
            password=password,
        )
        click.echo("Token downloaded successfully")
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
    """Verify token file exists and is valid."""
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
