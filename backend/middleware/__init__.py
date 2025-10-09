"""
Middleware package for production hardening.
"""

from .security import SecurityHeadersMiddleware, configure_security_headers
from .logging_middleware import (
    RequestLoggingMiddleware,
    AuthFailureLoggingMiddleware,
    QuotaLimitLoggingMiddleware,
    configure_request_logging,
)
from .rate_limit import (
    limiter,
    configure_rate_limiting,
    public_limit,
    auth_limit,
    query_limit,
    admin_limit,
    no_limit,
)

__all__ = [
    "SecurityHeadersMiddleware",
    "configure_security_headers",
    "RequestLoggingMiddleware",
    "AuthFailureLoggingMiddleware",
    "QuotaLimitLoggingMiddleware",
    "configure_request_logging",
    "limiter",
    "configure_rate_limiting",
    "public_limit",
    "auth_limit",
    "query_limit",
    "admin_limit",
    "no_limit",
]
