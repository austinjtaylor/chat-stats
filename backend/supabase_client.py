"""
Supabase client configuration and helper functions.
Provides database connection and auth integration with Supabase.
"""

import os
from typing import Any

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
JWT_SECRET = os.getenv("JWT_SECRET")

# Database URL for direct PostgreSQL connection
DATABASE_URL = os.getenv("DATABASE_URL")


def get_supabase_url() -> str:
    """Get Supabase project URL."""
    if not SUPABASE_URL:
        raise ValueError("SUPABASE_URL environment variable not set")
    return SUPABASE_URL


def get_supabase_anon_key() -> str:
    """Get Supabase anon/public key (safe for frontend)."""
    if not SUPABASE_ANON_KEY:
        raise ValueError("SUPABASE_ANON_KEY environment variable not set")
    return SUPABASE_ANON_KEY


def get_supabase_service_key() -> str:
    """Get Supabase service role key (backend only, full access)."""
    if not SUPABASE_SERVICE_KEY:
        raise ValueError("SUPABASE_SERVICE_KEY environment variable not set")
    return SUPABASE_SERVICE_KEY


def get_jwt_secret() -> str:
    """Get JWT secret for token verification."""
    if not JWT_SECRET:
        raise ValueError("JWT_SECRET environment variable not set")
    return JWT_SECRET


def get_database_url() -> str:
    """Get PostgreSQL connection URL."""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable not set")
    return DATABASE_URL


def verify_supabase_config() -> dict[str, Any]:
    """
    Verify that all required Supabase configuration is present.

    Returns:
        Dictionary with configuration status

    Raises:
        ValueError: If required configuration is missing
    """
    config_status = {
        "supabase_url": bool(SUPABASE_URL),
        "supabase_anon_key": bool(SUPABASE_ANON_KEY),
        "supabase_service_key": bool(SUPABASE_SERVICE_KEY),
        "jwt_secret": bool(JWT_SECRET),
        "database_url": bool(DATABASE_URL),
    }

    missing = [key for key, present in config_status.items() if not present]

    if missing:
        raise ValueError(
            f"Missing required Supabase configuration: {', '.join(missing)}"
        )

    return {
        "status": "configured",
        "url": SUPABASE_URL,
        "has_anon_key": bool(SUPABASE_ANON_KEY),
        "has_service_key": bool(SUPABASE_SERVICE_KEY),
        "has_jwt_secret": bool(JWT_SECRET),
        "has_database_url": bool(DATABASE_URL),
    }


# Validate configuration on import
try:
    verify_supabase_config()
    print("✅ Supabase configuration validated")
except ValueError as e:
    print(f"⚠️  Supabase configuration warning: {e}")
    print(
        "   Set SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY, JWT_SECRET, and DATABASE_URL in .env"
    )


# Initialize Supabase admin client (for server-side operations like deleting users)
supabase_admin = None
try:
    from supabase import create_client

    if SUPABASE_URL and SUPABASE_SERVICE_KEY:
        supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        print("✅ Supabase admin client initialized")
except Exception as e:
    print(f"⚠️  Failed to initialize Supabase admin client: {e}")
    print("   User account deletion will not be available")
