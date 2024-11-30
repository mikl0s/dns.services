"""Environment manager for DNS template configurations."""
from typing import Dict, List, Optional, Tuple
from copy import deepcopy
from enum import Enum

from ..models.base import EnvironmentModel, RecordModel, VariableModel
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
        self, base_variables: VariableModel, base_records: Dict[str, List[RecordModel]]
    ):
        """Initialize environment manager.

        Args:
            base_variables: Base template variables
            base_records: Base template records
        """
        self.base_variables = base_variables
        self.base_records = base_records
        self.environments: Dict[str, EnvironmentModel] = {}
        self.record_manager = RecordManager(domain=base_variables.domain)
        self.record_managers: Dict[str, RecordManager] = {}

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

        # Create environment-specific record manager
        variables = self._merge_variables(environment)
        domain = variables.domain
        record_manager = RecordManager(domain=domain)

        # Add base records
        for group_name, records in self.base_records.items():
            record_manager.add_group(group_name, deepcopy(records))

        # Override with environment-specific records
        for group_name, records in environment.records.items():
            record_manager.add_group(group_name, records)

        # Store environment and record manager
        self.environments[environment.name] = environment
        self.record_managers[environment.name] = record_manager

        return []

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

        # Get current records
        record_manager = self.record_managers.get(environment_name)
        if not record_manager:
            return [], [f"Environment {environment_name} not found"]

        current_records = record_manager.get_all_records()
        current_map = {(r.name, r.type): r for r in current_records}

        # Get target records
        target_records = []
        if mode == "full":
            # Full sync: use all records
            target_records = current_records
        else:
            # Incremental: use only changed records
            environment = self.environments.get(environment_name)
            if not environment:
                return [], [f"Environment {environment_name} not found"]
            for group in environment.records.values():
                target_records.extend(group)

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
            if current.value != target.value:
                changes.append(Change(ChangeType.UPDATE, target))

        # Records to delete
        for key in current_keys - target_keys:
            record = current_map[key]
            changes.append(Change(ChangeType.DELETE, record))

        return changes, errors

    def apply_changes(
        self, environment_name: str, changes: List[Change]
    ) -> Tuple[bool, List[str]]:
        """Apply record changes to an environment.

        Args:
            environment_name: Environment name
            changes: List of changes to apply

        Returns:
            Tuple of (success, errors)
        """
        record_manager = self.record_managers.get(environment_name)
        if not record_manager:
            return False, [f"Environment {environment_name} not found"]

        errors: List[str] = []
        success = True

        # Create changeset for rollback
        changeset = ChangeSet()
        changeset.domain = record_manager.domain
        changeset.environment = environment_name

        # Apply changes
        for change in changes:
            if change.type == ChangeType.CREATE:
                result = record_manager.add_record("default", change.record)
                if result:
                    errors.extend(result)
                    success = False
                else:
                    changeset.add_record(change.record)
            elif change.type == ChangeType.UPDATE:
                result = record_manager.update_record(change.record)
                if result:
                    errors.extend(result)
                    success = False
                else:
                    changeset.update_record(change.record)
            elif change.type == ChangeType.DELETE:
                if record_manager.delete_record(change.record):
                    changeset.delete_record(change.record)
                else:
                    errors.append(f"Failed to delete record {change.record.name}")
                    success = False

        return success, errors

    def _validate_environment(self, environment: EnvironmentModel) -> List[str]:
        """Validate environment configuration.

        Args:
            environment: Environment to validate

        Returns:
            List of validation errors
        """
        errors: List[str] = []

        # Validate name
        if not environment.name:
            errors.append("Environment name is required")
        elif environment.name in self.environments:
            errors.append(f"Environment {environment.name} already exists")

        # Validate variables
        if not environment.variables:
            errors.append("Environment variables are required")
        else:
            variables = self._merge_variables(environment)
            if not variables.domain:
                errors.append("Domain is required in variables")

        return errors

    def _merge_variables(self, environment: EnvironmentModel) -> VariableModel:
        """Merge base and environment variables.

        Args:
            environment: Environment to merge variables for

        Returns:
            Merged variables
        """
        variables = deepcopy(self.base_variables)
        if environment.variables:
            for key, value in environment.variables.items():
                setattr(variables, key, value)
        return variables
