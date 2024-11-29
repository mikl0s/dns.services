"""Handler for domain list operations."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

router = APIRouter()


@router.get("/domains/list", summary="Bulk Domain Listing")
async def list_domains_handler(
    status: Optional[str] = Query(None, description="Filter by registration status"),
    expiration_date: Optional[str] = Query(
        None, description="Filter by expiration date range"
    ),
):
    """
    Handle listing of domains.

    This function is responsible for retrieving a list of domains based on the provided
    filters. It returns a list of domain objects, each containing information about the
    domain's registration status, expiration date, DNS configuration, and
    nameservers.

    Args:
        status (Optional[str]): Filter by registration status.
        expiration_date (Optional[str]): Filter by expiration date range.

    Returns:
        list: A list of domain objects.
    """
    try:
        # Mocked response for demonstration purposes
        domains = [
            {
                "id": "domain1",
                "name": "example.com",
                "status": "active",
                "expires": "2024-12-31T23:59:59Z",
                "auto_renew": True,
                "nameservers": ["ns1.example.com", "ns2.example.com"],
            }
        ]
        return domains
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list domains: {str(e)}")
