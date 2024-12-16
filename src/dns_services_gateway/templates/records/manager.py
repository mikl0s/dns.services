"""DNS record manager for template-based configurations."""

from typing import Dict, List, Optional, Set
from ..models.base import RecordModel
from .groups import RecordGroup
from .validator import RecordValidator


class RecordManager:
    """Manages DNS records and their operations."""

    def __init__(self, domain: str):
        """Initialize record manager.

        Args:
            domain: Base domain for records
        """
        self.domain = domain
        self.groups: Dict[str, RecordGroup] = {}
        self.validator = RecordValidator(domain)

    def add_group(self, name: str, records: List[RecordModel]) -> List[str]:
        """Add a record group.

        Args:
            name: Group name
            records: List of records for the group

        Returns:
            List of validation errors (empty if valid)
        """
        # Validate records
        errors = []
        for record in records:
            errors.extend(self.validator.validate_record(record))
        if errors:
            return errors

        # Create group
        group = RecordGroup(name=name, description=f"Record group {name}")
        group.records = records
        self.groups[name] = group
        return []

    def get_group(self, name: str) -> Optional[RecordGroup]:
        """Get a record group.

        Args:
            name: Group name

        Returns:
            RecordGroup if found, None otherwise
        """
        return self.groups.get(name)

    def remove_group(self, name: str) -> bool:
        """Remove a record group.

        Args:
            name: Group name

        Returns:
            True if group was removed, False if not found
        """
        if name in self.groups:
            del self.groups[name]
            return True
        return False

    def add_record(self, group_name: str, record: RecordModel) -> List[str]:
        """Add a record to a group.

        Args:
            group_name: Group name
            record: Record to add

        Returns:
            List of validation errors (empty if valid)
        """
        # Validate record
        errors = self.validator.validate_record(record)
        if errors:
            return errors

        # Check for duplicate records
        for group in self.groups.values():
            for existing in group.records:
                if existing.name == record.name and existing.type == record.type:
                    return [f"Record {record.name} ({record.type}) already exists"]

        # Get or create group
        if group_name not in self.groups:
            self.groups[group_name] = RecordGroup(
                name=group_name, description=f"Record group {group_name}"
            )

        # Add record to group
        group = self.groups[group_name]
        group.records.append(record)
        return []

    def update_record(self, record: RecordModel) -> List[str]:
        """Update an existing record.

        Args:
            record: Record to update

        Returns:
            List of validation errors (empty if valid)
        """
        # Validate record
        errors = self.validator.validate_record(record)
        if errors:
            return errors

        # Find and update record
        for group in self.groups.values():
            for i, existing in enumerate(group.records):
                if existing.name == record.name and existing.type == record.type:
                    group.records[i] = record
                    return []

        return ["Record not found"]

    def delete_record(self, record: RecordModel) -> bool:
        """Delete a record.

        Args:
            record: Record to delete

        Returns:
            True if record was deleted, False if not found
        """
        for group in self.groups.values():
            for i, existing in enumerate(group.records):
                if existing.name == record.name and existing.type == record.type:
                    group.records.pop(i)
                    return True
        return False

    def get_records(self) -> List[RecordModel]:
        """Get all records.

        Returns:
            List of all records
        """
        records: List[RecordModel] = []
        for group in self.groups.values():
            records.extend(group.records)
        return records

    def remove_record(
        self, group_name: str, record_type: str, name: str
    ) -> Optional[RecordModel]:
        """Remove a record from a group.

        Args:
            group_name: Group name
            record_type: Record type
            name: Record name

        Returns:
            Removed record if found, None otherwise
        """
        group = self.groups.get(group_name)
        if not group:
            return None

        for i, record in enumerate(group.records):
            if record.type == record_type and record.name == name:
                return group.records.pop(i)
        return None

    def get_all_records(self) -> List[RecordModel]:
        """Get all records from all groups.

        Returns:
            List of all records
        """
        records: List[RecordModel] = []
        for group in self.groups.values():
            records.extend(group.records)
        return records

    def get_records_by_type(self, record_type: str) -> List[RecordModel]:
        """Get all records of a specific type.

        Args:
            record_type: Record type to get

        Returns:
            List of matching records
        """
        records: List[RecordModel] = []
        for group in self.groups.values():
            records.extend([r for r in group.records if r.type == record_type])
        return records

    def get_record_names(self) -> Set[str]:
        """Get all record names.

        Returns:
            Set of record names
        """
        names: Set[str] = set()
        for record in self.get_all_records():
            if record.name == "@":
                names.add(self.domain)
            elif record.name.endswith(self.domain):
                names.add(record.name)
            else:
                names.add(f"{record.name}.{self.domain}")
        return names

    def validate(self) -> List[str]:
        """Validate all records and their relationships.

        Returns:
            List of validation errors (empty if valid)
        """
        # Convert groups to format expected by validator
        groups_dict = {name: group.records for name, group in self.groups.items()}
        return self.validator.validate_groups(groups_dict)

    def merge_groups(self, group_names: List[str]) -> List[RecordModel]:
        """Merge multiple record groups."""
        merged_records = []
        for group_name in group_names:
            if group_name not in self.groups:
                raise KeyError(f"Group '{group_name}' not found")
            merged_records.extend(self.groups[group_name].records)
        return merged_records
