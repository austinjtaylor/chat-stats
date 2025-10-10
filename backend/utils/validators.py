"""
Input validation utilities for security-critical operations.

Provides validation for payment-related inputs like price IDs and redirect URLs.
"""

import os
import re
from typing import Optional
from fastapi import HTTPException


# Valid Stripe price ID format: price_XXXX... (starts with price_)
STRIPE_PRICE_ID_PATTERN = re.compile(r'^price_[a-zA-Z0-9]+$')

# Allowed redirect URL patterns (production domains)
ALLOWED_REDIRECT_DOMAINS = [
    "localhost:3000",
    "localhost:3001",
    "localhost:4173",
    "chat-frisbee-stats.vercel.app",
    "chat-stats.vercel.app",
    "chat-with-stats.vercel.app",
]


def get_valid_price_ids() -> set[str]:
    """
    Get the set of valid price IDs from environment variables.

    Returns:
        Set of valid Stripe price IDs
    """
    # Get price ID from environment (production) or use test ID (development)
    pro_price_id = os.getenv("STRIPE_PRO_PRICE_ID", "price_1SEVEqFQ5wQ0K5wX7rwFg6z2")

    return {pro_price_id}


def validate_price_id(price_id: str) -> None:
    """
    Validate a Stripe price ID.

    Args:
        price_id: The price ID to validate

    Raises:
        HTTPException: If price ID is invalid or not whitelisted
    """
    # Check format
    if not STRIPE_PRICE_ID_PATTERN.match(price_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid price ID format"
        )

    # Check against whitelist
    valid_ids = get_valid_price_ids()
    if price_id not in valid_ids:
        raise HTTPException(
            status_code=400,
            detail="Price ID not recognized"
        )


def validate_redirect_url(url: str) -> None:
    """
    Validate a redirect URL for Stripe checkout success/cancel.

    Prevents open redirect vulnerabilities by ensuring URLs only redirect
    to trusted domains.

    Args:
        url: The redirect URL to validate

    Raises:
        HTTPException: If URL is invalid or not from an allowed domain
    """
    # Parse URL
    from urllib.parse import urlparse

    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid redirect URL format"
        )

    # Must be HTTP or HTTPS
    if parsed.scheme not in ["http", "https"]:
        raise HTTPException(
            status_code=400,
            detail="Redirect URL must use HTTP or HTTPS"
        )

    # localhost must use HTTP in development
    if "localhost" in parsed.netloc and parsed.scheme != "http":
        raise HTTPException(
            status_code=400,
            detail="localhost URLs must use HTTP"
        )

    # Production domains must use HTTPS
    if "localhost" not in parsed.netloc and parsed.scheme != "https":
        raise HTTPException(
            status_code=400,
            detail="Production URLs must use HTTPS"
        )

    # Check against allowed domains
    # Extract domain (including port for localhost)
    netloc = parsed.netloc.lower()

    # Check if domain is in allowed list
    allowed = False
    for domain in ALLOWED_REDIRECT_DOMAINS:
        if netloc == domain or netloc.endswith(f".{domain}"):
            allowed = True
            break

    # Also check if it's a Vercel preview deployment
    if netloc.endswith(".vercel.app"):
        # Allow Vercel preview deployments with our project names
        for project in ["chat-frisbee-stats", "chat-stats", "chat-with-stats"]:
            if project in netloc:
                allowed = True
                break

    if not allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Redirect URL domain not allowed: {netloc}"
        )


def validate_customer_email(email: Optional[str]) -> None:
    """
    Validate a customer email address.

    Args:
        email: The email address to validate

    Raises:
        HTTPException: If email is invalid
    """
    if not email:
        return  # Email is optional for checkout

    # Basic email validation
    email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    if not email_pattern.match(email):
        raise HTTPException(
            status_code=400,
            detail="Invalid email address"
        )

    # Prevent excessively long emails (DoS protection)
    if len(email) > 254:
        raise HTTPException(
            status_code=400,
            detail="Email address too long"
        )
