"""Template loader for managing DNS configuration templates."""

import os
from pathlib import Path
from typing import Any, Dict, Optional, Union
import yaml  # type: ignore

from ..models.base import MetadataModel, VariableModel, RecordModel, EnvironmentModel
from ..models.settings import BackupSettings, RollbackSettings, ChangeManagementSettings
from ..variables.manager import VariableManager


class Template:
    """Template class representing a DNS template."""

    def __init__(self, data: Dict[str, Any]):
        """Initialize template.

        Args:
            data: Template data
        """
        self._data = data
        self.metadata = (
            MetadataModel(**data.get("metadata", {})) if "metadata" in data else None
        )
        self.variables = VariableManager(data.get("variables", {}))

        # Initialize environments with proper models
        self.environments = {}
        for env_name, env_data in data.get("environments", {}).items():
            if isinstance(env_data, dict):
                env_dict = dict(env_data)
                env_dict["name"] = env_name  # Set name before creating model
                env_dict["variables"] = env_dict.get("variables", {})
                self.environments[env_name] = EnvironmentModel.from_dict(env_dict)
            else:
                # If env_data is already a model instance
                self.environments[env_name] = env_data

        # Initialize records
        self.records = {}
        for record_type, records in data.get("records", {}).items():
            self.records[record_type] = []
            for record_data in records:
                record_data = dict(
                    record_data
                )  # Make a copy to avoid modifying the original
                record_data["type"] = record_type  # Add the type field
                if "ttl" not in record_data:
                    # Use default TTL from variables if available
                    variables = self.variables.get_variables()
                    if "ttl" in variables:
                        record_data["ttl"] = variables["ttl"]
                    else:
                        record_data["ttl"] = 3600  # Default TTL
                self.records[record_type].append(RecordModel(**record_data))

        # Initialize settings
        settings_data = data.get("settings", {})
        self.settings = {
            "backup": BackupSettings(**settings_data.get("backup", {})),
            "rollback": RollbackSettings(**settings_data.get("rollback", {})),
            "change_management": ChangeManagementSettings(
                **settings_data.get("change_management", {})
            ),
        }

        # Initialize record groups
        self.record_groups = data.get("record_groups", {})

    @property
    def name(self) -> str:
        """Get template name."""
        return self.metadata.name if self.metadata else ""

    @property
    def version(self) -> str:
        """Get template version."""
        return self.metadata.version if self.metadata else ""

    def model_dump(self) -> Dict[str, Any]:
        """Dump template data to dictionary."""
        records_dict = {}
        for record_type, records in self.records.items():
            records_dict[record_type] = [record.model_dump() for record in records]

        environments_dict = {}
        for env_name, env in self.environments.items():
            environments_dict[env_name] = env.model_dump()

        result = {
            "variables": self.variables.get_variables(),
            "environments": environments_dict,
            "records": records_dict,
            "settings": {
                "backup": self.settings["backup"].model_dump(),
                "rollback": self.settings["rollback"].model_dump(),
                "change_management": self.settings["change_management"].model_dump(),
            },
            "record_groups": self.record_groups,
        }

        if self.metadata:
            result["metadata"] = self.metadata.model_dump()

        return result

    def __getitem__(self, key: str) -> Any:
        """Get item from template data."""
        if key == "variables":
            return self.variables.get_variables()
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """Set item in template data."""
        if key == "variables":
            self.variables.update_variables(value)
        self._data[key] = value

    def __iter__(self):
        """Iterate over template data."""
        return iter(self._data)

    def get(self, key: str, default: Any = None) -> Any:
        """Get item from template data with default value."""
        if key == "variables":
            return self.variables.get_variables()
        return self._data.get(key, default)

    def items(self):
        """Get items from template data."""
        return self._data.items()

    def keys(self):
        """Get keys from template data."""
        return self._data.keys()

    def values(self):
        """Get values from template data."""
        return self._data.values()


