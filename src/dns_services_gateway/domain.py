"""Domain operations for DNS Services Gateway."""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from .models import (
    DomainInfo,
    OperationResponse,
    DomainAvailabilityRequest,
    DomainAvailabilityResponse,
    TLDInfo,
    TLDListResponse,
    BulkDomainListResponse,
)
from .exceptions import APIError


class DomainOperations:
    """Domain operations handler."""

    def __init__(self, client) -> None:
        """Initialize domain operations.

        Args:
            client: DNSServicesClient instance
        """
        self._client = client

    async def list_domains(
        self,
        page: int = 1,
        per_page: int = 20,
        include_metadata: bool = True,
        filters: Optional[Dict[str, Any]] = None,
    ) -> BulkDomainListResponse:
        """List all domains with metadata.

        Args:
            page: Page number for pagination
            per_page: Number of items per page
            include_metadata: Whether to include detailed metadata
            filters: Optional filters to apply (e.g., status, expiring_within_days)

        Returns:
            BulkDomainListResponse containing list of domains with metadata

        Raises:
            APIError: If the API request fails
        """
        try:
            params = {
                "page": page,
                "per_page": per_page,
                "include_metadata": "1" if include_metadata else "0",
            }
            if filters:
                params.update(filters)

            response = await self._client.get("/domains/list", params=params)

            domains = []
            for domain_data in response.get("domains", []):
                # Extract expiration date if available
                if "expires_at" in domain_data:
                    domain_data["expires"] = datetime.fromisoformat(
                        domain_data["expires_at"]
                    )

                # Add domain metadata
                if include_metadata and "metadata" in domain_data:
                    domain_data.update(domain_data.pop("metadata"))

                domains.append(DomainInfo(**domain_data))

            return BulkDomainListResponse(
                domains=domains,
                total=response.get("total", len(domains)),
                page=page,
                per_page=per_page,
                has_more=response.get("has_more", False),
                metadata={
                    "query_time": response.get("query_time"),
                    "filtered": bool(filters),
                    "filter_criteria": filters,
                },
                timestamp=datetime.now(timezone.utc),
            )

        except Exception as e:
            raise APIError(f"Failed to list domains: {str(e)}") from e

    async def get_domain_details(self, domain_identifier: str) -> OperationResponse:
        """Get detailed information for a specific domain.

        Args:
            domain_identifier: Domain ID or domain name to fetch details for

        Returns:
            OperationResponse containing domain details including:
            - Domain registration status
            - Expiration dates
            - DNS configuration
            - Nameserver details

        Raises:
            APIError: If the API request fails
        """
        print("get_domain_details called")
        try:
            response = await self._client.get(f"/domain/{domain_identifier}")
            domain_info = DomainInfo(**response)

            return OperationResponse(
                status="success",
                operation="read",
                data={"domain": domain_info.model_dump()},
                metadata={
                    "domain_identifier": domain_identifier,
                    "retrieved_at": datetime.now(timezone.utc),
                },
            )
        except Exception as e:
            raise APIError(f"Failed to get domain details: {str(e)}")

    async def verify_domain(self, domain_name: str) -> OperationResponse:
        """Verify domain configuration and status.

        Args:
            domain_name: Name of the domain to verify

        Returns:
            OperationResponse containing verification results

        Raises:
            APIError: If the API request fails
        """
        print("verify_domain called")
        try:
            response = await self._client.post(f"/domains/{domain_name}/verify")

            return OperationResponse(
                status="success",
                operation="verify",
                data={"verification_result": response},
                metadata={"domain_name": domain_name},
            )
        except Exception as e:
            raise APIError(f"Failed to verify domain: {str(e)}")

    async def get_domain_metadata(self, domain_name: str) -> OperationResponse:
        """Get domain metadata including registration status, expiration, etc.

        Args:
            domain_name: Name of the domain to fetch metadata for

        Returns:
            OperationResponse containing domain metadata

        Raises:
            APIError: If the API request fails
        """
        print("get_domain_metadata called")
        try:
            response = await self._client.get(f"/domains/{domain_name}/metadata")

            return OperationResponse(
                status="success",
                operation="read",
                data={"metadata": response},
                metadata={"domain_name": domain_name},
            )
        except Exception as e:
            raise APIError(f"Failed to get domain metadata: {str(e)}")

    async def check_domain_availability(
        self, domain: str, check_premium: bool = False
    ) -> DomainAvailabilityResponse:
        """Check domain name availability.

        Args:
            domain: Domain name to check
            check_premium: Whether to check if domain is premium

        Returns:
            DomainAvailabilityResponse with availability status and pricing info

        Raises:
            APIError: If the API request fails
            ValueError: If domain name is invalid
        """
        try:
            request = DomainAvailabilityRequest(
                domain=domain,
                check_premium=check_premium,
            )

            response = await self._client.get(
                "/domain/check",
                params={
                    "domain": request.domain,
                    "check_premium": str(request.check_premium).lower(),
                },
            )

            return DomainAvailabilityResponse(
                domain=request.domain,
                available=response.get("available", False),
                premium=response.get("premium"),
                price=response.get("price"),
                currency=response.get("currency"),
            )

        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise APIError(f"Failed to check domain availability: {str(e)}") from e

    async def list_available_tlds(self) -> TLDListResponse:
        """List all available TLDs with pricing information.

        Returns:
            TLDListResponse containing list of available TLDs with metadata

        Raises:
            APIError: If the API request fails
        """
        try:
            response = await self._client.get("/tlds/available")
            tlds = [TLDInfo(**tld_data) for tld_data in response.get("tlds", [])]

            return TLDListResponse(
                tlds=tlds,
                total=len(tlds),
            )

        except Exception as e:
            raise APIError(f"Failed to list available TLDs: {str(e)}") from e
