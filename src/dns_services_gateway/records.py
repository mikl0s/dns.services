"""DNS record management module for DNS Services Gateway.

This module provides a unified interface for managing DNS records through the DNS
Services Gateway. It supports CRUD operations for all standard DNS record types
and includes verification mechanisms.
"""

from typing import Dict, Any, List, Literal, Optional, Union
from datetime import datetime, timezone
from enum import Enum
import asyncio

from pydantic import BaseModel, Field, field_validator


class RecordType(str, Enum):
    """Supported DNS record types."""

    A = "A"
    AAAA = "AAAA"
    CNAME = "CNAME"
    MX = "MX"
    TXT = "TXT"
    NS = "NS"
    SRV = "SRV"
    CAA = "CAA"


class RecordAction(str, Enum):
    """Available actions for record management."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class BaseRecord(BaseModel):
    """Base model for all DNS record types."""

    name: str = Field(..., description="Record name (e.g., @ for root, subdomain, etc)")
    type: RecordType
    ttl: int = Field(default=3600, ge=60, description="Time to live in seconds")


class ARecord(BaseRecord):
    """Model for A record type."""

    type: Literal[RecordType.A] = RecordType.A
    value: str = Field(..., description="IPv4 address")

    @field_validator("value")
    @classmethod
    def validate_ipv4(cls, v: str) -> str:
        """Validate IPv4 address format."""
        # Basic IPv4 validation - could be enhanced
        parts = v.split(".")
        if len(parts) != 4 or not all(
            p.isdigit() and 0 <= int(p) <= 255 for p in parts
        ):
            raise ValueError("Invalid IPv4 address")
        return v


class AAAARecord(BaseRecord):
    """Model for AAAA record type."""

    type: Literal[RecordType.AAAA] = RecordType.AAAA
    value: str = Field(..., description="IPv6 address")


class CNAMERecord(BaseRecord):
    """Model for CNAME record type."""

    type: Literal[RecordType.CNAME] = RecordType.CNAME
    value: str = Field(..., description="Target hostname")


class MXRecord(BaseRecord):
    """Model for MX record type."""

    type: Literal[RecordType.MX] = RecordType.MX
    value: str = Field(..., description="Mail server hostname")
    priority: int = Field(..., ge=0, le=65535, description="Priority value")


class TXTRecord(BaseRecord):
    """Model for TXT record type."""

    type: Literal[RecordType.TXT] = RecordType.TXT
    value: str = Field(..., description="Text value")


class RecordOperation(BaseModel):
    """Model for batch record operations."""

    action: RecordAction
    record: Union[ARecord, AAAARecord, CNAMERecord, MXRecord, TXTRecord]


class RecordResponse(BaseModel):
    """Model for record operation responses."""

    status: str
    operation: RecordAction
    timestamp: datetime
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    verified: bool = False


class BatchRecordResponse(BaseModel):
    """Model for batch operation responses."""

    overall_status: str
    operations: List[RecordResponse]
    failed_operations: List[Dict[str, Any]]
    timestamp: datetime


class DNSRecordManager:
    """Manager class for DNS record operations."""

    def __init__(self, client):
        """Initialize the DNS record manager.

        Args:
            client: The DNS services client instance
        """
        self._client = client
        self._verification_timeout = 60  # seconds
        self._verification_interval = 5  # seconds

    async def manage_record(
        self,
        action: RecordAction,
        domain: str,
        record: Union[ARecord, AAAARecord, CNAMERecord, MXRecord, TXTRecord],
    ) -> RecordResponse:
        """Manage a single DNS record.

        Args:
            action: The action to perform (create, update, delete)
            domain: The domain name
            record: The record data

        Returns:
            RecordResponse containing operation details and status
        """
        endpoint = f"/domains/{domain}/records"

        record_data = record.model_dump()
        if isinstance(record, MXRecord):
            record_data["data"] = {"value": record.value, "priority": record.priority}
        else:
            record_data["data"] = {"value": record.value}

        request_data = {
            "name": record.name,
            "type": record.type.value,
            "ttl": record.ttl,
            **record_data["data"],
        }

        method = {
            RecordAction.CREATE: "POST",
            RecordAction.UPDATE: "PUT",
            RecordAction.DELETE: "DELETE",
        }[action]

        response = await self._client.make_request(
            method=method,
            endpoint=endpoint,
            data=request_data if method != "DELETE" else None,
        )

        verified = False
        if action != RecordAction.DELETE and response["status"] == "success":
            verified = await self.verify_record(domain, record)

        return RecordResponse(
            status=response["status"],
            operation=action,
            timestamp=datetime.now(timezone.utc),
            data=response.get("data", {}),
            metadata={
                "domain": domain,
                "record_type": record.type.value,
                "ttl": record.ttl,
            },
            verified=verified,
        )

    async def batch_manage_records(
        self,
        operations: List[RecordOperation],
        domain: str,
    ) -> BatchRecordResponse:
        """Perform batch operations on DNS records.

        Args:
            operations: List of record operations to perform
            domain: The domain name

        Returns:
            BatchRecordResponse containing results of all operations
        """
        responses = []
        failed_operations = []

        # Process operations in parallel with timeout
        async def process_operation(op: RecordOperation) -> Dict[str, Any]:
            try:
                async with asyncio.timeout(30):  # 30 second timeout per operation
                    response = await self.manage_record(
                        action=op.action, domain=domain, record=op.record
                    )
                    if response.status == "error":
                        return {
                            "success": False,
                            "operation": op,
                            "error": response.data.get("message", "Operation failed"),
                        }
                    return {"success": True, "response": response}
            except asyncio.TimeoutError:
                return {
                    "success": False,
                    "operation": op,
                    "error": "Operation timed out",
                }
            except Exception as e:
                return {"success": False, "operation": op, "error": str(e)}

        # Create and run tasks with overall timeout
        tasks = [process_operation(op) for op in operations]
        try:
            async with asyncio.timeout(60):  # 60 second overall timeout
                results = await asyncio.gather(*tasks, return_exceptions=True)
        except asyncio.TimeoutError:
            return BatchRecordResponse(
                overall_status="error",
                operations=[],
                failed_operations=[{"error": "Batch operation timed out"}],
                timestamp=datetime.now(timezone.utc),
            )

        # Process results
        for i, result in enumerate(results):
            if isinstance(result, dict):
                if result["success"]:
                    responses.append(result["response"])
                else:
                    error_response = RecordResponse(
                        status="error",
                        operation=operations[i].action,
                        timestamp=datetime.now(timezone.utc),
                        data={"error": result["error"]},
                        metadata={"domain": domain},
                        verified=False,
                    )
                    responses.append(error_response)
                    failed_operations.append(
                        {
                            "operation": operations[i].model_dump(),
                            "error": result["error"],
                        }
                    )
            else:
                # Handle unexpected errors
                error_response = RecordResponse(
                    status="error",
                    operation=operations[i].action,
                    timestamp=datetime.now(timezone.utc),
                    data={"error": str(result)},
                    metadata={"domain": domain},
                    verified=False,
                )
                responses.append(error_response)
                failed_operations.append(
                    {"operation": operations[i].model_dump(), "error": str(result)}
                )

        # Determine overall status
        if len(failed_operations) == len(operations):
            overall_status = "error"
        elif failed_operations:
            overall_status = "partial"
        else:
            overall_status = "success"

        return BatchRecordResponse(
            overall_status=overall_status,
            operations=responses,
            failed_operations=failed_operations,
            timestamp=datetime.now(timezone.utc),
        )

    async def verify_record(
        self,
        domain: str,
        record: Union[ARecord, AAAARecord, CNAMERecord, MXRecord, TXTRecord],
        timeout: Optional[int] = None,
    ) -> bool:
        """Verify that a DNS record has propagated.

        Args:
            domain: The domain name
            record: The record to verify
            timeout: Optional custom timeout in seconds

        Returns:
            bool indicating whether verification was successful
        """
        timeout = timeout or self._verification_timeout
        end_time = datetime.now(timezone.utc).timestamp() + timeout

        while datetime.now(timezone.utc).timestamp() < end_time:
            try:
                # Query the DNS.services API to verify record
                response = await self._client.make_request(
                    method="GET",
                    endpoint=f"/domains/{domain}/records",
                    params={"name": record.name, "type": record.type.value},
                )

                if response["status"] == "success":
                    records = response.get("data", {}).get("records", [])
                    for dns_record in records:
                        if (
                            dns_record["name"] == record.name
                            and dns_record["type"] == record.type.value
                        ):
                            # For MX records, check both value and priority
                            if isinstance(record, MXRecord):
                                if (
                                    dns_record["value"] == record.value
                                    and dns_record["priority"] == record.priority
                                ):
                                    return True
                            # For other records, just check the value
                            elif dns_record["value"] == record.value:
                                return True

                # Wait before next check
                await asyncio.sleep(self._verification_interval)

            except Exception:
                # If verification check fails, continue trying
                await asyncio.sleep(self._verification_interval)
                continue

        return False
