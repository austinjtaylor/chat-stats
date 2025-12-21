"""
Request logging middleware for production monitoring.
Logs all API requests with timing, status codes, and user information.
"""

import json
import logging
import time
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Configure logger
logger = logging.getLogger("api")
logger.setLevel(logging.INFO)

# Add StreamHandler to output to stdout (for Railway log collection)
if not logger.handlers:  # Avoid adding duplicate handlers
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all API requests with detailed information.

    Logs include:
    - HTTP method and path
    - Status code
    - Response time
    - User ID (if authenticated)
    - Client IP
    - Error details (if any)
    """

    def __init__(self, app, log_format: str = "json"):
        """
        Initialize request logging middleware.

        Args:
            app: FastAPI application instance
            log_format: Logging format ('json' or 'text')
        """
        super().__init__(app)
        self.log_format = log_format

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response details."""
        start_time = time.time()

        # Extract user info from request state (set by auth middleware)
        user_id = None
        if hasattr(request.state, "user"):
            user_id = request.state.user.get("user_id")

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Process request
        try:
            response: Response = await call_next(request)
            status_code = response.status_code
            error = None
        except Exception as e:
            # Log error and re-raise
            status_code = 500
            error = str(e)
            raise
        finally:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log the request
            self._log_request(
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                duration_ms=duration_ms,
                user_id=user_id,
                client_ip=client_ip,
                error=error,
            )

        return response

    def _log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        user_id: str | None,
        client_ip: str,
        error: str | None,
    ):
        """Log request details in specified format."""
        log_data = {
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
            "user_id": user_id,
            "client_ip": client_ip,
        }

        if error:
            log_data["error"] = error

        if self.log_format == "json":
            # JSON format for structured logging (production)
            logger.info(json.dumps(log_data))
        else:
            # Human-readable format (development)
            log_message = f"{method} {path} - {status_code} - {duration_ms:.2f}ms"
            if user_id:
                log_message += f" - user:{user_id}"
            if error:
                log_message += f" - ERROR: {error}"
            logger.info(log_message)


class AuthFailureLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log authentication failures for security monitoring.

    Logs 401 and 403 responses with client IP for potential security analysis.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log authentication failures."""
        response: Response = await call_next(request)

        # Log auth failures
        if response.status_code in [401, 403]:
            client_ip = request.client.host if request.client else "unknown"
            logger.warning(
                json.dumps(
                    {
                        "event": "auth_failure",
                        "status_code": response.status_code,
                        "path": request.url.path,
                        "method": request.method,
                        "client_ip": client_ip,
                    }
                )
            )

        return response


class QuotaLimitLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log query quota limit hits for analytics.

    Helps track user behavior and upgrade conversion opportunities.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log quota limit hits."""
        response: Response = await call_next(request)

        # Log quota limit hits (429 = rate limit / quota exceeded)
        if response.status_code == 429:
            user_id = None
            if hasattr(request.state, "user"):
                user_id = request.state.user.get("user_id")

            logger.info(
                json.dumps(
                    {
                        "event": "quota_limit_hit",
                        "user_id": user_id,
                        "path": request.url.path,
                        "method": request.method,
                    }
                )
            )

        return response


def configure_request_logging(app, log_format: str = "json"):
    """
    Configure request logging middleware for the application.

    Args:
        app: FastAPI application instance
        log_format: Logging format ('json' for production, 'text' for development)
    """
    app.add_middleware(RequestLoggingMiddleware, log_format=log_format)
    app.add_middleware(AuthFailureLoggingMiddleware)
    app.add_middleware(QuotaLimitLoggingMiddleware)