class TemplateLoader:
    """Loads and parses DNS template files."""

    def __init__(self, template_path: Union[str, Path]):
        """Initialize template loader.

        Args:
            template_path: Path to template file
        """
        self.template_path = Path(template_path)
        self._validate_path()

    def _validate_path(self) -> None:
        """Validate template file path."""
        if not self.template_path.exists():
            raise FileNotFoundError(f"Template file not found: {self.template_path}")
        if not str(self.template_path).endswith((".yaml", ".yml")):
            raise ValueError("Template file must be a YAML file")

    def load(self) -> Template:
        """Load and parse template file.

        Returns:
            Template object containing parsed template data
        """
        with open(self.template_path, "r") as f:
            try:
                template_data = yaml.safe_load(f) or {}
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid YAML format: {str(e)}")

        return self._parse_template(template_data)

    def load_template(self, template_path: Union[str, Path]) -> Template:
        """Load template from file.

        Args:
            template_path: Path to template file

        Returns:
            Template object containing parsed template data
        """
        self.template_path = Path(template_path)
        self._validate_path()
        return self.load()

    def load_template_string(self, template_content: str) -> Template:
        """Load template from string.

        Args:
            template_content: Template content as string

        Returns:
            Template object containing parsed template data
        """
        try:
            template_data = yaml.safe_load(template_content) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format: {str(e)}")

        return self._parse_template(template_data)

    def _parse_template(self, template_data: Dict[str, Any]) -> Template:
        """Parse template data.

        Args:
            template_data: Raw template data

        Returns:
            Template object containing parsed template data
        """
        # Handle variables first
        if "variables" in template_data:
            variables = template_data["variables"]
            if not isinstance(variables, dict):
                raise ValueError("Variables must be a dictionary")
            if "custom_vars" not in variables:
                variables["custom_vars"] = {}
            template_data["variables"] = variables

        # Handle records
        if "records" in template_data:
            records = template_data["records"]
            if not isinstance(records, dict):
                raise ValueError("Records must be a dictionary")

            # Add type field to each record
            for record_type, record_list in records.items():
                if not isinstance(record_list, list):
                    raise ValueError(f"Records for type {record_type} must be a list")
                for record in record_list:
                    record["type"] = record_type
                    # If TTL is not specified, use default from variables
                    if "ttl" not in record and "variables" in template_data:
                        record["ttl"] = template_data["variables"].get("ttl", 3600)

        # Handle environments
        if "environments" in template_data:
            environments = template_data["environments"]
            if not isinstance(environments, dict):
                raise ValueError("Environments must be a dictionary")
            for env_name, env_data in environments.items():
                if not isinstance(env_data, dict):
                    raise ValueError(f"Environment {env_name} must be a dictionary")
                env_data["name"] = env_name
                # Merge base variables with environment variables
                if "variables" in env_data:
                    env_vars = env_data["variables"]
                    if not isinstance(env_vars, dict):
                        raise ValueError(
                            f"Variables for environment {env_name} must be a dictionary"
                        )
                    base_vars = template_data.get("variables", {})
                    merged_vars = {**base_vars, **env_vars}
                    env_data["variables"] = merged_vars

        return Template(template_data)

    def _parse_variables(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse template variables.

        Args:
            data: Raw template data

        Returns:
            Parsed variables dictionary
        """
        variables = data.get("variables", {})
        if not isinstance(variables, dict):
            return variables

        # Handle built-in variables
        result = {
            "domain": variables.get("domain", ""),
            "ttl": variables.get("ttl", 3600),
            "_descriptions": {
                "domain": "Domain name",
                "ttl": "Default TTL",
            },
        }

        # Handle custom variables
        if "custom_vars" in variables:
            result["custom_vars"] = variables["custom_vars"]
        else:
            # Add other variables as custom vars
            custom_vars = {}
            for name, value in variables.items():
                if name not in ["domain", "ttl", "_descriptions"]:
                    if isinstance(value, dict) and "value" in value:
                        custom_vars[name] = value
                    else:
                        custom_vars[name] = {
                            "value": value,
                            "description": "",
                        }
            if custom_vars:
                result["custom_vars"] = custom_vars

        return result

    def dump(self, data: Dict[str, Any]) -> str:
        """Dump template data to YAML string.

        Args:
            data: Template data to dump

        Returns:
            YAML string representation of template data
        """
        return yaml.dump(data, default_flow_style=False)

    def save(self, data: Dict[str, Any]) -> None:
        """Save template data to file.

        Args:
            data: Template data to save
        """
        with open(self.template_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

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
        env_data = template_data.get("environments", {}).get(environment)
        if env_data is None:
            return None

        # Create a copy of the environment data and ensure it has a name
        env_dict = dict(env_data)
        env_dict["name"] = environment
        env_dict["variables"] = env_dict.get("variables", {})

        return EnvironmentModel.from_dict(env_dict)
