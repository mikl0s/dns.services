"""DNS Services Gateway nameserver management module."""

from datetime import datetime, timezone
from typing import List, Optional
from pydantic import ValidationError as PydanticValidationError

from .models import NameserverUpdate, NameserverResponse, OperationResponse
from .exceptions import (
    DNSServicesError,
    ValidationError,
)


class NameserverManager:
    """Manages domain nameserver operations."""

    def __init__(self, client):
        """Initialize nameserver manager.

        Args:
            client: DNS Services Gateway client instance
        """
        self._client = client

    async def get_nameservers(self, domain: str) -> NameserverResponse:
        """Get nameservers for a domain.

        Args:
            domain: Domain name or ID

        Returns:
            NameserverResponse: Current nameserver configuration

        Raises:
            ValidationError: If domain format is invalid
            DNSServicesError: If API request fails
        """
        if not domain:
            raise ValidationError("Domain name or ID is required")

        try:
            response = await self._client.get(f"domain/{domain}/nameservers")
            return NameserverResponse(
                domain=domain,
                nameservers=response.get("nameservers", []),
                status="success",
                updated=datetime.now(timezone.utc),
            )
        except Exception as e:
            raise DNSServicesError(f"Failed to get nameservers: {str(e)}") from e

    async def update_nameservers(
        self, domain: str, nameservers: List[str], validate: bool = True
    ) -> OperationResponse:
        """Update nameservers for a domain.

        Args:
            domain: Domain name or ID
            nameservers: List of nameservers
            validate: Whether to validate nameserver format

        Returns:
            OperationResponse: Update operation result

        Raises:
            ValidationError: If domain or nameserver format is invalid
            DNSServicesError: If API request fails
        """
        if not domain:
            raise ValidationError("Domain name or ID is required")

        try:
            update = NameserverUpdate(
                domain=domain,
                nameservers=nameservers,
                perform_validation=validate,
            )
        except PydanticValidationError as e:
            raise ValidationError(str(e)) from e

        try:
            response = await self._client.put(
                f"domain/{domain}/nameservers",
                json={"nameservers": update.nameservers},
            )
            return OperationResponse(
                status="success",
                operation="update",
                data={
                    "before": response.get("previous_nameservers", []),
                    "after": update.nameservers,
                    "verified": response.get("verified", False),
                },
                metadata={
                    "domain": domain,
                    "nameservers": update.nameservers,
                    "validate": validate,
                },
            )
        except Exception as e:
            raise DNSServicesError(f"Failed to update nameservers: {str(e)}") from e

    async def verify_nameservers(
        self, domain: str, nameservers: Optional[List[str]] = None
    ) -> bool:
        """Verify nameserver configuration for a domain.

        Args:
            domain: Domain name or ID
            nameservers: Optional list of nameservers to verify against.
                        If not provided, verifies current nameservers.

        Returns:
            bool: True if nameservers are correctly configured

        Raises:
            ValidationError: If domain format is invalid
            DNSServicesError: If API request fails
        """
        try:
            current = await self.get_nameservers(domain)
            if nameservers is None:
                nameservers = current.nameservers

            response = await self._client.post(
                f"domain/{domain}/nameservers/verify",
                json={"nameservers": nameservers},
            )
            return response.get("verified", False)
        except Exception as e:
            raise DNSServicesError(f"Failed to verify nameservers: {str(e)}") from e
