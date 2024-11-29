"""Data models for DNS Services Gateway."""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator, ConfigDict


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


class OperationResponse(BaseModel):
    """API operation response model."""

    status: str = Field(..., description="Operation status (success/error)")
    operation: str = Field(
        ..., description="Operation type (create/read/update/delete)"
    )
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class DomainInfo(BaseModel):
    """Domain information model."""

    id: str = Field(..., description="Domain ID")
    name: str = Field(..., description="Domain name")
    status: str = Field(..., description="Domain status")
    expires: Optional[datetime] = Field(None, description="Expiration date")
    auto_renew: bool = Field(False, description="Auto-renewal status")
    nameservers: List[str] = Field(default_factory=list)
    records: List[DNSRecord] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class AuthResponse(BaseModel):
    """Authentication response model."""

    token: Optional[str] = None
    expires: Optional[datetime] = None
    refresh_token: Optional[str] = None
    expiration: Optional[str] = None

    model_config = ConfigDict(extra="allow")

    @field_validator("expires", mode="before")
    @classmethod
    def set_expiration(cls, v, info):
        """Set expiration to 1 hour from now if not provided."""
        if not v:
            # Check if expiration is provided in the raw data
            raw_data = info.data
            if "expiration" in raw_data:
                v = raw_data["expiration"]
                # Store the original expiration string
                info.data["expiration"] = v

        if isinstance(v, str):
            return datetime.fromisoformat(v).replace(microsecond=0)
        elif isinstance(v, datetime):
            return v.replace(microsecond=0)
        return datetime.now(timezone.utc).replace(microsecond=0) + timedelta(hours=1)


class NameserverUpdate(BaseModel):
    """Nameserver update request model."""

    domain: str = Field(..., description="Domain name or ID")
    nameservers: List[str] = Field(..., description="List of nameservers")
    perform_validation: bool = Field(True, description="Validate nameserver format")

    model_config = ConfigDict(extra="allow")

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v):
        """Validate domain name or ID."""
        if not v:
            raise ValueError("Domain name or ID is required")
        return v

    @field_validator("nameservers")
    @classmethod
    def validate_nameservers(cls, v):
        """Validate nameserver format."""
        if not v:
            raise ValueError("At least one nameserver must be provided")
        for ns in v:
            if not isinstance(ns, str) or not ns:
                raise ValueError("Invalid nameserver format")
            if not ns.lower().endswith("."):
                # Append trailing dot if missing
                ns = f"{ns}."
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


class DomainAvailabilityResponse(BaseModel):
    """Domain availability check response model."""

    domain: str = Field(..., description="Domain name checked")
    available: bool = Field(..., description="Whether the domain is available")
    premium: Optional[bool] = Field(None, description="Whether the domain is premium")
    price: Optional[float] = Field(None, description="Domain price if available")
    currency: Optional[str] = Field(None, description="Currency for the price")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of the check",
    )

    model_config = ConfigDict(extra="allow")


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
