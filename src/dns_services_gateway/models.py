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
