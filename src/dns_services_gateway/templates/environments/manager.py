"""Environment manager for DNS template configurations."""

from typing import Dict, List, Optional, Tuple, Union, Any
from copy import deepcopy
from enum import Enum

from ..models.base import (
    EnvironmentModel,
    RecordModel,
    VariableModel,
    SingleVariableModel,
)
from ..records.manager import RecordManager
from ..safety.rollback import ChangeSet


class ChangeType(str, Enum):
    """Change type enumeration."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class Change:
    """Represents a record change."""

    def __init__(self, type: ChangeType, record: RecordModel):
        """Initialize change.

        Args:
            type: Change type
            record: Record being changed
        """
        self.type = type
        self.record = record
        self.id = f"{type.value}_{record.name}_{record.type}"


class EnvironmentManager:
    """Manages environment-specific configurations."""

    def __init__(
        self,
        base_variables: Union[Dict[str, Any], VariableModel, "VariableManager"],
        base_records: Dict[str, List[RecordModel]],
    ):
        """Initialize environment manager.

        Args:
            base_variables: Base template variables (dict, VariableModel, or VariableManager)
            base_records: Base template records
        """
        # Get variables in a consistent format
        if isinstance(base_variables, dict):
            base_vars = base_variables
        elif hasattr(base_variables, "get_variables"):
            base_vars = base_variables.get_variables(flatten_custom_vars=True)
        else:
            base_vars = {}
            if hasattr(base_variables, "model_dump"):
                base_vars = base_variables.model_dump()
            else:
                base_vars = {
                    "domain": base_variables.domain,
                    "ttl": base_variables.ttl,
                    "custom_vars": (
                        base_variables.custom_vars
                        if hasattr(base_variables, "custom_vars")
                        else {}
                    ),
                }

        # Store base variables in a consistent format
        self.base_variables = {}

        # Handle descriptions if present
        descriptions = {}
        if isinstance(base_vars, dict) and "_descriptions" in base_vars:
            desc_val = base_vars["_descriptions"]
            if isinstance(desc_val, dict):
                descriptions = desc_val

        # Handle root level variables
        for key in ["domain", "ttl"]:
            if key in base_vars:
                value = base_vars[key]
                if isinstance(value, dict) and "value" in value:
                    self.base_variables[key] = SingleVariableModel(
                        name=key,
                        value=str(value["value"]),
                        description=value.get("description", descriptions.get(key, "")),
                    )
                else:
                    self.base_variables[key] = SingleVariableModel(
                        name=key,
                        value=str(value),
                        description=descriptions.get(key, ""),
                    )

        # Add custom variables
        if "custom_vars" in base_vars:
            custom_vars = base_vars["custom_vars"]
            if isinstance(custom_vars, dict):
                for name, var in custom_vars.items():
                    if isinstance(var, dict) and "value" in var:
                        self.base_variables[name] = SingleVariableModel(
                            name=name,
                            value=str(var["value"]),
                            description=var.get("description", ""),
                        )
                    else:
                        self.base_variables[name] = SingleVariableModel(
                            name=name, value=str(var), description=""
                        )

        # Convert base records to model instances
        self.base_records = {}
        for record_type, records in base_records.items():
            self.base_records[record_type] = []
            for record in records:
                if isinstance(record, dict):
                    record_data = dict(record)  # Make a copy
                    record_data["type"] = record_type
                    self.base_records[record_type].append(RecordModel(**record_data))
                else:
                    self.base_records[record_type].append(record)

        self.environments = {}
        self.record_managers = {}

        # Get domain value from base variables
        domain = (
            self.base_variables["domain"].value
            if "domain" in self.base_variables
            else ""
        )
        self.record_manager = RecordManager(domain=domain)

    def add_environment(self, environment: EnvironmentModel) -> List[str]:
        """Add an environment configuration.

        Args:
            environment: Environment configuration to add

        Returns:
            List of validation errors (empty if valid)
        """
        errors = self._validate_environment(environment)
        if errors:
            return errors

        if environment.name in self.environments:
            errors.append(f"Environment {environment.name} already exists")
            return errors

        # Merge variables and create new EnvironmentModel
        try:
            merged_vars = self._merge_variables(environment)
            environment.variables = merged_vars
        except Exception as e:
            errors.append(f"Failed to merge variables: {str(e)}")
            return errors

        # Create record manager for this environment
        try:
            domain = self.base_variables["domain"].value  # Use base domain
            self.record_managers[environment.name] = RecordManager(domain=domain)
        except Exception as e:
            errors.append(f"Failed to create record manager: {str(e)}")
            return errors

        # Store environment
        self.environments[environment.name] = environment
        return errors

    def _merge_variables(
        self, environment: EnvironmentModel
    ) -> Dict[str, SingleVariableModel]:
        """Merge base and environment variables.

        Args:
            environment: Environment to merge variables from

        Returns:
            Merged variables dictionary
        """
        # Start with a copy of base variables
        merged = {name: deepcopy(var) for name, var in self.base_variables.items()}

        # Merge environment variables
        if environment.variables:
            for name, var in environment.variables.items():
                if isinstance(var, SingleVariableModel):
                    merged[name] = var
                elif isinstance(var, dict):
                    if "value" in var:
                        # Handle nested variable structure
                        merged[name] = SingleVariableModel(
                            name=name,
                            value=str(var["value"]),  # Convert value to string
                            description=var.get("description", ""),
                        )
                    else:
                        # Handle flat variable structure
                        merged[name] = SingleVariableModel(
                            name=name,
                            value=str(var),
                            description="",
                        )
                else:
                    # Handle simple value
                    merged[name] = SingleVariableModel(
                        name=name,
                        value=str(var),
                        description="",
                    )

        return merged

    def get_environment(self, name: str) -> Optional[EnvironmentModel]:
        """Get an environment configuration.

        Args:
            name: Environment name

        Returns:
            EnvironmentModel if found, None otherwise
        """
        return self.environments.get(name)

    def remove_environment(self, name: str) -> bool:
        """Remove an environment configuration.

        Args:
            name: Environment name

        Returns:
            True if environment was removed, False if not found
        """
        if name in self.environments:
            del self.environments[name]
            del self.record_managers[name]
            return True
        return False

    def calculate_changes(
        self, environment_name: str, mode: str = "full"
    ) -> Tuple[List[Change], List[str]]:
        """Calculate record changes for an environment.

        Args:
            environment_name: Environment name
            mode: Change calculation mode ("full", "incremental")

        Returns:
            Tuple of (changes, errors)
        """
        errors: List[str] = []
        changes: List[Change] = []

        # Get environment
        environment = self.environments.get(environment_name)
        if not environment:
            return [], [f"Environment {environment_name} not found"]

        # Get record manager
        record_manager = self.record_managers.get(environment_name)
        if not record_manager:
            return [], [f"Environment {environment_name} not found"]

        # Get current records
        current_records = record_manager.get_all_records()
        current_map = {(r.name, r.type): r for r in current_records}

        # Get target records from base records and environment records
        target_records = []
        for record_type, records in self.base_records.items():
            for record in records:
                target_records.append(record)

        # Add environment-specific records
        if environment.records:
            for record_type, records in environment.records.items():
                for record in records:
                    if isinstance(record, dict):
                        record_data = dict(record)  # Make a copy
                        record_data["type"] = record_type
                        target_records.append(RecordModel(**record_data))
                    else:
                        target_records.append(record)

        # Calculate changes
        target_map = {(r.name, r.type): r for r in target_records}
        current_keys = set(current_map.keys())
        target_keys = set(target_map.keys())

        # Records to create
        for key in target_keys - current_keys:
            record = target_map[key]
            changes.append(Change(ChangeType.CREATE, record))

        # Records to update
        for key in current_keys & target_keys:
            current = current_map[key]
            target = target_map[key]
            if current.value != target.value or current.ttl != target.ttl:
                changes.append(Change(ChangeType.UPDATE, target))

        # Records to delete (only in force mode or full mode)
        if mode in ["force", "full"]:
            for key in current_keys - target_keys:
                record = current_map[key]
                changes.append(Change(ChangeType.DELETE, record))

        return changes, errors

    def apply_changes(self, name: str, changes: List[Change]) -> Tuple[bool, List[str]]:
        """Apply changes to an environment.

        Args:
            name: Environment name
            changes: Changes to apply

        Returns:
            Tuple of (success, errors)
        """
        errors = []
        if name not in self.environments:
            return False, [f"Environment {name} not found"]

        if not changes:
            return True, []

        record_manager = self.record_managers.get(name)
        if not record_manager:
            return False, [f"Record manager for {name} not found"]

        try:
            # Apply each change
            for change in changes:
                if change.type == ChangeType.CREATE:
                    result = record_manager.add_record("default", change.record)
                    if isinstance(result, list):
                        errors.extend(result)
                    elif not result:
                        errors.append(f"Failed to create record {change.record.name}")
                elif change.type == ChangeType.UPDATE:
                    result = record_manager.update_record(change.record)
                    if isinstance(result, list):
                        errors.extend(result)
                    elif not result:
                        errors.append(f"Failed to update record {change.record.name}")
                elif change.type == ChangeType.DELETE:
                    result = record_manager.delete_record(change.record)
                    if isinstance(result, list):
                        errors.extend(result)
                    elif not result:
                        errors.append(f"Failed to delete record {change.record.name}")

            return len(errors) == 0, errors
        except Exception as e:
            return False, [str(e)]

    def _validate_environment(self, environment: EnvironmentModel) -> List[str]:
        """Validate environment configuration.

        Args:
            environment: Environment to validate

        Returns:
            List of validation errors
        """
        errors = []

        # Check for required fields
        if not environment.name:
            errors.append("Environment name is required")

        # Check for required variables
        required_vars = ["domain", "ttl"]
        if environment.variables:
            vars_dict = environment.variables
            if not isinstance(vars_dict, dict):
                vars_dict = vars_dict.model_dump()

            for var in required_vars:
                if var not in vars_dict:
                    errors.append(f"Missing required variable: {var}")
                elif not vars_dict[var].get("value"):
                    errors.append(f"Value required for variable: {var}")

        # Validate record types
        if environment.records:
            valid_record_types = {
                "A",
                "AAAA",
                "CNAME",
                "MX",
                "TXT",
                "NS",
                "SOA",
                "SRV",
                "CAA",
            }
            for record_type in environment.records:
                if record_type not in valid_record_types:
                    errors.append(f"Invalid record type: {record_type}")

        return errors

    def apply_environment(self, name: str) -> Dict[str, Any]:
        """Apply environment changes.

        Args:
            name: Environment name

        Returns:
            Dict with success status and any errors
        """
        if name not in self.environments:
            return {"success": False, "errors": [f"Environment {name} not found"]}

        try:
            # Validate environment first
            errors = self.validate_environment(name)
            if errors:
                return {"success": False, "errors": errors}

            # Apply environment changes
            env = self.environments[name]

            # Apply variables
            if env.variables:
                for var_name, var in env.variables.items():
                    if not isinstance(var, SingleVariableModel):
                        return {
                            "success": False,
                            "errors": [f"Invalid variable type for {var_name}"],
                        }

            # Apply records if present
            if env.records:
                for record_type, records in env.records.items():
                    for record_data in records:
                        # Convert dict to RecordModel if needed
                        if isinstance(record_data, dict):
                            record_data["type"] = record_type
                            record = RecordModel(**record_data)
                        else:
                            record = record_data

                        # Add record to manager
                        errors = self.record_manager.add_record("default", record)
                        if errors:
                            return {"success": False, "errors": errors}

            return {"success": True, "errors": []}

        except Exception as e:
            return {"success": False, "errors": [str(e)]}

    def update_environment(
        self, name: str, variables: Optional[Dict[str, Any]] = None
    ) -> EnvironmentModel:
        """Update an environment.

        Args:
            name: Environment name
            variables: Environment variables to update

        Returns:
            Updated environment
        """
        if name not in self.environments:
            raise ValueError(f"Environment {name} not found")

        env = self.environments[name]
        if variables:
            # Convert variables to VariableModel instances if needed
            var_models = {}
            for var_name, var_value in variables.items():
                if isinstance(var_value, SingleVariableModel):
                    var_models[var_name] = var_value
                elif isinstance(var_value, dict) and "value" in var_value:
                    var_models[var_name] = SingleVariableModel(
                        name=var_name,
                        value=var_value["value"],
                        description=var_value.get("description", ""),
                    )
                else:
                    var_models[var_name] = SingleVariableModel(
                        name=var_name, value=str(var_value), description=""
                    )
            env.variables = var_models

        errors = self._validate_environment(env)
        if errors:
            raise ValueError(", ".join(errors))

        return env

    def import_environment(self, data: Dict[str, Any]) -> EnvironmentModel:
        """Import environment configuration.

        Args:
            data: Environment configuration data

        Returns:
            Imported environment
        """
        # Convert variables to VariableModel instances
        if "variables" in data:
            var_models = {}
            for var_name, var_value in data["variables"].items():
                if isinstance(var_value, dict) and "value" in var_value:
                    var_models[var_name] = SingleVariableModel(
                        name=var_name,
                        value=var_value["value"],
                        description=var_value.get("description", ""),
                    )
                else:
                    var_models[var_name] = SingleVariableModel(
                        name=var_name, value=str(var_value), description=""
                    )
            data["variables"] = var_models

        env = EnvironmentModel(**data)
        errors = self.add_environment(env)
        if errors:
            raise ValueError(", ".join(errors))
        return env

    def merge_environments(
        self, environments: List[str]
    ) -> Dict[str, SingleVariableModel]:
        """Merge environment variables.

        Args:
            environments: List of environment names

        Returns:
            Dict of merged variables
        """
        merged = {}
        for env_name in environments:
            env = self.get_environment(env_name)
            if not env:
                continue
            if env.variables:
                merged.update(env.variables)
        return merged

    def list_environments(self) -> Dict[str, EnvironmentModel]:
        """List all environments.

        Returns:
            Dictionary of environment name to EnvironmentModel
        """
        return self.environments

    def create_environment(
        self, name: str, variables: Optional[Dict[str, Any]] = None
    ) -> EnvironmentModel:
        """Create a new environment.

        Args:
            name: Environment name
            variables: Environment variables (optional)

        Returns:
            Created environment
        """
        # Convert variables to VariableModel instances
        var_models = {}
        if variables:
            for var_name, var_value in variables.items():
                if isinstance(var_value, SingleVariableModel):
                    var_models[var_name] = var_value
                elif isinstance(var_value, dict) and "value" in var_value:
                    var_models[var_name] = SingleVariableModel(
                        name=var_name,
                        value=var_value["value"],
                        description=var_value.get("description", ""),
                    )
                else:
                    var_models[var_name] = SingleVariableModel(
                        name=var_name, value=str(var_value), description=""
                    )

        env = EnvironmentModel(name=name, variables=var_models)
        errors = self.add_environment(env)
        if errors:
            raise ValueError(", ".join(errors))
        return self.environments[name]

    def delete_environment(self, name: str) -> None:
        """Delete an environment.

        Args:
            name: Environment name
        """
        if name in self.environments:
            del self.environments[name]
            if name in self.record_managers:
                del self.record_managers[name]

    def get_environment_variables(self, name: str) -> Dict[str, Any]:
        """Get environment variables.

        Args:
            name: Environment name

        Returns:
            Environment variables
        """
        env = self.get_environment(name)
        if not env:
            raise ValueError(f"Environment {name} not found")
        return env.variables

    def set_environment_variable(
        self,
        name: str,
        variable: Union[Dict[str, Any], VariableModel, SingleVariableModel],
    ) -> None:
        """Set an environment variable.

        Args:
            name: Environment name
            variable: Variable to set
        """
        if name not in self.environments:
            raise ValueError(f"Environment {name} not found")

        # Convert variable to SingleVariableModel
        if isinstance(variable, SingleVariableModel):
            var_model = variable
        elif isinstance(variable, VariableModel):
            # If VariableModel has name/value fields directly, use those
            if hasattr(variable, "name") and hasattr(variable, "value"):
                var_model = SingleVariableModel(
                    name=variable.name,
                    value=variable.value,
                    description=(
                        variable.description if hasattr(variable, "description") else ""
                    ),
                )
                if not self.environments[name].variables:
                    self.environments[name].variables = {}
                self.environments[name].variables[var_model.name] = var_model
                return
            else:
                # Otherwise handle it as a domain/ttl/custom_vars model
                if not self.environments[name].variables:
                    self.environments[name].variables = {}

                # Add domain and ttl variables
                self.environments[name].variables["domain"] = SingleVariableModel(
                    name="domain",
                    value=variable.domain,
                    description="Domain name",
                )
                self.environments[name].variables["ttl"] = SingleVariableModel(
                    name="ttl",
                    value=variable.ttl,
                    description="Default TTL",
                )

                # Add custom variables
                for var_name, var_value in variable.custom_vars.items():
                    if isinstance(var_value, dict) and "value" in var_value:
                        self.environments[name].variables[var_name] = (
                            SingleVariableModel(
                                name=var_name,
                                value=var_value["value"],
                                description=var_value.get("description", ""),
                            )
                        )
                    else:
                        self.environments[name].variables[var_name] = (
                            SingleVariableModel(
                                name=var_name,
                                value=str(var_value),
                                description="",
                            )
                        )
                return
        elif isinstance(variable, dict):
            var_name = variable.get("name")
            if not var_name:
                raise ValueError("Variable name is required")
            if "value" in variable:
                var_model = SingleVariableModel(
                    name=var_name,
                    value=str(variable["value"]),
                    description=variable.get("description", ""),
                )
            else:
                var_model = SingleVariableModel(
                    name=var_name,
                    value=str(variable),
                    description="",
                )
        else:
            raise ValueError("Invalid variable type")

        # Update environment variables
        if not self.environments[name].variables:
            self.environments[name].variables = {}
        self.environments[name].variables[var_model.name] = var_model

    def remove_environment_variable(self, name: str, variable_name: str) -> None:
        """Remove environment variable.

        Args:
            name: Environment name
            variable_name: Variable name to remove
        """
        env = self.get_environment(name)
        if not env:
            raise ValueError(f"Environment {name} not found")

        if env.variables and variable_name in env.variables:
            del env.variables[variable_name]

    def clone_environment(self, source: str, target: str) -> EnvironmentModel:
        """Clone an environment.

        Args:
            source: Source environment name
            target: Target environment name

        Returns:
            Cloned environment
        """
        source_env = self.get_environment(source)
        if not source_env:
            raise ValueError(f"Environment {source} not found")

        target_env = EnvironmentModel(
            name=target, variables=source_env.variables, records=source_env.records
        )

        errors = self.add_environment(target_env)
        if errors:
            raise ValueError(", ".join(errors))

        return target_env

    def validate_environment(self, name: str) -> List[str]:
        """Validate environment configuration.

        Args:
            name: Environment name

        Returns:
            List of validation errors
        """
        env = self.get_environment(name)
        if not env:
            return [f"Environment {name} not found"]
        return self._validate_environment(env)

    def export_environment(self, name: str) -> Dict[str, Any]:
        """Export environment configuration.

        Args:
            name: Environment name

        Returns:
            Environment configuration as dictionary
        """
        env = self.get_environment(name)
        if not env:
            raise ValueError(f"Environment {name} not found")
        return env.model_dump()

    def _rollback_changes(self, changeset: ChangeSet) -> None:
        """Rollback changes on failure.

        Args:
            changeset: Changes to rollback
        """
        record_manager = self.record_managers.get(changeset.environment)
        if not record_manager:
            return

        for record, action in changeset.records:
            if action == "create":
                record_manager.delete_record(record)
            elif action == "update":
                record_manager.update_record(record)
            elif action == "delete":
                record_manager.add_record("default", record)
