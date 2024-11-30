"""Environment configuration management for DNS templates."""
import os
from typing import Dict, Optional, Union
from pydantic import BaseModel, Field

from ..models.base import EnvironmentModel


class EnvironmentConfig(BaseModel):
    """Environment configuration settings."""

    name: str = Field(..., description="Environment name")
    description: Optional[str] = Field(None, description="Environment description")
    variables: Dict[str, Union[str, int]] = Field(
        default_factory=dict, description="Environment-specific variables"
    )


class EnvironmentConfigHandler:
    """Handles environment configuration and detection."""

    def __init__(self):
        """Initialize environment config handler."""
        self.configs: Dict[str, EnvironmentConfig] = {}
        self._current_env: Optional[str] = None

    def add_config(self, config: EnvironmentConfig) -> None:
        """Add an environment configuration.

        Args:
            config: Environment configuration to add
        """
        self.configs[config.name] = config

    def get_config(self, name: str) -> Optional[EnvironmentConfig]:
        """Get an environment configuration.

        Args:
            name: Environment name

        Returns:
            EnvironmentConfig if found, None otherwise
        """
        return self.configs.get(name)

    def detect_environment(self) -> str:
        """Detect current environment.

        Returns:
            Detected environment name
        """
        if self._current_env:
            return self._current_env

        # Check environment variable
        env = os.getenv("DNS_SERVICES_ENV")
        if env and env in self.configs:
            self._current_env = env
            return env

        # Check hostname-based detection
        hostname = os.uname().nodename.lower()
        if "prod" in hostname:
            return "production"
        if "staging" in hostname:
            return "staging"
        if "dev" in hostname:
            return "development"

        # Default to development
        return "development"

    def set_environment(self, name: str) -> None:
        """Set current environment.

        Args:
            name: Environment name to set

        Raises:
            ValueError: If environment doesn't exist
        """
        if name not in self.configs:
            raise ValueError(f"Environment '{name}' not found")
        self._current_env = name

    def get_current_config(self) -> EnvironmentConfig:
        """Get current environment configuration.

        Returns:
            Current environment configuration

        Raises:
            ValueError: If no environment is set
        """
        env = self.detect_environment()
        return self.configs[env]

    def apply_environment_config(
        self, environment: EnvironmentModel, base_variables: Dict[str, Union[str, int]]
    ) -> EnvironmentModel:
        """Apply environment configuration to environment model.

        Args:
            environment: Environment model to update
            base_variables: Base template variables

        Returns:
            Updated environment model
        """
        config = self.configs.get(environment.name)
        if not config:
            return environment

        # Start with base variables
        final_variables: Dict[str, Union[str, int]] = base_variables.copy()

        # Override with environment-specific variables
        if environment.variables:
            final_variables.update(environment.variables)
        if config.variables:
            final_variables.update(config.variables)

        # Create new environment with merged variables
        return EnvironmentModel(name=environment.name, variables=final_variables)
