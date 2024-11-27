"""Configuration management for DNS Services Gateway."""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, SecretStr
from dotenv import load_dotenv

from .exceptions import ConfigurationError


class DNSServicesConfig(BaseModel):
    """Configuration for DNS Services Gateway."""

    username: str = Field(..., description="DNS.services account username")
    password: SecretStr = Field(..., description="DNS.services account password")
    base_url: str = Field(
        "https://dns.services",
        description="DNS.services API base URL",
    )
    token_path: Optional[Path] = Field(
        None,
        description="Path to store JWT token",
    )
    verify_ssl: bool = Field(
        True,
        description="Whether to verify SSL certificates",
    )
    timeout: int = Field(
        30,
        description="API request timeout in seconds",
        ge=1,
        le=300,
    )
    debug: bool = Field(
        False,
        description="Enable debug logging",
    )

    @classmethod
    def from_env(cls, env_file: Optional[str] = None) -> "DNSServicesConfig":
        """Create configuration from environment variables.

        Args:
            env_file: Path to .env file (optional)

        Returns:
            DNSServicesConfig: Configuration instance

        Raises:
            ConfigurationError: If required environment variables are missing
        """
        if env_file:
            if not os.path.exists(env_file):
                raise ConfigurationError(f"Environment file not found: {env_file}")
            load_dotenv(env_file)

        try:
            return cls(
                username=os.getenv("DNS_SERVICES_USERNAME", ""),
                password=SecretStr(os.getenv("DNS_SERVICES_PASSWORD", "")),
                base_url=os.getenv("DNS_SERVICES_BASE_URL", "https://dns.services"),
                token_path=os.getenv("DNS_SERVICES_TOKEN_PATH"),
                verify_ssl=os.getenv("DNS_SERVICES_VERIFY_SSL", "true").lower() == "true",
                timeout=int(os.getenv("DNS_SERVICES_TIMEOUT", "30")),
                debug=os.getenv("DNS_SERVICES_DEBUG", "false").lower() == "true",
            )
        except ValueError as e:
            raise ConfigurationError(f"Invalid configuration: {str(e)}")

    def get_token_path(self) -> Optional[Path]:
        """Get the absolute path for token storage.

        Returns:
            Optional[Path]: Absolute path to token file or None if not configured
        """
        if not self.token_path:
            return None

        path = self.token_path.expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
