"""Data models for DNS Services Gateway."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class DNSRecord(BaseModel):
    """DNS record model."""

    id: str = Field(..., description="Record ID")
    type: str = Field(..., description="Record type (A, AAAA, CNAME, TXT, etc.)")
    name: str = Field(..., description="Record name/hostname")
    content: str = Field(..., description="Record content/value")
    ttl: int = Field(3600, description="Time to live in seconds")
    priority: Optional[int] = Field(None, description="Record priority (MX, SRV)")
    proxied: bool = Field(False, description="Whether the record is proxied")


class OperationResponse(BaseModel):
    """API operation response model."""

    status: str = Field(..., description="Operation status (success/error)")
    operation: str = Field(..., description="Operation type (create/read/update/delete)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DomainInfo(BaseModel):
    """Domain information model."""

    id: str = Field(..., description="Domain ID")
    name: str = Field(..., description="Domain name")
    status: str = Field(..., description="Domain status")
    expires: Optional[datetime] = Field(None, description="Expiration date")
    auto_renew: bool = Field(False, description="Auto-renewal status")
    nameservers: List[str] = Field(default_factory=list)
    records: List[DNSRecord] = Field(default_factory=list)


class AuthResponse(BaseModel):
    """Authentication response model."""

    token: str = Field(..., description="JWT token")
    expires: datetime = Field(..., description="Token expiration timestamp")
    refresh_token: Optional[str] = Field(None, description="Refresh token if available")
