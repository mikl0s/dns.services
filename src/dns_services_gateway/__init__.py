"""DNS Services Gateway - A Python client for managing DNS records via DNS.services API."""

__version__ = "0.2.3"
__author__ = "DNS Services Gateway Contributors"
__license__ = "MIT"

from .config import DNSServicesConfig
from .client import DNSServicesClient
from .exceptions import (
    DNSServicesError,
    AuthenticationError,
    ConfigurationError,
    ValidationError,
    APIError,
)

__all__ = [
    "DNSServicesClient",
    "DNSServicesConfig",
    "DNSServicesError",
    "AuthenticationError",
    "ConfigurationError",
    "ValidationError",
    "APIError",
]
