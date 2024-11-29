"""Domain operations for DNS Services Gateway."""

import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
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

    async def get_registry_lock_status(
        self, domain_identifier: str
    ) -> OperationResponse:
        """Get registry lock status for a domain.

        Args:
            domain_identifier: Domain ID or name to check registry lock status

        Returns:
            OperationResponse containing registry lock status

        Raises:
            APIError: If the API request fails
        """
        try:
            response = await self._client.get(f"/domain/{domain_identifier}/reglock")
            return OperationResponse(
                status="success",
                operation="get_registry_lock_status",
                data=response,
                timestamp=datetime.now(timezone.utc),
                metadata={"domain": domain_identifier},
            )
        except Exception as e:
            raise APIError(f"Failed to get registry lock status: {str(e)}") from e

    async def update_registry_lock(
        self, domain_identifier: str, enabled: bool
    ) -> OperationResponse:
        """Update registry lock status for a domain.

        Args:
            domain_identifier: Domain ID or name to update registry lock
            enabled: Whether to enable or disable registry lock

        Returns:
            OperationResponse containing updated registry lock status

        Raises:
            APIError: If the API request fails
        """
        try:
            response = await self._client.put(
                f"/domain/{domain_identifier}/reglock",
                json={"enabled": enabled},
            )
            return OperationResponse(
                status="success",
                operation="update_registry_lock",
                data=response,
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "domain": domain_identifier,
                    "enabled": enabled,
                },
            )
        except Exception as e:
            raise APIError(f"Failed to update registry lock: {str(e)}") from e

    async def get_domain_forwarding(self, domain_identifier: str) -> OperationResponse:
        """Get domain forwarding configuration.

        Args:
            domain_identifier: Domain ID or name to get forwarding config

        Returns:
            OperationResponse containing domain forwarding configuration

        Raises:
            APIError: If the API request fails
        """
        try:
            response = await self._client.get(f"/domain/{domain_identifier}/forwarding")
            return OperationResponse(
                status="success",
                operation="get_domain_forwarding",
                data=response,
                timestamp=datetime.now(timezone.utc),
                metadata={"domain": domain_identifier},
            )
        except Exception as e:
            raise APIError(f"Failed to get domain forwarding: {str(e)}") from e

    async def update_domain_forwarding(
        self,
        domain_identifier: str,
        target_url: str,
        preserve_path: bool = True,
        include_query: bool = True,
    ) -> OperationResponse:
        """Update domain forwarding configuration.

        Args:
            domain_identifier: Domain ID or name to update forwarding
            target_url: URL to forward the domain to
            preserve_path: Whether to preserve the path when forwarding
            include_query: Whether to include query parameters when forwarding

        Returns:
            OperationResponse containing updated forwarding configuration

        Raises:
            APIError: If the API request fails
        """
        try:
            response = await self._client.put(
                f"/domain/{domain_identifier}/forwarding",
                json={
                    "target_url": target_url,
                    "preserve_path": preserve_path,
                    "include_query": include_query,
                },
            )
            return OperationResponse(
                status="success",
                operation="update_domain_forwarding",
                data=response,
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "domain": domain_identifier,
                    "target_url": target_url,
                    "preserve_path": preserve_path,
                    "include_query": include_query,
                },
            )
        except Exception as e:
            raise APIError(f"Failed to update domain forwarding: {str(e)}") from e

    async def create_dns_record(
        self,
        domain_identifier: str,
        record_type: str,
        name: str,
        value: str,
        ttl: int = 3600,
        priority: Optional[int] = None,
    ) -> OperationResponse:
        """Create a new DNS record for a domain.

        Args:
            domain_identifier: Domain ID or name to add the record to
            record_type: Type of DNS record (A, AAAA, CNAME, MX, TXT)
            name: Record name (e.g., www, @)
            value: Record value (e.g., IP address, domain name)
            ttl: Time to live in seconds (default: 3600)
            priority: Priority for MX records (optional)

        Returns:
            OperationResponse containing the created record details

        Raises:
            APIError: If the API request fails
        """
        try:
            data = {
                "type": record_type.upper(),
                "name": name,
                "value": value,
                "ttl": ttl,
            }
            if priority is not None and record_type.upper() == "MX":
                data["priority"] = priority

            response = await self._client.post(
                f"/domain/{domain_identifier}/dns",
                json=data,
            )
            return OperationResponse(
                status="success",
                operation="create_dns_record",
                data=response,
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "domain": domain_identifier,
                    "record_type": record_type,
                    "name": name,
                    "ttl": ttl,
                },
            )
        except Exception as e:
            raise APIError(f"Failed to create DNS record: {str(e)}") from e

    async def delete_dns_record(
        self,
        domain_identifier: str,
        record_index: int,
    ) -> OperationResponse:
        """Delete a DNS record from a domain.

        Args:
            domain_identifier: Domain ID or name to delete the record from
            record_index: Index of the record to delete

        Returns:
            OperationResponse containing the deletion status

        Raises:
            APIError: If the API request fails
        """
        try:
            response = await self._client.delete(
                f"/domain/{domain_identifier}/dns/{record_index}",
            )
            return OperationResponse(
                status="success",
                operation="delete_dns_record",
                data=response,
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "domain": domain_identifier,
                    "record_index": record_index,
                },
            )
        except Exception as e:
            raise APIError(f"Failed to delete DNS record: {str(e)}") from e

    async def batch_dns_operations(
        self,
        operations: List[Dict[str, Any]],
    ) -> List[OperationResponse]:
        """Perform multiple DNS operations in parallel.

        Args:
            operations: List of operations, each containing:
                - action: create, update, or delete
                - domain: domain identifier
                - record_data: record details for create/update

        Returns:
            List of OperationResponse objects for each operation

        Raises:
            APIError: If any operation fails
        """

        async def execute_operation(op: Dict[str, Any]) -> OperationResponse:
            action = op["action"].lower()
            domain = op["domain"]
            if action == "create":
                return await self.create_dns_record(
                    domain_identifier=domain,
                    **op["record_data"],
                )
            elif action == "delete":
                return await self.delete_dns_record(
                    domain_identifier=domain,
                    record_index=op["record_index"],
                )
            else:
                raise APIError(f"Unsupported action: {action}")

        try:
            tasks = [execute_operation(op) for op in operations]
            results = await asyncio.gather(*tasks)
            return [
                result
                if isinstance(result, OperationResponse)
                else OperationResponse(
                    status="error",
                    operation="batch_dns_operations",
                    data={"error": str(result)},
                    timestamp=datetime.now(timezone.utc),
                    metadata={"failed_operation": operations[i]},
                )
                for i, result in enumerate(results)
            ]
        except Exception as e:
            raise APIError(f"Batch DNS operations failed: {str(e)}") from e

    async def list_dns_records(
        self,
        domain_identifier: str,
        record_type: Optional[str] = None,
    ) -> OperationResponse:
        """List all DNS records for a domain.

        Args:
            domain_identifier: Domain ID or name to list records for
            record_type: Optional filter by record type (A, AAAA, CNAME, MX, TXT)

        Returns:
            OperationResponse containing list of DNS records

        Raises:
            APIError: If the API request fails
        """
        try:
            params = {}
            if record_type:
                params["type"] = record_type.upper()

            response = await self._client.get(
                f"/domain/{domain_identifier}/dns",
                params=params,
            )
            return OperationResponse(
                status="success",
                operation="list_dns_records",
                data=response,
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "domain": domain_identifier,
                    "record_type_filter": record_type,
                },
            )
        except Exception as e:
            raise APIError(f"Failed to list DNS records: {str(e)}") from e

    async def get_nameservers(self, domain_identifier: str) -> OperationResponse:
        """Get nameservers for a domain.

        Args:
            domain_identifier: Domain ID or name to get nameservers for

        Returns:
            OperationResponse containing nameserver information

        Raises:
            APIError: If the API request fails
        """
        try:
            response = await self._client.get(
                f"/domain/{domain_identifier}/nameservers",
            )
            return OperationResponse(
                status="success",
                operation="get_nameservers",
                data=response,
                timestamp=datetime.now(timezone.utc),
                metadata={"domain": domain_identifier},
            )
        except Exception as e:
            raise APIError(f"Failed to get nameservers: {str(e)}") from e

    async def update_nameservers(
        self,
        domain_identifier: str,
        nameservers: List[str],
    ) -> OperationResponse:
        """Update nameservers for a domain.

        Args:
            domain_identifier: Domain ID or name to update nameservers for
            nameservers: List of nameserver hostnames

        Returns:
            OperationResponse containing updated nameserver information

        Raises:
            APIError: If the API request fails
        """
        try:
            response = await self._client.put(
                f"/domain/{domain_identifier}/nameservers",
                json={"nameservers": nameservers},
            )
            return OperationResponse(
                status="success",
                operation="update_nameservers",
                data=response,
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "domain": domain_identifier,
                    "nameservers": nameservers,
                },
            )
        except Exception as e:
            raise APIError(f"Failed to update nameservers: {str(e)}") from e

    async def register_nameservers(
        self,
        domain_identifier: str,
        nameservers: List[Dict[str, str]],
    ) -> OperationResponse:
        """Register nameservers for a domain.

        Args:
            domain_identifier: Domain ID or name to register nameservers for
            nameservers: List of nameserver configurations, each containing:
                - hostname: Nameserver hostname
                - ip: IP address for the nameserver

        Returns:
            OperationResponse containing registration status

        Raises:
            APIError: If the API request fails
        """
        try:
            response = await self._client.post(
                f"/domain/{domain_identifier}/nameservers/register",
                json={"nameservers": nameservers},
            )
            return OperationResponse(
                status="success",
                operation="register_nameservers",
                data=response,
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "domain": domain_identifier,
                    "nameservers": nameservers,
                },
            )
        except Exception as e:
            raise APIError(f"Failed to register nameservers: {str(e)}") from e
