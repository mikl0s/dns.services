"""Record groups management for DNS template configurations."""

from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field, field_validator, ValidationInfo
import re

from ..models.base import RecordModel


class ARecord(RecordModel):
    """A record type."""

    type: Literal["A"] = Field(default="A", description="Record type")

    @field_validator("value")
    @classmethod
    def validate_ipv4(cls, v: str, info: ValidationInfo) -> str:
        """Validate IPv4 address."""
        import ipaddress

        try:
            ipaddress.IPv4Address(v)
        except ValueError:
            raise ValueError(f"Invalid IPv4 address: {v}")
        return v


class AAAARecord(RecordModel):
    """AAAA record type."""

    type: Literal["AAAA"] = Field(default="AAAA", description="Record type")

    @field_validator("value")
    @classmethod
    def validate_ipv6(cls, v: str, info: ValidationInfo) -> str:
        """Validate IPv6 address."""
        import ipaddress

        try:
            ipaddress.IPv6Address(v)
        except ValueError:
            raise ValueError(f"Invalid IPv6 address: {v}")
        return v


class CNAMERecord(RecordModel):
    """CNAME record type."""

    type: Literal["CNAME"] = Field(default="CNAME", description="Record type")

    @field_validator("value")
    @classmethod
    def validate_hostname(cls, v: str, info: ValidationInfo) -> str:
        """Validate hostname."""
        if not v or not isinstance(v, str):
            raise ValueError("Hostname must be a non-empty string")
        if v.endswith("."):
            v = v[:-1]
        if len(v) > 253:
            raise ValueError("Domain name exceeds maximum length")
        return v


class MXRecord(RecordModel):
    """MX record type."""

    type: Literal["MX"] = Field(default="MX", description="Record type")
    priority: int = Field(
        ...,  # Required field
        description="Priority for MX records (0-65535)",
        ge=0,  # Minimum value
        le=65535,  # Maximum value
    )

    @field_validator("priority", mode="before")
    @classmethod
    def validate_priority(cls, v: int, info: ValidationInfo) -> int:
        """Validate MX record priority."""
        if not isinstance(v, int):
            raise ValueError("Priority must be an integer")
        if v < 0:
            raise ValueError("Priority must be non-negative")
        if v > 65535:
            raise ValueError("Priority must not exceed 65535")
        return v

    @field_validator("value")
    @classmethod
    def validate_mx_hostname(cls, v: str, info: ValidationInfo) -> str:
        """Validate hostname."""
        if not v or not isinstance(v, str):
            raise ValueError("Hostname must be a non-empty string")
        if v.endswith("."):
            v = v[:-1]  # Remove trailing dot for length check
        if len(v) > 253:
            raise ValueError("Domain name exceeds maximum length")
        # Validate hostname format
        if not re.match(
            r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$",
            v,
        ):
            raise ValueError("Invalid hostname for MX record")
        return v

    class Config:
        validate_assignment = True
        extra = "allow"


class TXTRecord(RecordModel):
    """TXT record type."""

    type: Literal["TXT"] = Field(default="TXT", description="Record type")

    @field_validator("value")
    @classmethod
    def validate_txt(cls, v: str, info: ValidationInfo) -> str:
        """Validate TXT record value."""
        if not v or not isinstance(v, str):
            raise ValueError("TXT value must be a non-empty string")
        if len(v) > 255:
            raise ValueError("TXT value too long")
        return v


class CAARecord(RecordModel):
    """CAA record type."""

    type: Literal["CAA"] = Field(default="CAA", description="Record type")
    flags: int = Field(default=0, ge=0, le=255)
    tag: Literal["issue", "issuewild", "iodef"] = Field(...)

    @field_validator("value")
    @classmethod
    def validate_caa(cls, v: str, info: ValidationInfo) -> str:
        """Validate CAA record value."""
        if not v or not isinstance(v, str):
            raise ValueError("CAA value must be a non-empty string")
        if len(v) > 255:
            raise ValueError("CAA value too long")
        return v


class RecordGroup(BaseModel):
    """Record group model."""

    name: str = Field(..., description="Group name")
    description: Optional[str] = Field(None, description="Group description")
    enabled: bool = Field(default=True, description="Whether group is enabled")
    records: List[RecordModel] = Field(
        default_factory=list, description="Records in group"
    )


class RecordGroupManager:
    """Manages record groups within templates."""

    def __init__(self):
        """Initialize record group manager."""
        self.groups: Dict[str, RecordGroup] = {}

    def add_group(self, group: RecordGroup):
        """Add a record group.

        Args:
            group: Group to add
        """
        self.groups[group.name] = group

    def get_group(self, name: str) -> Optional[RecordGroup]:
        """Get a record group.

        Args:
            name: Group name

        Returns:
            Record group if found, None otherwise
        """
        return self.groups.get(name)

    def list_groups(self) -> List[str]:
        """List available record groups.

        Returns:
            List of group names
        """
        return list(self.groups.keys())

    def merge_groups(self, groups: List[str]) -> List[RecordModel]:
        """Merge multiple record groups.

        Args:
            groups: List of group names to merge

        Returns:
            Combined list of records

        Raises:
            KeyError: If a group is not found
        """
        records = []
        for group_name in groups:
            group = self.groups.get(group_name)
            if not group:
                raise KeyError(f"Record group not found: {group_name}")
            if group.enabled:
                records.extend(group.records)
        return records
