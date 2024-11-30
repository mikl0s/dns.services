"""Environment validator for DNS template configurations."""
from typing import Dict, List, Set
import re

from ..models.base import EnvironmentModel, RecordModel, VariableModel


class EnvironmentValidator:
    """Validates environment configurations."""

    def __init__(
        self, base_variables: VariableModel, base_records: Dict[str, List[RecordModel]]
    ):
        """Initialize environment validator.

        Args:
            base_variables: Base template variables
            base_records: Base template records
        """
        self.base_variables = base_variables
        self.base_records = base_records
        self.variable_pattern = re.compile(r"\${([^}]+)}")

    def validate_environment(self, environment: EnvironmentModel) -> List[str]:
        """Validate an environment configuration.

        Args:
            environment: Environment to validate

        Returns:
            List of validation errors
        """
        errors = []
        errors.extend(self._validate_variables(environment))
        errors.extend(self._validate_records(environment))
        errors.extend(self._validate_variable_references(environment))
        return errors

    def _validate_variables(self, environment: EnvironmentModel) -> List[str]:
        """Validate environment variables.

        Args:
            environment: Environment to validate

        Returns:
            List of validation errors
        """
        errors = []
        base_vars = set(self.base_variables.dict().keys())

        # Check for invalid variable overrides
        for var_name in environment.variables:
            if var_name not in base_vars:
                errors.append(
                    f"Environment '{environment.name}' overrides undefined "
                    f"variable: {var_name}"
                )

        # Validate variable types match base variables
        base_var_types = {
            name: type(value) for name, value in self.base_variables.dict().items()
        }

        for name, value in environment.variables.items():
            if name in base_var_types:
                expected_type = base_var_types[name]
                if not isinstance(value, expected_type):
                    errors.append(
                        f"Variable '{name}' in environment '{environment.name}' "
                        f"has wrong type. Expected {expected_type.__name__}, "
                        f"got {type(value).__name__}"
                    )

        return errors

    def _validate_records(self, environment: EnvironmentModel) -> List[str]:
        """Validate environment records.

        Args:
            environment: Environment to validate

        Returns:
            List of validation errors
        """
        errors = []
        base_groups = set(self.base_records.keys())

        # Check for invalid record groups
        for group_name in environment.records:
            if group_name not in base_groups:
                errors.append(
                    f"Environment '{environment.name}' contains undefined "
                    f"record group: {group_name}"
                )

        # Validate record conflicts
        defined_names: Dict[str, Set[str]] = {}  # group -> set of record names
        for group_name, records in environment.records.items():
            if group_name not in defined_names:
                defined_names[group_name] = set()

            for record in records:
                name = record.name
                if name in defined_names[group_name]:
                    errors.append(
                        f"Duplicate record name '{name}' in group '{group_name}' "
                        f"of environment '{environment.name}'"
                    )
                defined_names[group_name].add(name)

        return errors

    def _validate_variable_references(self, environment: EnvironmentModel) -> List[str]:
        """Validate variable references in environment.

        Args:
            environment: Environment to validate

        Returns:
            List of validation errors
        """
        errors = []

        # Get all available variables
        available_vars = set(self.base_variables.dict().keys())
        available_vars.update(environment.variables.keys())

        def check_references(value: str, context: str) -> None:
            """Check variable references in a string value."""
            for match in self.variable_pattern.finditer(value):
                var_name = match.group(1)
                if var_name not in available_vars:
                    errors.append(
                        f"Undefined variable '{var_name}' referenced in {context}"
                    )

        # Check record values
        for group_name, records in environment.records.items():
            for record in records:
                if isinstance(record.value, str):
                    check_references(
                        record.value,
                        f"record '{record.name}' in group '{group_name}' "
                        f"of environment '{environment.name}'",
                    )

        return errors

    def validate_inheritance(
        self, environments: Dict[str, EnvironmentModel]
    ) -> List[str]:
        """Validate environment inheritance relationships.

        Args:
            environments: Dictionary of environments to validate

        Returns:
            List of validation errors
        """
        errors = []

        # Build inheritance graph
        inheritance_graph: Dict[str, Set[str]] = {}
        for env_name, env in environments.items():
            inheritance_graph[env_name] = set()

            # Check for inherited record groups
            base_groups = set(self.base_records.keys())
            env_groups = set(env.records.keys())

            for group in env_groups:
                if group in base_groups:
                    inheritance_graph[env_name].add(group)

        # Check for circular dependencies
        visited = set()
        path = []

        def check_circular(node: str) -> None:
            """Check for circular dependencies starting from node."""
            path.append(node)
            visited.add(node)

            for dep in inheritance_graph[node]:
                if dep in path:
                    cycle = " -> ".join(path[path.index(dep) :])
                    errors.append(f"Circular dependency detected: {cycle}")
                elif dep not in visited:
                    check_circular(dep)

            path.pop()

        # Check each node
        for env_name in inheritance_graph:
            if env_name not in visited:
                check_circular(env_name)

        return errors
