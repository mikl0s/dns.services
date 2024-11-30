"""Record groups management for DNS template configurations."""
from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field, validator

from ..models.base import RecordModel


class ARecord(RecordModel):
    """A record type."""

    type: Literal["A"] = Field(default="A")

    @validator("value")
    def validate_ipv4(cls, v: str) -> str:
        """Validate IPv4 address."""
        import ipaddress

        try:
            ipaddress.IPv4Address(v)
        except ValueError:
            raise ValueError(f"Invalid IPv4 address: {v}")
        return v


class AAAARecord(RecordModel):
    """AAAA record type."""

    type: Literal["AAAA"] = Field(default="AAAA")

    @validator("value")
    def validate_ipv6(cls, v: str) -> str:
        """Validate IPv6 address."""
        import ipaddress

        try:
            ipaddress.IPv6Address(v)
        except ValueError:
            raise ValueError(f"Invalid IPv6 address: {v}")
        return v


class CNAMERecord(RecordModel):
    """CNAME record type."""

    type: Literal["CNAME"] = Field(default="CNAME")

    @validator("value")
    def validate_hostname(cls, v: str) -> str:
        """Validate hostname."""
        if v != "@" and not v.endswith("."):
            if not all(part.isalnum() or part == "-" for part in v.split(".")):
                raise ValueError(f"Invalid hostname: {v}")
        return v


class MXRecord(RecordModel):
    """MX record type."""

    type: Literal["MX"] = Field(default="MX")
    priority: int = Field(default=..., ge=0, le=65535)

    @validator("value")
    def validate_hostname(cls, v: str) -> str:
        """Validate hostname."""
        if v != "@" and not v.endswith("."):
            if not all(part.isalnum() or part == "-" for part in v.split(".")):
                raise ValueError(f"Invalid hostname: {v}")
        return v


class TXTRecord(RecordModel):
    """TXT record type."""

    type: Literal["TXT"] = Field(default="TXT")

    @validator("value")
    def validate_txt(cls, v: str) -> str:
        """Validate TXT record value."""
        if len(v) > 255:
            raise ValueError("TXT record value exceeds 255 characters")
        return v


class CAARecord(RecordModel):
    """CAA record type."""

    type: Literal["CAA"] = Field(default="CAA")
    flags: int = Field(default=0, ge=0, le=255)
    tag: Literal["issue", "issuewild", "iodef"] = Field(default=...)

    @validator("value")
    def validate_caa(cls, v: str) -> str:
        """Validate CAA record value."""
        if not v.startswith('"') or not v.endswith('"'):
            raise ValueError("CAA record value must be quoted")
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

    def add_group(self, group: RecordGroup) -> None:
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
        """
        records: List[RecordModel] = []
        for group in groups:
            if group_obj := self.get_group(group):
                if group_obj.enabled:
                    records.extend(group_obj.records)
        return records
