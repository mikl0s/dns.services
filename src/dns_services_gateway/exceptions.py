"""Custom exceptions for the DNS Services Gateway."""

from typing import Optional, Any, Dict


class DNSServicesError(Exception):
    """Base exception for all DNS Services Gateway errors."""

    def __init__(
        self,
        message: str,
        *args: Any,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error message
            details: Additional error details
        """
        super().__init__(message, *args)
        self.message = message
        self.details = details or {}


class AuthenticationError(DNSServicesError):
    """Raised when authentication fails."""

    pass


class ConfigurationError(DNSServicesError):
    """Raised when there is an issue with the configuration."""

    pass


class ValidationError(DNSServicesError):
    """Raised when data validation fails."""

    pass


class APIError(DNSServicesError):
    """Raised when the API returns an error."""

    def __init__(
        self,
        message: str,
        *args: Any,
        status_code: Optional[int] = None,
        response_body: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the API error.

        Args:
            message: Human-readable error message
            status_code: HTTP status code if available
            response_body: Raw API response if available
        """
        super().__init__(
            message,
            *args,
            details={
                "status_code": status_code,
                "response_body": response_body,
            },
        )
        self.status_code = status_code
        self.response_body = response_body
