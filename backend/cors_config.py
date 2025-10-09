"""
Middleware and static file handlers for FastAPI application.
"""

from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def configure_cors(app):
    """Configure CORS middleware for the application."""
    origins = [
        "http://localhost:3000",  # Local development (Vite dev server)
        "http://localhost:3001",  # Local development (Vite dev server alternate port)
        "http://localhost:4173",  # Local production preview
        "https://chat-frisbee-stats.vercel.app",  # Vercel production (actual)
        "https://chat-stats.vercel.app",  # Vercel production (if renamed)
        "https://chat-with-stats.vercel.app",  # Vercel production (old - temporary)
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=r"https://(chat-frisbee-stats|chat-stats|chat-with-stats).*\.vercel\.app",  # Vercel preview deployments
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )


def configure_trusted_host(app):
    """
    Configure trusted host middleware to prevent Host header attacks.

    In production, restricts which hosts can be used to access the application.
    In development, allows all hosts for flexibility.

    Note: Railway's internal healthchecks and load balancers require allowing
    wildcard hosts. Railway's edge layer handles Host header validation.
    """
    import os

    environment = os.getenv("ENVIRONMENT", "development")

    # Always allow all hosts for Railway compatibility
    # Railway's edge layer validates the Host header before reaching our app
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])


class DevStaticFiles(StaticFiles):
    """Custom static file handler with no-cache headers for development."""

    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if isinstance(response, FileResponse):
            # Add no-cache headers for development
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response
