"""Data models for DNS Services Gateway."""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator, ConfigDict
from dataclasses import dataclass, field
from datetime import datetime


class DNSRecord(BaseModel):
    """DNS record model."""

    id: str = Field(..., description="Record ID")
    type: str = Field(..., description="Record type (A, AAAA, CNAME, TXT, etc.)")
    name: str = Field(..., description="Record name/hostname")
    content: str = Field(..., description="Record content/value")
    ttl: int = Field(3600, description="Time to live in seconds")
    priority: Optional[int] = Field(None, description="Record priority (MX, SRV)")
    proxied: bool = Field(False, description="Whether the record is proxied")

    model_config = ConfigDict(extra="allow")


@dataclass
class DomainInfo:
    """Domain information."""

    id: str
    name: str
    status: str
    expires: Optional[datetime] = None
    auto_renew: bool = False
    nameservers: List[str] = field(default_factory=list)
    records: List[Dict[str, Any]] = field(default_factory=list)
    expires_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    registrar: Optional[str] = None

    @property
    def registrar_name(self) -> Optional[str]:
        """Get registrar name from metadata."""
        return self.metadata.get("registrar")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DomainInfo":
        """Create instance from dictionary."""
        metadata = data.get("metadata", {})
        expires = None
        if expires_at := data.get("expires_at"):
            try:
                expires = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        return cls(
            id=data["id"],
            name=data["name"],
            status=data["status"],
            expires=expires,
            auto_renew=data.get("auto_renew", False),
            nameservers=data.get("nameservers", []),
            records=data.get("records", []),
            expires_at=data.get("expires_at"),
            metadata=metadata,
            registrar=data.get("registrar") or metadata.get("registrar"),
        )


class DomainAvailabilityResponse(BaseModel):
    """Response for domain availability check."""

    domain: Optional[str] = Field(None, description="Domain name checked")
    available: bool = Field(..., description="Whether the domain is available")
    price: Optional[float] = Field(None, description="Registration price if available")
    currency: Optional[str] = Field(None, description="Currency for the price")
    premium: Optional[bool] = Field(
        None, description="Whether this is a premium domain"
    )
    timestamp: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Response timestamp",
    )

    model_config = ConfigDict(extra="allow")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DomainAvailabilityResponse":
        """Create instance from dictionary."""
        return cls(
            domain=data.get("domain"),
            available=data["available"],
            price=data.get("price"),
            currency=data.get("currency"),
            premium=data.get("premium"),
            timestamp=data.get("timestamp"),
        )


class OperationResponse(BaseModel):
    """Response for domain operations."""

    status: str = Field(..., description="Operation status")
    operation: str = Field(..., description="Operation type")
    data: Dict[str, Any] = Field(default_factory=dict, description="Operation data")
    timestamp: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Operation timestamp",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    model_config = ConfigDict(extra="allow")


class AuthResponse(BaseModel):
    """Authentication response model."""

    token: Optional[str] = None
    expires: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(hours=1)
    )
    refresh_token: Optional[str] = None
    expiration: Optional[str] = None

    model_config = ConfigDict(extra="allow")

    def __init__(self, **data):
        """Initialize authentication response model with given data.

        Args:
            **data: Keyword arguments for model initialization.
        """
        if "expiration" in data:
            if isinstance(data["expiration"], datetime):
                data["expires"] = data["expiration"]
                data["expiration"] = data["expiration"].isoformat()
            elif not data.get("expires"):
                data["expires"] = data["expiration"]
        super().__init__(**data)

    @field_validator("expires", mode="before")
    @classmethod
    def set_expiration(cls, v, info):
        """Set expiration from string or datetime."""
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        elif isinstance(v, datetime):
            return v
        return v


class NameserverUpdate(BaseModel):
    """Nameserver update request model."""

    domain: str = Field(..., description="Domain name or ID")
    nameservers: List[str] = Field(..., description="List of nameservers")

    model_config = ConfigDict(extra="allow")

    def __init__(self, **data):
        """Initialize nameserver update model with given data.

        Args:
            **data: Keyword arguments for model initialization.
        """
        super().__init__(**data)

    @field_validator("nameservers")
    @classmethod
    def validate_nameservers(cls, v):
        """Validate nameserver format."""
        if not v:
            raise ValueError("At least one nameserver must be provided")
        for ns in v:
            # Remove trailing dot for validation
            ns = ns.rstrip(".")
            if (
                not ns
                or ".." in ns
                or not all(part.isalnum() or part == "-" for part in ns.split("."))
            ):
                raise ValueError(f"Invalid nameserver format: {ns}")
        return v

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v):
        """Validate domain name."""
        if not v:
            raise ValueError("Domain name or ID is required")
        return v


class NameserverResponse(BaseModel):
    """Nameserver operation response model."""

    domain: str = Field(..., description="Domain name")
    nameservers: List[str] = Field(..., description="List of nameservers")
    updated: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last update timestamp",
    )
    status: str = Field(..., description="Operation status")

    model_config = ConfigDict(extra="allow")


class DomainAvailabilityRequest(BaseModel):
    """Domain availability check request model."""

    domain: str = Field(..., description="Domain name to check")
    check_premium: bool = Field(False, description="Check if domain is premium")

    model_config = ConfigDict(extra="allow")

    @field_validator("domain")
    def validate_domain(cls, v: str) -> str:
        """Validate domain name format."""
        if not v or not isinstance(v, str):
            raise ValueError("Domain name must be a non-empty string")
        return v.lower()


class TLDInfo(BaseModel):
    """TLD information model."""

    name: str = Field(..., description="TLD name (e.g., 'com', 'net', 'org')")
    available: bool = Field(
        True, description="Whether the TLD is available for registration"
    )
    price: Optional[float] = Field(None, description="Base registration price")
    currency: Optional[str] = Field(None, description="Currency for the price")
    restrictions: Optional[str] = Field(
        None, description="Any registration restrictions"
    )

    model_config = ConfigDict(extra="allow")


class TLDListResponse(BaseModel):
    """Response model for TLD listing."""

    tlds: List[TLDInfo] = Field(default_factory=list)
    total: int = Field(..., description="Total number of TLDs")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of the response",
    )

    model_config = ConfigDict(extra="allow")


class BulkDomainListResponse(BaseModel):
    """Response model for bulk domain listing."""

    domains: List[DomainInfo] = Field(default_factory=list)
    total: int = Field(..., description="Total number of domains")
    page: int = Field(1, description="Current page number")
    per_page: int = Field(20, description="Items per page")
    has_more: bool = Field(False, description="Whether there are more pages")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of the response",
    )

    model_config = ConfigDict(extra="allow")
