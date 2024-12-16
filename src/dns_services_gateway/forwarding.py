"""DNS Forwarding rules management for DNS Services Gateway.

This module provides functionality for managing DNS forwarding rules, including
creation, validation, and management of forwarding configurations.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
import ipaddress

from .exceptions import APIError
from .client import DNSServicesClient


class ForwardingTarget(BaseModel):
    """Model representing a DNS forwarding target."""

    address: str = Field(..., description="IP address of the target DNS server")
    port: int = Field(53, description="Port number of the target DNS server")
    protocol: str = Field("udp", description="Protocol to use (udp/tcp)")
    tls: bool = Field(False, description="Whether to use DNS over TLS")
    tls_hostname: Optional[str] = Field(
        None, description="TLS hostname for verification"
    )

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        """Validate IP address format."""
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            raise ValueError("Invalid IP address format")

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate port number."""
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v

    @field_validator("protocol")
    @classmethod
    def validate_protocol(cls, v: str) -> str:
        """Validate protocol."""
        if v.lower() not in ["udp", "tcp"]:
            raise ValueError("Protocol must be either 'udp' or 'tcp'")
        return v.lower()


class ForwardingRule(BaseModel):
    """Model representing a DNS forwarding rule."""

    domain: str = Field(..., description="Domain pattern to match for forwarding")
    targets: List[ForwardingTarget] = Field(
        ..., description="List of forwarding targets"
    )
    enabled: bool = Field(True, description="Whether the rule is enabled")
    priority: int = Field(
        0, description="Rule priority (higher numbers = higher priority)"
    )
    description: Optional[str] = Field(None, description="Rule description")

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        """Validate domain pattern."""
        if not v or not isinstance(v, str):
            raise ValueError("Domain pattern must be a non-empty string")
        if v.startswith("."):
            raise ValueError("Domain pattern cannot start with a dot")
        return v.lower()


class ForwardingResponse(BaseModel):
    """Model representing a forwarding operation response."""

    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    rules: Optional[List[ForwardingRule]] = Field(
        None, description="List of forwarding rules"
    )


class ForwardingManager:
    """Manager class for DNS forwarding operations."""

    def __init__(self, client: DNSServicesClient):
        """Initialize the forwarding manager.

        Args:
            client: The DNS Services client instance
        """
        self.client = client

    async def list_rules(self) -> ForwardingResponse:
        """List all DNS forwarding rules."""
        try:
            response = await self.client.get("/forwarding/rules")
            rules = [ForwardingRule(**rule) for rule in response.get("rules", [])]
            return ForwardingResponse(
                success=True,
                message="Successfully retrieved forwarding rules",
                rules=rules,
            )
        except APIError as e:
            raise

    async def add_rule(self, rule: ForwardingRule) -> ForwardingRule:
        """Add a new forwarding rule."""
        try:
            data = rule.model_dump()
            response = await self.client.post("/forwarding/rules", data=data)
            return ForwardingRule(**response["rule"])
        except APIError as e:
            raise

    async def update_rule(self, domain: str, rule: ForwardingRule) -> ForwardingRule:
        """Update an existing forwarding rule."""
        try:
            data = rule.model_dump()
            response = await self.client.put(f"/forwarding/rules/{domain}", data=data)
            return ForwardingRule(**response["rule"])
        except APIError as e:
            raise

    async def delete_rule(self, domain: str) -> ForwardingResponse:
        """Delete a DNS forwarding rule."""
        try:
            await self.client.delete(f"/forwarding/rules/{domain}")
            return ForwardingResponse(
                success=True, message="Successfully deleted forwarding rule", rules=None
            )
        except APIError as e:
            raise

    async def validate_rule(self, rule: ForwardingRule) -> ForwardingResponse:
        """Validate a forwarding rule."""
        try:
            data = rule.model_dump()
            await self.client.post("/forwarding/validate", data=data)
            return ForwardingResponse(
                success=True, message="Rule validation successful", rules=None
            )
        except APIError as e:
            raise
