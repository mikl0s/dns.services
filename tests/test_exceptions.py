"""Tests for DNS Services Gateway exceptions."""

from dns_services_gateway.exceptions import (
    DNSServicesError,
    APIError,
    RateLimitError,
)


def test_dns_services_error_with_details():
    """Test DNSServicesError with details."""
    error = DNSServicesError("Test error", details={"detail": "More info"})
    assert str(error) == "Test error: {'detail': 'More info'}"


def test_dns_services_error_without_details():
    """Test DNSServicesError without details."""
    error = DNSServicesError("Test error")
    assert str(error) == "Test error"


def test_api_error_with_full_details():
    """Test APIError with full details."""
    error = APIError("API error", {"code": 400, "message": "Bad request"})
    assert str(error) == "API error: {'code': 400, 'message': 'Bad request'}"


def test_api_error_without_details():
    """Test APIError without details."""
    error = APIError("API error")
    assert str(error) == "API error"


def test_rate_limit_error_with_retry():
    """Test RateLimitError with retry after."""
    error = RateLimitError(
        "Rate limit exceeded", retry_after=60
    )  # Use seconds instead of datetime
    assert str(error) == "Rate limit exceeded (retry after 60 seconds)"


def test_rate_limit_error_without_retry():
    """Test RateLimitError without retry after."""
    error = RateLimitError("Rate limit exceeded")
    assert str(error) == "Rate limit exceeded"
