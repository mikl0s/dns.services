"""Template loader for managing DNS configuration templates."""

import os
from typing import Any, Dict, Optional
import yaml  # type: ignore

from ..models.base import MetadataModel, VariableModel, RecordModel, EnvironmentModel
from ..models.settings import BackupSettings, RollbackSettings, ChangeManagementSettings


class TemplateLoader:
    """Loads and parses DNS template files."""

    def __init__(self, template_path: str):
        """Initialize template loader.

        Args:
            template_path: Path to template file
        """
        self.template_path = template_path
        self._validate_path()

    def _validate_path(self) -> None:
        """Validate template file path."""
        if not os.path.exists(self.template_path):
            raise FileNotFoundError(f"Template file not found: {self.template_path}")
        if not self.template_path.endswith((".yaml", ".yml")):
            raise ValueError("Template file must be a YAML file")

    def load(self) -> Dict[str, Any]:
        """Load and parse template file.

        Returns:
            Dict containing parsed template data
        """
        with open(self.template_path, "r") as f:
            try:
                template_data = yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid YAML format: {str(e)}")

        return self._parse_template(template_data)

    def _parse_template(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse template data into model instances.

        Args:
            data: Raw template data

        Returns:
            Dict containing parsed template components
        """
        # Parse metadata
        metadata = MetadataModel(**data.get("metadata", {}))

        # Parse variables
        variables = VariableModel(**data.get("variables", {}))

        # Parse records
        records = {}
        for group, record_list in data.get("records", {}).items():
            records[group] = [RecordModel(**record) for record in record_list]

        # Parse environments
        environments = {}
        for env_name, env_data in data.get("environments", {}).items():
            env_data["name"] = env_name
            environments[env_name] = EnvironmentModel(**env_data)

        # Parse settings
        settings = {
            "backup": BackupSettings(**data.get("settings", {}).get("backup", {})),
            "rollback": RollbackSettings(
                **data.get("settings", {}).get("rollback", {})
            ),
            "change_management": ChangeManagementSettings(
                **data.get("settings", {}).get("change_management", {})
            ),
        }

        return {
            "metadata": metadata,
            "variables": variables,
            "records": records,
            "environments": environments,
            "settings": settings,
        }

    @staticmethod
    def get_environment(
        template_data: Dict[str, Any], environment: str
    ) -> Optional[EnvironmentModel]:
        """Get environment-specific configuration.

        Args:
            template_data: Parsed template data
            environment: Environment name

        Returns:
            EnvironmentModel if environment exists, None otherwise
        """
        return template_data.get("environments", {}).get(environment)
