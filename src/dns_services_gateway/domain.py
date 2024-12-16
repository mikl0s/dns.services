"""Domain operations for DNS Services Gateway."""

import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Union
from .models import (
    DomainInfo,
    OperationResponse,
    DomainAvailabilityRequest,
    DomainAvailabilityResponse,
    TLDInfo,
    TLDListResponse,
    BulkDomainListResponse,
    DNSRecord,
)
from .exceptions import APIError, ValidationError, DomainError


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
        """List all domains with metadata."""
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
                # Ensure required fields are present
                if "domain" in domain_data:
                    domain_data["name"] = domain_data.pop("domain")
                if "domain_id" in domain_data:
                    domain_data["id"] = domain_data.pop("domain_id")
                elif "name" in domain_data and "id" not in domain_data:
                    domain_data["id"] = domain_data["name"]

                # Handle expiration date
                if "expires_at" in domain_data:
                    domain_data["expires"] = datetime.fromisoformat(
                        domain_data["expires_at"]
                    )
                elif "expires" in domain_data and isinstance(
                    domain_data["expires"], str
                ):
                    domain_data["expires"] = datetime.fromisoformat(
                        domain_data["expires"]
                    )

                # Handle metadata and registrar
                metadata = domain_data.get("metadata", {})
                if include_metadata and "registrar" in metadata:
                    domain_data["registrar"] = metadata["registrar"]
                elif "registrar" not in domain_data:
                    domain_data["registrar"] = None

                # Ensure required fields have defaults if missing
                if "status" not in domain_data:
                    domain_data["status"] = "unknown"

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

    async def get_domain_details(self, domain: str) -> OperationResponse:
        """Get detailed information about a domain.

        Args:
            domain: Domain name

        Returns:
            OperationResponse containing domain details

        Raises:
            APIError: If the API request fails
        """
        try:
            response = await self._client.get(f"/domain/{domain}")
            return OperationResponse(
                status="success",
                operation="read",
                data={"domain": response},
                metadata={"domain_name": domain},
            )
        except Exception as e:
            raise APIError(f"Failed to get domain details: {str(e)}") from e

    async def verify_domain(self, domain: str) -> OperationResponse:
        """Verify domain ownership.

        Args:
            domain: Domain name to verify

        Returns:
            OperationResponse with verification status

        Raises:
            APIError: If verification fails
        """
        try:
            response = await self._client.post(f"/domains/{domain}/verify")
            return OperationResponse(
                status="success",
                operation="verify",
                data={
                    "verification_result": {
                        "verified": response.get("verified", False),
                        "status": response.get("status", "unknown"),
                        "method": response.get("method"),
                    }
                },
                metadata={"domain_name": domain},
                timestamp=datetime.now(timezone.utc),
            )
        except Exception as e:
            raise APIError(f"Failed to verify domain: {str(e)}") from e

    async def get_domain_metadata(self, domain_name: str) -> OperationResponse:
        """Get domain metadata including registration status, expiration, etc.

        Args:
            domain_name: Name of the domain to fetch metadata for

        Returns:
            OperationResponse containing domain metadata

        Raises:
            APIError: If the API request fails
        """
        try:
            response = await self._client.get(f"/domains/{domain_name}/metadata")
            return OperationResponse(
                status="success",
                operation="read",
                data={"metadata": response},
                metadata={"domain_name": domain_name},
                timestamp=datetime.now(timezone.utc),
            )
        except Exception as e:
            raise APIError(f"Failed to get domain metadata: {str(e)}") from e

    async def check_domain_availability(
        self, domain: str, check_premium: bool = False
    ) -> DomainAvailabilityResponse:
        """Check domain name availability.

        Args:
            domain: Domain name to check
            check_premium: Whether to check if domain is premium

        Returns:
            DomainAvailabilityResponse with availability info

        Raises:
            APIError: If the API request fails
            ValueError: If domain name is invalid
        """
        if not domain:
            raise ValueError("Domain name is required")

        try:
            response = await self._client.get(
                "/domain/check",
                params={"domain": domain, "check_premium": str(check_premium).lower()},
            )

            # Convert response to proper types
            price = response.get("price")
            price = float(price) if price is not None else None
            premium = response.get("premium")
            premium = bool(premium) if premium is not None else None

            return DomainAvailabilityResponse(
                domain=domain,
                available=bool(response.get("available")),
                price=price,
                currency=(
                    str(response.get("currency", "USD")) if price is not None else None
                ),
                premium=premium,
                timestamp=datetime.now(timezone.utc),
            )
        except Exception as e:
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
            tlds = []
            for tld_data in response.get("tlds", []):
                tld_info = TLDInfo(
                    name=tld_data["name"],
                    available=tld_data.get("available", True),
                    price=tld_data.get("price"),
                    currency=tld_data.get("currency", "USD"),
                    restrictions=str(tld_data.get("restrictions", "")),
                )
                tlds.append(tld_info)

            return TLDListResponse(
                tlds=tlds,
                total=len(tlds),
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "query_time": response.get("query_time"),
                    "last_updated": response.get("last_updated"),
                },
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
            raise APIError(f"Failed to get registry lock status: {str(e)}")

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
            raise APIError(f"Failed to update registry lock: {str(e)}")

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

    async def list_dns_records(
        self, domain: str, record_type: Optional[str] = None
    ) -> OperationResponse:
        """List DNS records for a domain.

        Args:
            domain: Domain name to list records for
            record_type: Optional record type filter (e.g., 'A', 'AAAA', 'CNAME')

        Returns:
            OperationResponse containing list of DNS records
        """
        try:
            if record_type is None:
                response = await self._client.get(f"/domain/{domain}/dns")
            else:
                response = await self._client.get(
                    f"/domain/{domain}/dns", params={"type": record_type}
                )
            records = response.get("records", [])
            return OperationResponse(
                status="success",
                operation="list",
                data={"records": records},
                metadata={"domain_name": domain},
                timestamp=datetime.now(timezone.utc),
            )
        except Exception as e:
            raise APIError(f"Failed to list DNS records: {str(e)}") from e

    async def create_dns_record(
        self,
        domain: str,
        record_type: str,
        name: str,
        content: str,
        ttl: int = 3600,
        priority: Optional[int] = None,
    ) -> OperationResponse:
        """Create a new DNS record.

        Args:
            domain: Domain name
            record_type: DNS record type (e.g., A, AAAA, CNAME, MX)
            name: Record name (e.g., www, @)
            content: Record content (e.g., IP address, domain name)
            ttl: Time to live in seconds
            priority: Priority for MX records

        Returns:
            OperationResponse with created record data

        Raises:
            APIError: If the API request fails
            ValueError: If required fields are missing
        """
        if not all([domain, record_type, name, content]):
            raise ValueError("Missing required fields")

        data = {
            "type": record_type,
            "name": name,
            "content": content,
            "ttl": ttl,
        }
        if priority is not None:
            data["priority"] = priority

        try:
            response = await self._client.post(f"/domain/{domain}/dns", json=data)
            return OperationResponse(
                status="success", operation="create_dns_record", data=response
            )
        except Exception as e:
            raise APIError(f"Failed to create DNS record: {str(e)}") from e

    async def delete_dns_record(self, domain: str, record_id: int) -> OperationResponse:
        """Delete a DNS record.

        Args:
            domain: Domain name
            record_id: Record ID to delete

        Returns:
            OperationResponse indicating success/failure

        Raises:
            APIError: If the API request fails
        """
        try:
            response = await self._client.delete(f"/domain/{domain}/dns/{record_id}")
            return OperationResponse(
                status="success", operation="delete_dns_record", data=response
            )
        except Exception as e:
            raise APIError(f"Failed to delete DNS record: {str(e)}")

    async def batch_dns_operations(
        self, operations: List[Dict[str, Any]]
    ) -> List[OperationResponse]:
        """Perform multiple DNS operations in sequence.

        Args:
            operations: List of operations to perform
                Each operation should have:
                - action: "create" or "delete"
                - domain: Domain name
                - For create: record_data with type, name, content, ttl
                - For delete: record_id

        Returns:
            List of OperationResponse objects
        """
        if not operations:
            raise ValueError("No operations provided")

        responses = []
        for op in operations:
            action = op.get("action")
            domain = op.get("domain")

            if not domain:
                raise ValueError("Missing domain identifier")

            if action == "create":
                record_data = op.get("record_data")
                if not record_data:
                    raise ValueError("Missing record data")
                if not all(k in record_data for k in ["type", "name", "content"]):
                    raise ValueError("Missing required fields in record data")

                response = await self.create_dns_record(
                    domain,
                    record_data["type"],
                    record_data["name"],
                    record_data["content"],
                    record_data.get("ttl", 3600),
                    record_data.get("priority"),
                )
            elif action == "delete":
                record_id = op.get("record_id")
                if record_id is None:
                    raise ValueError("Missing record ID")
                response = await self.delete_dns_record(domain, record_id)
            else:
                raise ValueError("Invalid action")

            responses.append(response)

        return responses

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
        self, domain_identifier: str, nameservers: List[str]
    ) -> OperationResponse:
        """Update nameservers for a domain.

        Args:
            domain_identifier: Domain ID or name
            nameservers: List of nameserver hostnames

        Returns:
            OperationResponse indicating success or failure

        Raises:
            APIError: If the API request fails
            ValueError: If nameservers list is empty or invalid
        """
        if not nameservers:
            raise ValueError("Nameservers list cannot be empty")

        try:
            endpoint = f"/domain/{domain_identifier}/nameservers"
            response = await self._client.put(
                endpoint, json={"nameservers": nameservers}
            )

            # Ensure response is a dictionary with required fields
            if not isinstance(response, dict):
                response = {"nameservers": nameservers, "status": "success"}
            elif "nameservers" not in response:
                response["nameservers"] = nameservers
            elif "status" not in response:
                response["status"] = "success"

            return OperationResponse(
                status="success",
                operation="update_nameservers",
                data=response,
                timestamp=datetime.now(timezone.utc),
                metadata={"domain": domain_identifier, "nameservers": nameservers},
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

    async def create_domain(self, domain_name: str, **kwargs) -> DomainInfo:
        """Create a new domain."""
        try:
            response = await self._client.post(
                "/domains", json={"domain": domain_name, **kwargs}
            )
            # Ensure the response has required fields
            if "domain" in response:
                response["name"] = response.pop("domain")
            if "id" not in response:
                response["id"] = domain_name
            return DomainInfo(**response)
        except Exception as e:
            if "Invalid" in str(e):
                raise ValidationError(str(e))
            raise APIError(f"Failed to create domain: {str(e)}")

    async def delete_domain(self, domain_identifier: str) -> Dict[str, str]:
        """Delete a domain."""
        try:
            response = await self._client.delete(f"/domains/{domain_identifier}")
            return response
        except Exception as e:
            raise APIError(f"Failed to delete domain: {str(e)}")

    async def get_domain_info(self, domain_identifier: str) -> DomainInfo:
        """Get detailed domain information.

        Args:
            domain_identifier: Domain ID or name to get info for

        Returns:
            DomainInfo object containing detailed domain information

        Raises:
            APIError: If the API request fails
            DomainError: If domain is not found
        """
        try:
            response = await self._client.get_domain(domain_identifier)
            if not response:
                raise APIError("Domain not found")
            return response
        except Exception as e:
            if "not found" in str(e).lower():
                raise APIError("Domain not found")
            raise APIError(f"Failed to get domain info: {str(e)}")

    async def update_domain(self, domain_id: str, **kwargs: Any) -> Dict[str, Any]:
        """Update domain settings.

        Args:
            domain_id: The ID of the domain to update
            **kwargs: Additional domain settings to update

        Returns:
            Dict containing updated domain information

        Raises:
            APIError: If the API request fails
            ValidationError: If the input parameters are invalid
        """
        try:
            response = await self._client.put(f"/domains/{domain_id}", json=kwargs)
            return response
        except Exception as e:
            raise APIError(f"Failed to update domain: {str(e)}") from e

    async def update_domain_nameservers(
        self, domain_id: str, nameservers: List[str]
    ) -> Dict[str, Any]:
        """Update nameservers for a domain.

        Args:
            domain_id: The ID of the domain
            nameservers: List of nameserver hostnames

        Returns:
            Dict containing updated nameserver information

        Raises:
            APIError: If the API request fails
            ValidationError: If the nameservers are invalid
        """
        try:
            response = await self._client.put(
                f"/domains/{domain_id}/nameservers", json={"nameservers": nameservers}
            )
            return response
        except Exception as e:
            raise APIError(f"Failed to update domain nameservers: {str(e)}") from e

    async def add_domain_record(
        self, domain_id: str, record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add a DNS record to a domain.

        Args:
            domain_id: The ID of the domain
            record: Record data including type, name, value, and optional parameters

        Returns:
            Dict containing the created record information

        Raises:
            APIError: If the API request fails
            ValidationError: If the record parameters are invalid
        """
        try:
            response = await self._client.post(
                f"/domains/{domain_id}/records", data=record
            )
            return response
        except Exception as e:
            if "validation" in str(e).lower():
                raise ValidationError(f"Invalid record data: {str(e)}")
            raise APIError(f"Failed to add domain record: {str(e)}")

    async def delete_domain_record(
        self, domain_id: str, record_id: str
    ) -> Dict[str, str]:
        """Delete a DNS record from a domain.

        Args:
            domain_id: The ID of the domain
            record_id: The ID of the record to delete

        Returns:
            Dict containing deletion status

        Raises:
            APIError: If the API request fails
        """
        try:
            await self._client.delete(f"/domains/{domain_id}/records/{record_id}")
            return {"status": "deleted"}
        except Exception as e:
            raise APIError(f"Failed to delete domain record: {str(e)}")

    async def delete_record(self, domain_id: str, record_id: str) -> bool:
        """Delete a DNS record from a domain.

        Args:
            domain_id: The ID of the domain
            record_id: The ID of the record to delete

        Returns:
            True if deletion was successful

        Raises:
            APIError: If the API request fails
        """
        try:
            return await self._client.delete_record(domain_id, record_id)
        except Exception as e:
            raise APIError(f"Failed to delete record: {str(e)}")

    async def add_record(
        self, domain_identifier: str, record_data: Dict[str, Any]
    ) -> DNSRecord:
        """Add a DNS record.

        Args:
            domain_identifier: Domain ID or name to add record to
            record_data: Record data including type, name, content, etc.

        Returns:
            DNSRecord object containing created record information

        Raises:
            APIError: If the API request fails
        """
        try:
            return await self._client.add_record(domain_identifier, record_data)
        except Exception as e:
            raise APIError(f"Failed to add DNS record: {str(e)}")

    async def get_domain_records(self, domain_identifier: str) -> Dict[str, Any]:
        """Get domain DNS records.

        Args:
            domain_identifier: Domain ID or name to get records for

        Returns:
            Dict containing DNS records

        Raises:
            APIError: If the API request fails
        """
        try:
            response = await self._client.get(f"/domains/{domain_identifier}/records")
            return response
        except Exception as e:
            raise APIError(f"Failed to get domain records: {str(e)}")

    async def get_domain_nameservers(self, domain_identifier: str) -> Dict[str, Any]:
        """Get domain nameservers.

        Args:
            domain_identifier: Domain ID or name to get nameservers for

        Returns:
            Dict containing nameserver information

        Raises:
            APIError: If the API request fails
        """
        try:
            response = await self._client.get(
                f"/domains/{domain_identifier}/nameservers"
            )
            return response
        except Exception as e:
            raise APIError(f"Failed to get domain nameservers: {str(e)}")

    async def get_domain_status(self, domain_identifier: str) -> str:
        """Get domain status.

        Args:
            domain_identifier: Domain ID or name to check status

        Returns:
            String containing domain status

        Raises:
            APIError: If the API request fails
        """
        try:
            response = await self._client.get(f"/domains/{domain_identifier}/status")
            return response.get("status")
        except Exception as e:
            raise APIError(f"Failed to get domain status: {str(e)}")

    async def list_domains_bulk(
        self, domains: List[str], include_metadata: bool = True
    ) -> List[DomainInfo]:
        """Get information for multiple domains.

        Args:
            domains: List of domain names
            include_metadata: Whether to include metadata

        Returns:
            List of DomainInfo objects
        """
        try:
            params = {
                "domains": ",".join(domains),
                "include_metadata": "1" if include_metadata else "0",
            }
            response = await self._client.get("/domains/bulk", params=params)
            domain_list = []

            for domain_data in response.get("domains", []):
                # Ensure registrar is properly set from metadata
                if "metadata" in domain_data:
                    registrar = domain_data["metadata"].get("registrar")
                    if registrar:
                        # Set registrar directly in the domain data
                        domain_data["registrar"] = registrar
                domain_info = DomainInfo.from_dict(domain_data)
                domain_list.append(domain_info)

            return domain_list
        except Exception as e:
            raise APIError(f"Failed to list domains in bulk: {str(e)}") from e

    async def error_handling_for_operations(self, domain: str) -> None:
        """Test error handling for various operations.

        Args:
            domain: Domain name to test with

        Raises:
            APIError: When API request fails
        """
        try:
            await self.get_registry_lock_status(domain)
        except Exception as e:
            raise APIError(f"Failed to get registry lock status: {str(e)}")

        try:
            await self.update_registry_lock(domain, True)
        except Exception as e:
            raise APIError(f"Failed to update registry lock: {str(e)}")

        try:
            await self.get_domain_forwarding(domain)
        except Exception as e:
            raise APIError(f"Failed to get domain forwarding: {str(e)}")

        try:
            await self.update_domain_forwarding(domain, "https://target.com")
        except Exception as e:
            raise APIError(f"Failed to update domain forwarding: {str(e)}")

        try:
            await self.create_dns_record(domain, "A", "www", "192.0.2.1")
        except Exception as e:
            raise APIError(f"Failed to create DNS record: {str(e)}")

        try:
            await self.delete_dns_record(domain, 1)
        except Exception as e:
            raise APIError(f"Failed to delete DNS record: {str(e)}")

        try:
            await self.list_dns_records(domain)
        except Exception as e:
            raise APIError(f"Failed to list DNS records: {str(e)}")

        try:
            await self.get_nameservers(domain)
        except Exception as e:
            raise APIError(f"Failed to get nameservers: {str(e)}")

        try:
            await self.update_nameservers(domain, ["ns1.example.com"])
        except Exception as e:
            raise APIError(f"Failed to update nameservers: {str(e)}")

        try:
            await self.register_nameservers(
                domain, [{"hostname": "ns1", "ip": "192.0.2.1"}]
            )
        except Exception as e:
            raise APIError(f"Failed to register nameservers: {str(e)}")

    async def get_domain(self, domain: str) -> Dict[str, Any]:
        """Get information about a specific domain.

        Args:
            domain: Domain name to get information for

        Returns:
            Dict containing domain information

        Raises:
            DomainError: If domain is not found
            APIError: If the API request fails
        """
        try:
            response = await self._client.get(f"/domains/{domain}")
            return response
        except DomainError as e:
            raise e
        except Exception as e:
            raise APIError(f"Failed to get domain information: {str(e)}") from e

    async def register_domain(
        self, domain: str, nameservers: Optional[List[str]] = None
    ) -> OperationResponse:
        """Register a new domain.

        Args:
            domain: Domain name to register
            nameservers: Optional list of nameservers to use

        Returns:
            OperationResponse containing registration status

        Raises:
            APIError: If the API request fails
        """
        try:
            data = {"domain": domain}
            if nameservers:
                data["nameservers"] = nameservers

            response = await self._client.post(f"/domain/{domain}/reg", json=data)
            return OperationResponse(
                status="success",
                operation="register_domain",
                data=response,
                timestamp=datetime.now(timezone.utc),
                metadata={"domain": domain, "nameservers": nameservers},
            )
        except Exception as e:
            raise APIError(f"Failed to register domain: {str(e)}") from e

    async def transfer_domain(self, domain: str, auth_code: str) -> OperationResponse:
        """Transfer a domain.

        Args:
            domain: Domain name to transfer
            auth_code: Authorization code for transfer

        Returns:
            OperationResponse containing transfer status

        Raises:
            APIError: If the API request fails
        """
        try:
            response = await self._client.post(
                f"/domain/{domain}/transfer", json={"auth_code": auth_code}
            )
            return OperationResponse(
                status="success",
                operation="transfer_domain",
                data=response,
                timestamp=datetime.now(timezone.utc),
                metadata={"domain": domain},
            )
        except Exception as e:
            raise APIError(f"Failed to transfer domain: {str(e)}") from e

    async def get_transfer_status(self, domain: str) -> str:
        """Get domain transfer status.

        Args:
            domain: Domain name to check transfer status

        Returns:
            String containing transfer status

        Raises:
            APIError: If the API request fails
        """
        try:
            response = await self._client.get(f"/domain/{domain}/transfer/status")
            return response.get("status", "unknown")
        except Exception as e:
            raise APIError(f"Failed to get transfer status: {str(e)}") from e

    async def cancel_transfer(self, domain: str) -> OperationResponse:
        """Cancel a domain transfer.

        Args:
            domain: Domain name to cancel transfer

        Returns:
            OperationResponse containing cancellation status

        Raises:
            APIError: If the API request fails
        """
        try:
            response = await self._client.delete(f"/domain/{domain}/transfer")
            return OperationResponse(
                status="success",
                operation="cancel_transfer",
                data=response,
                timestamp=datetime.now(timezone.utc),
                metadata={"domain": domain},
            )
        except Exception as e:
            raise APIError(f"Failed to cancel transfer: {str(e)}") from e

    async def get_auth_code(self, domain: str) -> str:
        """Get domain authorization code.

        Args:
            domain: Domain name to get auth code for

        Returns:
            String containing authorization code

        Raises:
            APIError: If the API request fails
        """
        try:
            response = await self._client.get(f"/domain/{domain}/authcode")
            return response.get("auth_code", "")
        except Exception as e:
            raise APIError(f"Failed to get auth code: {str(e)}") from e

    async def lock_domain(self, domain: str) -> OperationResponse:
        """Lock a domain.

        Args:
            domain: Domain name to lock

        Returns:
            OperationResponse containing lock status

        Raises:
            APIError: If the API request fails
        """
        try:
            response = await self._client.put(
                f"/domain/{domain}/reglock", json={"enabled": True}
            )
            return OperationResponse(
                status="success",
                operation="lock_domain",
                data=response,
                timestamp=datetime.now(timezone.utc),
                metadata={"domain": domain},
            )
        except Exception as e:
            raise APIError(f"Failed to lock domain: {str(e)}") from e

    async def unlock_domain(self, domain: str) -> OperationResponse:
        """Unlock a domain.

        Args:
            domain: Domain name to unlock

        Returns:
            OperationResponse containing unlock status

        Raises:
            APIError: If the API request fails
        """
        try:
            response = await self._client.put(
                f"/domain/{domain}/reglock", json={"enabled": False}
            )
            return OperationResponse(
                status="success",
                operation="unlock_domain",
                data=response,
                timestamp=datetime.now(timezone.utc),
                metadata={"domain": domain},
            )
        except Exception as e:
            raise APIError(f"Failed to unlock domain: {str(e)}") from e

    async def get_contacts(self, domain: str) -> Dict[str, Any]:
        """Get domain contact information.

        Args:
            domain: Domain name to get contacts for

        Returns:
            Dict containing contact information

        Raises:
            APIError: If the API request fails
        """
        try:
            response = await self._client.get(f"/domain/{domain}/contacts")
            return response.get("contacts", {})
        except Exception as e:
            raise APIError(f"Failed to get contacts: {str(e)}") from e

    async def update_contacts(
        self, domain: str, contacts: Dict[str, Any]
    ) -> OperationResponse:
        """Update domain contact information.

        Args:
            domain: Domain name to update contacts for
            contacts: Dict containing contact information

        Returns:
            OperationResponse containing update status

        Raises:
            APIError: If the API request fails
        """
        try:
            response = await self._client.put(
                f"/domain/{domain}/contacts", json={"contacts": contacts}
            )
            return OperationResponse(
                status="success",
                operation="update_contacts",
                data=response,
                timestamp=datetime.now(timezone.utc),
                metadata={"domain": domain},
            )
        except Exception as e:
            raise APIError(f"Failed to update contacts: {str(e)}") from e

    async def get_privacy_status(self, domain: str) -> bool:
        """Get domain privacy status.

        Args:
            domain: Domain name to get privacy status for

        Returns:
            Boolean indicating if privacy is enabled

        Raises:
            APIError: If the API request fails
        """
        try:
            response = await self._client.get(f"/domain/{domain}/privacy")
            return response.get("enabled", False)
        except Exception as e:
            raise APIError(f"Failed to get privacy status: {str(e)}") from e

    async def enable_privacy(self, domain: str) -> OperationResponse:
        """Enable domain privacy.

        Args:
            domain: Domain name to enable privacy for

        Returns:
            OperationResponse containing privacy status

        Raises:
            APIError: If the API request fails
        """
        try:
            response = await self._client.put(
                f"/domain/{domain}/privacy", json={"enabled": True}
            )
            return OperationResponse(
                status="success",
                operation="enable_privacy",
                data=response,
                timestamp=datetime.now(timezone.utc),
                metadata={"domain": domain},
            )
        except Exception as e:
            raise APIError(f"Failed to enable privacy: {str(e)}") from e

    async def disable_privacy(self, domain: str) -> OperationResponse:
        """Disable domain privacy.

        Args:
            domain: Domain name to disable privacy for

        Returns:
            OperationResponse containing privacy status

        Raises:
            APIError: If the API request fails
        """
        try:
            response = await self._client.put(
                f"/domain/{domain}/privacy", json={"enabled": False}
            )
            return OperationResponse(
                status="success",
                operation="disable_privacy",
                data=response,
                timestamp=datetime.now(timezone.utc),
                metadata={"domain": domain},
            )
        except Exception as e:
            raise APIError(f"Failed to disable privacy: {str(e)}") from e
