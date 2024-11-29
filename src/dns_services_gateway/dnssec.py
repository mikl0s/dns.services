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
