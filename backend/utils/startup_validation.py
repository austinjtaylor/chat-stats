"""
Startup validation for required environment variables and configuration.

Validates that all critical environment variables are set before the application starts.
Fails fast with clear error messages if configuration is missing or invalid.
"""

import os
import sys
from typing import List, Tuple


class ValidationError(Exception):
    """Raised when startup validation fails."""

    pass


def validate_required_env_vars() -> None:
    """
    Validate that all required environment variables are set.

    Raises:
        ValidationError: If any required variables are missing
    """
    # Required variables for all environments
    required_vars = [
        ("ANTHROPIC_API_KEY", "Anthropic API key for AI features"),
        ("SUPABASE_URL", "Supabase project URL"),
        ("SUPABASE_ANON_KEY", "Supabase anonymous/public key"),
        ("SUPABASE_SERVICE_KEY", "Supabase service role key"),
        ("DATABASE_URL", "PostgreSQL database connection string"),
        ("JWT_SECRET", "JWT secret for token verification"),
    ]

    # Stripe variables (required in production)
    stripe_vars = [
        ("STRIPE_SECRET_KEY", "Stripe secret key"),
        ("STRIPE_WEBHOOK_SECRET", "Stripe webhook signing secret"),
    ]

    # Check environment
    environment = os.getenv("ENVIRONMENT", "development")

    if environment == "production":
        # In production, all Stripe variables are required
        required_vars.extend(stripe_vars)

    # Collect missing variables
    missing: List[Tuple[str, str]] = []

    for var_name, description in required_vars:
        value = os.getenv(var_name)
        if not value or value.strip() == "":
            missing.append((var_name, description))

    if missing:
        error_message = "Missing required environment variables:\n\n"
        for var_name, description in missing:
            error_message += f"  • {var_name}: {description}\n"
        error_message += "\nPlease check your .env file and ensure all required variables are set."
        raise ValidationError(error_message)


def validate_stripe_configuration() -> None:
    """
    Validate Stripe configuration is properly set up.

    Raises:
        ValidationError: If Stripe configuration is invalid
    """
    environment = os.getenv("ENVIRONMENT", "development")

    stripe_key = os.getenv("STRIPE_SECRET_KEY", "")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    # Validate Stripe key format
    if stripe_key:
        # Test keys start with sk_test_, live keys with sk_live_
        if environment == "production" and not stripe_key.startswith("sk_live_"):
            raise ValidationError(
                "Production environment requires live Stripe keys (sk_live_). "
                "Found test key instead."
            )

        if environment == "development" and stripe_key.startswith("sk_live_"):
            print(
                "⚠️  WARNING: Using live Stripe key in development environment! "
                "This should only be used for testing production setup."
            )

    # Validate webhook secret format
    if webhook_secret and not webhook_secret.startswith("whsec_"):
        raise ValidationError(
            f"Invalid STRIPE_WEBHOOK_SECRET format. "
            f"Expected format: whsec_xxx, got: {webhook_secret[:10]}..."
        )


def validate_database_connection() -> None:
    """
    Validate database connection string format.

    Raises:
        ValidationError: If database URL is invalid
    """
    db_url = os.getenv("DATABASE_URL", "")

    if not db_url:
        return  # Already caught by required vars check

    # Must be PostgreSQL
    if not db_url.startswith("postgresql://"):
        raise ValidationError(
            "DATABASE_URL must be a PostgreSQL connection string "
            "(should start with postgresql://)"
        )

    # Must include required components
    required_parts = ["@", "/"]
    for part in required_parts:
        if part not in db_url:
            raise ValidationError(f"DATABASE_URL appears to be malformed (missing '{part}')")


def validate_supabase_configuration() -> None:
    """
    Validate Supabase configuration.

    Raises:
        ValidationError: If Supabase configuration is invalid
    """
    url = os.getenv("SUPABASE_URL", "")
    anon_key = os.getenv("SUPABASE_ANON_KEY", "")
    service_key = os.getenv("SUPABASE_SERVICE_KEY", "")

    # Validate URL format
    if url and not url.startswith("https://"):
        raise ValidationError("SUPABASE_URL must start with https://")

    if url and not url.endswith(".supabase.co"):
        raise ValidationError("SUPABASE_URL must be a valid Supabase URL (ends with .supabase.co)")

    # Validate key formats (JWT tokens start with eyJ)
    if anon_key and not anon_key.startswith("eyJ"):
        raise ValidationError("SUPABASE_ANON_KEY appears to be invalid (should be a JWT token)")

    if service_key and not service_key.startswith("eyJ"):
        raise ValidationError("SUPABASE_SERVICE_KEY appears to be invalid (should be a JWT token)")


def run_startup_validation() -> None:
    """
    Run all startup validations.

    This should be called at application startup before any routes are registered.
    Will exit the process with an error if validation fails.
    """
    try:
        print("🔍 Running startup validation...")

        validate_required_env_vars()
        print("  ✓ Required environment variables present")

        validate_database_connection()
        print("  ✓ Database configuration valid")

        validate_supabase_configuration()
        print("  ✓ Supabase configuration valid")

        validate_stripe_configuration()
        print("  ✓ Stripe configuration valid")

        print("✅ Startup validation passed!\n")

    except ValidationError as e:
        print(f"\n❌ STARTUP VALIDATION FAILED:\n")
        print(str(e))
        print("\nApplication cannot start. Please fix the configuration errors and try again.\n")
        sys.exit(1)
