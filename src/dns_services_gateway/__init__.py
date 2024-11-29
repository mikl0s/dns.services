"""DNS Services Gateway client library.

This package provides a Python client for interacting with the DNS.services API.
It handles authentication, token management, and provides a clean interface for
making API requests.
"""

__version__ = "0.1.0"
__author__ = "DNS Services Gateway Contributors"
__license__ = "MIT"

from dns_services_gateway.client import DNSServicesClient
from dns_services_gateway.config import DNSServicesConfig
from dns_services_gateway.domain import DomainOperations
from dns_services_gateway.exceptions import (
    AuthenticationError,
    TokenError,
    TokenVerificationError,
)

__all__ = [
    "DNSServicesClient",
    "DNSServicesConfig",
    "DomainOperations",
    "AuthenticationError",
    "TokenError",
    "TokenVerificationError",
]
