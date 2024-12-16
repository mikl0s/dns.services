"""DNS record validator for template configurations."""

from typing import Dict, List, Set
import re
from ipaddress import ip_address, IPv4Address, IPv6Address, AddressValueError
from ..models.base import RecordModel
from .groups import RecordGroup, CNAMERecord
from dns_services_gateway.exceptions import ValidationError


class RecordValidator:
    """Validates DNS records and their relationships."""

    def __init__(self, domain: str = "example.com") -> None:
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
        name_to_record = {}  # Track record names and their details

        # First pass: collect all record names and validate duplicates
        for group_name, records in groups.items():
            record_group = RecordGroup(
                name=group_name, description=f"Group {group_name}"
            )
            record_group.records = records
            for record in record_group.records:
                name = self._normalize_name(record.name)
                if name in name_to_record and record.type != "CNAME":
                    existing = name_to_record[name]
                    if existing[1] != "CNAME":  # Only report non-CNAME duplicates here
                        errors.append(
                            f"Duplicate record name '{name}' in groups '{group_name}' and '{existing[0]}'"
                        )
                else:
                    name_to_record[name] = (group_name, record.type)
                    if record.type != "CNAME":
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
        """Normalize record name."""
        if not name:
            return self.domain
        if name == "@":
            return self.domain
        if name.endswith("."):
            name = name[:-1]
        if "." not in name:
            return f"{name}.{self.domain}"
        return name

    def _validate_group_records(self, group: RecordGroup) -> List[str]:
        """Validate records within a group.

        Args:
            group: Record group to validate

        Returns:
            List of validation errors
        """
        errors = []

        # Validate CNAME conflicts
        errors.extend(self._check_cname_conflicts(group.records))

        # Validate MX records
        mx_records = [r for r in group.records if r.type == "MX"]
        seen_priorities: Dict[int, str] = {}
        for mx in mx_records:
            priority = getattr(mx, "priority", None)
            if priority is None:
                errors.append(f"MX record '{mx.name}' missing priority")
            elif not isinstance(priority, int):
                errors.append(f"MX priority must be an integer")
            else:
                if priority in seen_priorities:
                    errors.append(
                        f"Duplicate MX priority {priority} for records '{mx.name}' and '{seen_priorities[priority]}'"
                    )
                else:
                    seen_priorities[priority] = mx.name

        return errors

    def _check_cname_conflicts(self, records: List[RecordModel]) -> List[str]:
        """Check for CNAME conflicts."""
        errors = []
        cname_records = [r for r in records if r.type == "CNAME"]
        other_records = [r for r in records if r.type != "CNAME"]

        for cname in cname_records:
            cname_name = self._normalize_name(cname.name)
            for other in other_records:
                other_name = self._normalize_name(other.name)
                if cname_name == other_name:
                    errors.append(
                        f"CNAME record '{cname.name}' conflicts with {other.type} record"
                    )
                    break

        return errors

    def validate_record(self, record: RecordModel) -> bool:
        """Validate a single DNS record.

        Args:
            record: The record to validate

        Returns:
            bool: True if the record is valid

        Raises:
            ValidationError: If the record is invalid
        """
        # Skip validation if value contains variable references
        if "${" in record.value or "{{" in record.value:
            return True

        # Validate name based on record type
        if record.name != "@" and not "${" in record.name and not "{{" in record.name:
            if record.type == "PTR":
                if not re.match(
                    r"^(\d{1,3}\.){1,4}(in-addr|ip6)\.arpa\.?$",
                    record.name,
                    re.IGNORECASE,
                ):
                    raise ValidationError("PTR name must be in reverse DNS format")
            elif record.type == "SRV":
                if not record.name.startswith("_") or "._" not in record.name:
                    raise ValidationError(
                        "SRV name must be in format _service._proto.name"
                    )
            else:
                # Standard hostname validation for other records
                if not re.match(
                    r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*$",
                    record.name,
                ):
                    raise ValidationError(
                        "Invalid hostname: must start and end with alphanumeric character"
                    )

        # Type-specific validation
        try:
            if record.type == "A":
                try:
                    ip = ip_address(record.value)
                    if not isinstance(ip, IPv4Address):
                        raise ValidationError(
                            f"Expected IPv4 address, got {record.value}"
                        )
                except (AddressValueError, ValueError):
                    raise ValidationError(f"Expected 4 octets in '{record.value}'")

            elif record.type == "AAAA":
                try:
                    ip = ip_address(record.value)
                    if not isinstance(ip, IPv6Address):
                        raise ValidationError(
                            f"Expected IPv6 address, got {record.value}"
                        )
                except (AddressValueError, ValueError):
                    raise ValidationError(
                        f"At least 3 parts expected in '{record.value}'"
                    )

            elif record.type == "CNAME":
                # CNAME cannot be at apex
                if record.name == "@":
                    raise ValidationError("CNAME record cannot be at apex (@)")
                if not record.value:
                    raise ValidationError("Invalid hostname for CNAME record")
                value = record.value.rstrip(".")
                if not re.match(
                    r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*$",
                    value,
                ):
                    raise ValidationError("Invalid hostname for CNAME record")

            elif record.type == "MX":
                # Validate priority
                if record.priority is None:
                    raise ValidationError("MX record must have a priority")
                if isinstance(record.priority, str):
                    if "${" in record.priority or "{{" in record.priority:
                        return True
                    try:
                        priority = int(record.priority)
                        if priority < 0:
                            raise ValidationError("MX priority must be non-negative")
                    except ValueError:
                        raise ValidationError("MX priority must be an integer")
                elif record.priority < 0:
                    raise ValidationError("MX priority must be non-negative")

                # Validate hostname
                if not record.value:
                    raise ValidationError("Invalid hostname for MX record")
                value = record.value.rstrip(".")
                if not re.match(
                    r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*$",
                    value,
                ):
                    raise ValidationError("Invalid hostname for MX record")

            elif record.type == "SRV":
                # Validate priority, weight, port
                for field in ["priority", "weight", "port"]:
                    value = getattr(record, field)
                    if value is None:
                        raise ValidationError(f"SRV record must have {field}")
                    if isinstance(value, str):
                        if "${" in value or "{{" in value:
                            continue
                        try:
                            value = int(value)
                            if value < 0:
                                raise ValidationError(
                                    f"SRV {field} must be non-negative"
                                )
                        except ValueError:
                            raise ValidationError(f"SRV {field} must be an integer")
                    elif value < 0:
                        raise ValidationError(f"SRV {field} must be non-negative")

                # Validate target hostname
                if not record.value:
                    raise ValidationError("Invalid hostname for SRV target")
                value = record.value.rstrip(".")
                if not re.match(
                    r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*$",
                    value,
                ):
                    raise ValidationError("Invalid hostname for SRV target")

            elif record.type == "NS":
                if not record.value:
                    raise ValidationError("Invalid hostname for NS record")
                value = record.value.rstrip(".")
                if not re.match(
                    r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*$",
                    value,
                ):
                    raise ValidationError("Invalid hostname for NS record")

            elif record.type == "CAA":
                try:
                    flags, tag, value = record.value.split(" ", 2)
                    flags = int(flags)
                    if flags not in [0, 128]:
                        raise ValidationError("CAA flags must be 0 or 128")
                    if tag not in ["issue", "issuewild", "iodef"]:
                        raise ValidationError(
                            "CAA tag must be 'issue', 'issuewild', or 'iodef'"
                        )
                    if not value.startswith('"') or not value.endswith('"'):
                        raise ValidationError("CAA value must be quoted")
                except (ValueError, AttributeError):
                    raise ValidationError(
                        "CAA record must have flags, tag, and quoted value"
                    )

            elif record.type == "SOA":
                try:
                    parts = record.value.split()
                    if len(parts) != 7:
                        raise ValidationError(
                            "SOA record must have mname, rname, serial, refresh, retry, expire, and minimum"
                        )

                    mname, rname, serial, refresh, retry, expire, minimum = parts

                    # Validate hostnames
                    for hostname in [mname, rname]:
                        hostname = hostname.rstrip(".")
                        if not re.match(
                            r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*$",
                            hostname,
                        ):
                            raise ValidationError(
                                f"Invalid hostname in SOA record: {hostname}"
                            )

                    # Validate numeric values
                    for value in [serial, refresh, retry, expire, minimum]:
                        try:
                            value = int(value)
                            if value < 0:
                                raise ValidationError(
                                    "SOA numeric values must be non-negative"
                                )
                        except ValueError:
                            raise ValidationError("SOA numeric values must be integers")

                except (ValueError, IndexError):
                    raise ValidationError(
                        "SOA record must have mname, rname, serial, refresh, retry, expire, and minimum"
                    )

        except ValidationError as e:
            raise ValidationError(str(e))

        return True

    def _is_valid_hostname(self, hostname: str) -> bool:
        """Validate a hostname."""
        if not hostname:
            return False
        # Remove trailing dot if present
        if hostname.endswith("."):
            hostname = hostname[:-1]
        # Basic hostname validation
        if len(hostname) > 253:
            return False
        allowed = re.compile(
            r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*$"
        )
        return bool(allowed.match(hostname))
