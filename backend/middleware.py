"""
Middleware and static file handlers for FastAPI application.
"""

from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse


def configure_cors(app):
    """Configure CORS middleware for the application."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )


def configure_trusted_host(app):
    """Configure trusted host middleware for proxy support."""
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