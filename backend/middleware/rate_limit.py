"""
Rate limiting middleware for API abuse prevention.

Protects against DOS attacks and API abuse by limiting requests per time window.
Uses SlowAPI for flexible rate limiting with different limits per endpoint.
"""

from fastapi import Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse


def get_user_id_or_ip(request: Request) -> str:
    """
    Get user ID for authenticated requests, IP address for anonymous.

    This allows per-user rate limiting for authenticated endpoints
    and per-IP rate limiting for public endpoints.
    """
    # Try to get user ID from request state (set by auth middleware)
    if hasattr(request.state, "user") and request.state.user:
        return f"user:{request.state.user.get('user_id')}"

    # Fall back to IP address for unauthenticated requests
    return f"ip:{get_remote_address(request)}"


# Initialize rate limiter
# storage_uri can be:
# - "memory://" for in-memory (single server)
# - "redis://localhost:6379" for Redis (multi-server, recommended for production)
limiter = Limiter(
    key_func=get_user_id_or_ip,
    storage_uri="memory://",  # Use Redis in production for multi-server setups
    default_limits=["100/minute"],  # Default limit for all endpoints
)


def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """
    Custom handler for rate limit exceeded errors.

    Returns a user-friendly JSON response when rate limit is hit.
    """
    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "detail": f"Too many requests. Please try again in {exc.retry_after} seconds.",
            "retry_after": exc.retry_after,
        },
        headers={"Retry-After": str(exc.retry_after)},
    )


# Rate limit decorators for different endpoint types
# These can be applied to individual routes in the API


# Public endpoints - more permissive
public_limit = limiter.limit("100/minute")

# Authenticated endpoints - per-user limits
auth_limit = limiter.limit("200/hour")

# AI query endpoints - already limited by subscription quotas
# This is just for anti-abuse (e.g., prevent scripts from spamming)
query_limit = limiter.limit("30/minute")

# Admin endpoints - stricter limits
admin_limit = limiter.limit("20/minute")

# No limit (for webhooks and health checks)
no_limit = limiter.exempt


def configure_rate_limiting(app):
    """
    Configure rate limiting for the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    # Add rate limiter to app state
    app.state.limiter = limiter

    # Add exception handler for rate limit errors
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    return limiter


# Example usage in routes:
# from middleware.rate_limit import public_limit, auth_limit, query_limit, no_limit
#
# @router.get("/api/stats")
# @public_limit  # 100 requests/minute
# async def get_stats():
#     ...
#
# @router.post("/api/query")
# @query_limit  # 30 requests/minute (plus subscription quota enforcement)
# async def query_stats():
#     ...
#
# @router.post("/api/stripe/webhook")
# @no_limit  # No rate limit for Stripe webhooks
# async def stripe_webhook():
#     ...
