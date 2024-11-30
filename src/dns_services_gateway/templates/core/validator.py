"""Core validator for DNS template configurations."""
import re
from typing import Dict, List, Set, Any

from ..models.base import EnvironmentModel, RecordModel


class TemplateValidator:
    """Validates DNS template configurations."""

    def __init__(self):
        """Initialize template validator."""
        self.variables: Set[str] = set()
        self.environments: Dict[str, EnvironmentModel] = {}

    def validate_template(
        self,
        variables: Dict[str, Any],
        environments: Dict[str, Dict[str, Any]],
        records: Dict[str, List[Dict[str, Any]]],
    ) -> List[str]:
        """Validate template configuration.

        Args:
            variables: Template variables
            environments: Dictionary of environments
            records: Dictionary of record lists by type

        Returns:
            List of validation errors
        """
        errors: List[str] = []

        # Reset state
        self.variables = set()
        self.environments = {}

        # Validate variables
        errors.extend(self._validate_variables(variables))

        # Validate environments
        for env_name, env_data in environments.items():
            env_model = EnvironmentModel(name=env_name, **env_data)
            errors.extend(self._validate_environment(env_model))

        # Validate records
        for record_type, record_list in records.items():
            record_models = [RecordModel(**r) for r in record_list]
            errors.extend(self._validate_records(record_type, record_models))

        # Validate variable references
        errors.extend(self._validate_variable_references())

        return errors

    def _validate_variables(self, variables: Dict[str, Any]) -> List[str]:
        """Validate template variables.

        Args:
            variables: Template variables

        Returns:
            List of validation errors
        """
        errors: List[str] = []

        # Store variables for reference validation
        self.variables = set(variables.keys())

        # Check for required variables
        required = {"domain", "ttl", "nameservers"}
        missing = required - self.variables
        if missing:
            errors.append(f"Missing required variables: {', '.join(missing)}")

        return errors

    def _validate_environment(self, environment: EnvironmentModel) -> List[str]:
        """Validate environment configuration.

        Args:
            environment: Environment model

        Returns:
            List of validation errors
        """
        errors: List[str] = []

        # Check for duplicate environments
        if environment.name in self.environments:
            errors.append(f"Duplicate environment: {environment.name}")

        # Store environment for reference validation
        self.environments[environment.name] = environment

        # Validate environment variables
        if environment.variables:
            errors.extend(self._validate_environment_variables(environment))

        return errors

    def _validate_environment_variables(
        self, environment: EnvironmentModel
    ) -> List[str]:
        """Validate environment variables.

        Args:
            environment: Environment model

        Returns:
            List of validation errors
        """
        errors: List[str] = []

        # Check variable references
        for var_name, var_value in environment.variables.items():
            if isinstance(var_value, str):
                errors.extend(self._validate_variable_value(var_name, var_value))

        return errors

    def _validate_records(
        self, record_type: str, records: List[RecordModel]
    ) -> List[str]:
        """Validate DNS records.

        Args:
            record_type: Type of records
            records: List of records

        Returns:
            List of validation errors
        """
        errors: List[str] = []

        # Validate each record
        for record in records:
            errors.extend(self._validate_record(record))

        return errors

    def _validate_record(self, record: RecordModel) -> List[str]:
        """Validate a DNS record.

        Args:
            record: Record model

        Returns:
            List of validation errors
        """
        errors: List[str] = []

        # Validate record name
        if not self._is_valid_hostname(record.name):
            errors.append(f"Invalid record name: {record.name}")

        # Validate record value
        if isinstance(record.value, str):
            errors.extend(self._validate_variable_value("value", record.value))

        return errors

    def _validate_variable_references(self) -> List[str]:
        """Validate all variable references.

        Returns:
            List of validation errors
        """
        errors: List[str] = []

        # Check environment variable references
        for env in self.environments.values():
            if env.variables:
                for var_name, var_value in env.variables.items():
                    if isinstance(var_value, str):
                        errors.extend(
                            self._validate_variable_value(var_name, var_value)
                        )

        return errors

    def _validate_variable_value(self, name: str, value: str) -> List[str]:
        """Validate a variable value.

        Args:
            name: Variable name
            value: Variable value

        Returns:
            List of validation errors
        """
        errors: List[str] = []

        # Check for variable references
        var_refs = self._find_variable_references(value)
        for var_ref in var_refs:
            if var_ref not in self.variables:
                errors.append(f"Invalid variable reference in {name}: {var_ref}")

        return errors

    def _find_variable_references(self, value: str) -> Set[str]:
        """Find variable references in a string.

        Args:
            value: String to check

        Returns:
            Set of variable names
        """
        pattern = r"\${([^}]+)}"
        matches = re.findall(pattern, value)
        return set(matches)

    def _is_valid_hostname(self, hostname: str) -> bool:
        """Check if hostname is valid.

        Args:
            hostname: Hostname to check

        Returns:
            True if valid, False otherwise
        """
        if hostname == "@":
            return True

        pattern = (
            r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?"
            r"(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$"
        )
        return bool(re.match(pattern, hostname))
