"""Tests for DNS Services Gateway exceptions."""

from datetime import datetime
from dns_services_gateway.exceptions import (
    DNSServicesError,
    APIError,
    RateLimitError,
)


def test_dns_services_error_with_details():
    """Test DNSServicesError with details."""
    error = DNSServicesError("Test error", {"detail": "More info"})
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
    now = datetime.now()
    error = RateLimitError("Rate limit exceeded", retry_after=now)
    assert str(error) == f"Rate limit exceeded (retry after {now})"


def test_rate_limit_error_without_retry():
    """Test RateLimitError without retry after."""
    error = RateLimitError("Rate limit exceeded")
    assert str(error) == "Rate limit exceeded"
