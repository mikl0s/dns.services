"""DNSSEC Management functionality for DNS Services Gateway.

This module provides functionality for managing DNSSEC keys including listing,
adding, and removing DNSSEC keys for domains.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from .exceptions import APIError
from .client import DNSServicesClient


class DNSSECKey(BaseModel):
    """Model representing a DNSSEC key."""

    key_tag: int = Field(..., description="The key tag identifier")
    algorithm: int = Field(..., description="DNSSEC algorithm number")
    digest_type: int = Field(..., description="The digest type")
    digest: str = Field(..., description="The key digest")
    flags: Optional[int] = Field(None, description="Key flags")
    protocol: Optional[int] = Field(None, description="Protocol number")
    public_key: Optional[str] = Field(None, description="Public key data")


class DNSSECResponse(BaseModel):
    """Model representing a DNSSEC operation response."""

    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    keys: Optional[List[DNSSECKey]] = Field(None, description="List of DNSSEC keys")


class DNSSECKeyConfig(BaseModel):
    """Model representing DNSSEC key configuration."""

    algorithm: int = Field(..., description="DNSSEC algorithm number")
    key_size: int = Field(..., description="Key size in bits")
    rotation_interval: int = Field(..., description="Key rotation interval in days")
    signing_practice: str = Field(..., description="Key signing practice (KSK/ZSK)")


class DNSSECSigningConfig(BaseModel):
    """Model representing DNSSEC signing configuration."""

    enabled: bool = Field(..., description="Whether DNSSEC signing is enabled")
    auto_signing: bool = Field(..., description="Whether auto-signing is enabled")
    nsec3: bool = Field(False, description="Whether NSEC3 is enabled")
    nsec3_iterations: Optional[int] = Field(
        None, description="NSEC3 iterations if enabled"
    )
    nsec3_salt_length: Optional[int] = Field(
        None, description="NSEC3 salt length if enabled"
    )
    key_config: DNSSECKeyConfig = Field(..., description="Key configuration")


class DNSSECStatus(BaseModel):
    """Model representing DNSSEC status."""

    domain: str = Field(..., description="Domain name")
    is_signed: bool = Field(..., description="Whether the domain is DNSSEC signed")
    keys: List[DNSSECKey] = Field(
        default_factory=list, description="Active DNSSEC keys"
    )
    next_key_event: Optional[str] = Field(None, description="Next scheduled key event")
    ds_records: List[str] = Field(default_factory=list, description="DS records")
    validation_status: str = Field(..., description="DNSSEC validation status")
    last_signed: Optional[str] = Field(None, description="Last signing timestamp")


class DNSSECManager:
    """Manager class for DNSSEC operations."""

    def __init__(self, client: DNSServicesClient):
        """Initialize the DNSSEC manager.

        Args:
            client: The DNS Services client instance
        """
        self.client = client

    async def list_keys(self, domain: str) -> DNSSECResponse:
        """List all DNSSEC keys for a domain.

        Args:
            domain: The domain name to list DNSSEC keys for.

        Returns:
            DNSSECResponse containing the list of DNSSEC keys.

        Raises:
            APIError: If the API request fails.
        """
        try:
            response = await self.client.get(f"/domain/{domain}/dnssec")  # type: ignore
            keys = [DNSSECKey(**key_data) for key_data in response.get("keys", [])]
            return DNSSECResponse(
                success=True, message="Successfully retrieved DNSSEC keys", keys=keys
            )
        except APIError as e:
            return DNSSECResponse(success=False, message=str(e), keys=None)

    async def add_key(
        self, domain: str, algorithm: int, public_key: str, flags: Optional[int] = None
    ) -> DNSSECResponse:
        """Add a new DNSSEC key to a domain.

        Args:
            domain: The domain name to add the DNSSEC key to.
            algorithm: DNSSEC algorithm number.
            public_key: The public key data.
            flags: Optional key flags.

        Returns:
            DNSSECResponse containing the operation result.

        Raises:
            APIError: If the API request fails.
        """
        data = {"algorithm": algorithm, "public_key": public_key}
        if flags is not None:
            data["flags"] = flags

        try:
            response = await self.client.post(  # type: ignore
                f"/domain/{domain}/dnssec", data=data
            )
            return DNSSECResponse(
                success=True,
                message="Successfully added DNSSEC key",
                keys=[DNSSECKey(**response["key"])] if "key" in response else None,
            )
        except APIError as e:
            return DNSSECResponse(success=False, message=str(e), keys=None)

    async def remove_key(self, domain: str, key_tag: int) -> DNSSECResponse:
        """Remove a DNSSEC key from a domain.

        Args:
            domain: The domain name to remove the DNSSEC key from.
            key_tag: The key tag identifier of the key to remove.

        Returns:
            DNSSECResponse containing the operation result.

        Raises:
            APIError: If the API request fails.
        """
        try:
            await self.client.delete(  # type: ignore
                f"/domain/{domain}/dnssec/{key_tag}"
            )
            return DNSSECResponse(
                success=True,
                message=f"Successfully removed DNSSEC key {key_tag}",
                keys=None,
            )
        except APIError as e:
            return DNSSECResponse(success=False, message=str(e), keys=None)

    async def generate_key(self, domain: str, config: DNSSECKeyConfig) -> DNSSECKey:
        """Generate a new DNSSEC key for a domain."""
        try:
            data = config.model_dump()
            response = await self.client.post(
                f"/domain/{domain}/dnssec/generate", data=data
            )
            return DNSSECKey(**response["key"])
        except APIError as e:
            raise APIError(str(e))

    async def rotate_keys(self, domain: str) -> DNSSECResponse:
        """Rotate DNSSEC keys for a domain.

        Args:
            domain: The domain name to rotate keys for

        Returns:
            DNSSECResponse containing the operation result
        """
        try:
            response = await self.client.post(  # type: ignore
                f"/domain/{domain}/dnssec/rotate"
            )
            return DNSSECResponse(
                success=True,
                message="Successfully rotated DNSSEC keys",
                keys=[DNSSECKey(**key) for key in response.get("keys", [])],
            )
        except APIError as e:
            return DNSSECResponse(success=False, message=str(e), keys=None)

    async def manage_ds_records(
        self, domain: str, operation: str, records: List[str]
    ) -> DNSSECResponse:
        """Manage DS records for a domain.

        Args:
            domain: The domain name
            operation: Operation to perform ('add' or 'remove')
            records: List of DS records

        Returns:
            DNSSECResponse containing the operation result
        """
        try:
            data = {"operation": operation, "records": records}
            response = await self.client.post(  # type: ignore
                f"/domain/{domain}/dnssec/ds", data=data
            )
            return DNSSECResponse(
                success=True,
                message=f"Successfully {operation}ed DS records",
                keys=None,
            )
        except APIError as e:
            return DNSSECResponse(success=False, message=str(e), keys=None)

    async def configure_signing(self, domain: str, config: DNSSECSigningConfig) -> bool:
        """Configure DNSSEC signing for a domain."""
        try:
            data = config.model_dump()
            response = await self.client.put(
                f"/domain/{domain}/dnssec/signing", data=data
            )
            return True
        except APIError as e:
            raise APIError(str(e))

    async def get_status(self, domain: str) -> DNSSECStatus:
        """Get DNSSEC status for a domain.

        Args:
            domain: The domain name

        Returns:
            DNSSECStatus containing the current DNSSEC status

        Raises:
            APIError: If the API request fails
        """
        response = await self.client.get(f"/domain/{domain}/dnssec/status")  # type: ignore
        return DNSSECStatus(**response)
