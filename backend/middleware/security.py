"""
Security headers middleware for production hardening.
Adds security headers to all HTTP responses.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Security headers help protect against common web vulnerabilities:
    - HSTS: Forces HTTPS connections
    - CSP: Prevents XSS and injection attacks
    - X-Frame-Options: Prevents clickjacking
    - X-Content-Type-Options: Prevents MIME sniffing
    - X-XSS-Protection: Enables browser XSS protection
    - Referrer-Policy: Controls referrer information
    """

    def __init__(self, app, enable_hsts: bool = True):
        """
        Initialize security headers middleware.

        Args:
            app: FastAPI application instance
            enable_hsts: Enable HSTS header (only enable when HTTPS is available)
        """
        super().__init__(app)
        self.enable_hsts = enable_hsts

    async def dispatch(self, request: Request, call_next):
        """Add security headers to response."""
        response: Response = await call_next(request)

        # Strict-Transport-Security (HSTS)
        # Only enable when explicitly requested (caller should ensure HTTPS is available)
        if self.enable_hsts:
            response.headers[
                "Strict-Transport-Security"
            ] = "max-age=31536000; includeSubDomains"

        # Content-Security-Policy (CSP)
        # Restricts resource loading to prevent XSS
        # Note: Adjust based on your frontend needs
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://js.stripe.com https://*.supabase.co",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self' https://*.supabase.co https://api.stripe.com https://*.railway.app https://*.vercel.app",
            "frame-src 'self' https://js.stripe.com",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # X-Frame-Options: Prevents clickjacking attacks
        response.headers["X-Frame-Options"] = "DENY"

        # X-Content-Type-Options: Prevents MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-XSS-Protection: Enables browser XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer-Policy: Controls referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions-Policy: Controls browser features
        # Disable features not needed by the application
        permissions_policies = [
            "geolocation=()",
            "microphone=()",
            "camera=()",
            "payment=(self)",
            "usb=()",
            "magnetometer=()",
            "gyroscope=()",
            "accelerometer=()",
        ]
        response.headers["Permissions-Policy"] = ", ".join(permissions_policies)

        return response


def configure_security_headers(app, enable_hsts: bool = True):
    """
    Configure security headers middleware for the application.

    Args:
        app: FastAPI application instance
        enable_hsts: Enable HSTS header (recommended for production)
    """
    app.add_middleware(SecurityHeadersMiddleware, enable_hsts=enable_hsts)
