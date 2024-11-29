"""Custom exceptions for the DNS Services Gateway."""

from typing import Optional, Any, Dict
from datetime import datetime


class DNSServicesError(Exception):
    """Base exception for all DNS Services Gateway errors."""

    def __init__(
        self, message: str, *args: Any, details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize the DNS Services error.

        Args:
            message: Human-readable error message
            args: Additional positional arguments for the base Exception class
            details: Optional dictionary containing additional error details
        """
        super().__init__(message, *args)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        """Return a string representation of the error.

        Returns:
            A string representation of the error
        """
        return self.message


class AuthenticationError(DNSServicesError):
    """Raised when authentication fails.

    Args:
        message: Human-readable error message
        args: Additional positional arguments for the base Exception class
        details: Optional dictionary containing additional error details
    """


class TokenError(Exception):
    """Exception raised for errors related to token management."""

    def __init__(self, message: str):
        """Initialize the token error.

        Args:
            message: Human-readable error message
        """
        super().__init__(message)


class ConfigurationError(DNSServicesError):
    """Raised when there is an issue with the configuration.

    Args:
        message: Human-readable error message
        args: Additional positional arguments for the base Exception class
        details: Optional dictionary containing additional error details
    """


class ValidationError(DNSServicesError):
    """Raised when data validation fails.

    Args:
        message: Human-readable error message
        args: Additional positional arguments for the base Exception class
        details: Optional dictionary containing additional error details
    """


class APIError(DNSServicesError):
    """Raised when the API returns an error.

    Args:
        message: Human-readable error message
        args: Additional positional arguments for the base Exception class
        status_code: HTTP status code if available
        response_body: Raw API response if available
    """

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


class TokenLoadError(TokenError):
    """Raised when there is an error loading a token from file.

    This can happen if:
    - The token file does not exist
    - The token file has invalid permissions
    - The token file contains invalid JSON
    - The token file is missing required fields

    Args:
        message: Human-readable error message
        args: Additional positional arguments for the base Exception class
        details: Optional dictionary containing additional error details
    """


class TokenDownloadError(TokenError):
    """Raised when there is an error downloading a token from the API.

    This can happen if:
    - The API returns an error response
    - The API response is missing required fields

    Args:
        message: Human-readable error message
        args: Additional positional arguments for the base Exception class
        details: Optional dictionary containing additional error details
    """


class TokenExpiredError(TokenError):
    """Raised when the authentication token has expired.

    Args:
        message: Human-readable error message
        args: Additional positional arguments for the base Exception class
        details: Optional dictionary containing additional error details
    """


class TokenVerificationError(TokenError):
    """Raised when there is an error verifying a token.

    This can happen if:
    - The token file cannot be loaded
    - The token has expired

    Args:
        message: Human-readable error message
        args: Additional positional arguments for the base Exception class
        details: Optional dictionary containing additional error details
    """


class RateLimitError(DNSServicesError):
    """Raised when API rate limit is exceeded.

    Args:
        message: Human-readable error message
        args: Additional positional arguments for the base Exception class
        retry_after: Optional number of seconds to wait before retrying
        details: Optional dictionary containing additional error details
    """

    def __init__(
        self,
        message: str,
        *args: Any,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the rate limit error.

        Args:
            message: Human-readable error message
            retry_after: Optional number of seconds to wait before retrying
            details: Optional dictionary containing additional error details
        """
        super().__init__(message, *args, details=details)
        self.retry_after = retry_after


class AuthResponse:
    """Authentication response model.

    Attributes:
        token: Authentication token
        expiration: Token expiration timestamp
        refresh_token: Optional refresh token
    """

    def __init__(
        self, token: str, expiration: datetime, refresh_token: Optional[str] = None
    ):
        """Initialize the authentication response.

        Args:
            token: Authentication token
            expiration: Token expiration timestamp
            refresh_token: Optional refresh token
        """
        self.token = token
        self.expiration = expiration
        self.refresh_token = refresh_token
