"""Domain operations for DNS Services Gateway."""

from .models import DomainInfo, OperationResponse
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
        self, page: int = 1, per_page: int = 20
    ) -> OperationResponse:
        """List all domains with metadata.

        Args:
            page: Page number for pagination
            per_page: Number of items per page

        Returns:
            OperationResponse containing list of domains with metadata

        Raises:
            APIError: If the API request fails
        """
        print("list_domains called")
        try:
            response = await self._client.get(
                "/domains", params={"page": page, "per_page": per_page}
            )
            domains = [DomainInfo(**domain) for domain in response.get("domains", [])]

            return OperationResponse(
                status="success",
                operation="read",
                data={"domains": [domain.model_dump() for domain in domains]},
                metadata={
                    "total": response.get("total", 0),
                    "page": page,
                    "per_page": per_page,
                },
            )
        except Exception as e:
            raise APIError(f"Failed to list domains: {str(e)}")

    async def get_domain_details(self, domain_name: str) -> OperationResponse:
        """Get detailed information for a specific domain.

        Args:
            domain_name: Name of the domain to fetch details for

        Returns:
            OperationResponse containing domain details

        Raises:
            APIError: If the API request fails
        """
        print("get_domain_details called")
        try:
            response = await self._client.get(f"/domains/{domain_name}")
            domain_info = DomainInfo(**response)

            return OperationResponse(
                status="success",
                operation="read",
                data={"domain": domain_info.model_dump()},
                metadata={"domain_name": domain_name},
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
