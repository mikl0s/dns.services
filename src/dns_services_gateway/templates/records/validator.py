"""DNS record validator for template configurations."""
from typing import Dict, List, Set
from ..models.base import RecordModel
from .groups import RecordGroup


class RecordValidator:
    """Validates DNS records and their relationships."""

    def __init__(self, domain: str) -> None:
        """Initialize record validator.

        Args:
            domain: Base domain for validation
        """
        self.domain = domain
        self.defined_names: Set[str] = set()

    def validate_groups(self, groups: Dict[str, List[RecordModel]]) -> List[str]:
        """Validate record groups.

        Args:
            groups: Dictionary of record groups

        Returns:
            List of validation errors
        """
        errors = []
        self.defined_names.clear()

        # First pass: collect all record names
        for group_name, records in groups.items():
            record_group = RecordGroup(
                name=group_name, description=f"Group {group_name}"
            )
            record_group.records = records
            for record in record_group.records:
                name = self._normalize_name(record.name)
                if name in self.defined_names:
                    errors.append(
                        f"Duplicate record name '{name}' in group '{group_name}'"
                    )
                self.defined_names.add(name)

        # Second pass: validate record relationships
        for group_name, records in groups.items():
            record_group = RecordGroup(
                name=group_name, description=f"Group {group_name}"
            )
            record_group.records = records
            errors.extend(self._validate_group_records(record_group))

        return errors

    def _normalize_name(self, name: str) -> str:
        """Normalize record name.

        Args:
            name: Record name to normalize

        Returns:
            Normalized record name
        """
        if name == "@":
            return self.domain
        if name.endswith(self.domain):
            return name
        return f"{name}.{self.domain}"

    def _validate_group_records(self, group: RecordGroup) -> List[str]:
        """Validate records within a group.

        Args:
            group: Record group to validate

        Returns:
            List of validation errors
        """
        errors = []

        # Validate CNAME conflicts
        cname_records = [r for r in group.records if r.type == "CNAME"]
        for cname in cname_records:
            name = self._normalize_name(cname.name)
            for record in group.records:
                if record.type != "CNAME" and self._normalize_name(record.name) == name:
                    errors.append(
                        f"CNAME record '{name}' conflicts with {record.type} record"
                    )

        # Validate MX records
        mx_records = [r for r in group.records if r.type == "MX"]
        seen_priorities: Set[int] = set()
        for mx in mx_records:
            priority = getattr(mx, "priority", None)
            if priority is None:
                errors.append(f"MX record '{mx.name}' missing priority")
            elif priority in seen_priorities:
                errors.append(
                    f"Duplicate MX priority {priority} for record '{mx.name}'"
                )
            else:
                seen_priorities.add(priority)

        return errors

    def validate_record(self, record: RecordModel) -> List[str]:
        """Validate a single record.

        Args:
            record: Record to validate

        Returns:
            List of validation errors
        """
        errors = []

        # Basic validation
        if not record.name:
            errors.append("Record name is required")
        if not record.type:
            errors.append("Record type is required")
        if not record.value:
            errors.append("Record value is required")

        # Type-specific validation
        if record.type == "MX":
            priority = getattr(record, "priority", None)
            if priority is None:
                errors.append(f"MX record '{record.name}' missing priority")
            elif not isinstance(priority, int):
                errors.append(f"MX record '{record.name}' priority must be an integer")

        return errors
