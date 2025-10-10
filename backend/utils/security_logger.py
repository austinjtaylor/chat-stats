"""
Security event logging utility.

Provides structured logging for security-critical events like authentication
failures, payment attempts, and suspicious activity.
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional

# Configure security logger
security_logger = logging.getLogger("security")
security_logger.setLevel(logging.INFO)

# Create console handler with JSON formatting
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
security_logger.addHandler(handler)


def log_security_event(
    event_type: str,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
    severity: str = "INFO",
) -> None:
    """
    Log a security event with structured data.

    Args:
        event_type: Type of security event (e.g., "auth_failure", "payment_attempt")
        user_id: User ID if available
        ip_address: Client IP address
        details: Additional event details
        severity: Log level (INFO, WARNING, ERROR, CRITICAL)
    """
    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "event": event_type,
        "user_id": user_id,
        "ip_address": ip_address,
        "details": details or {},
    }

    log_message = json.dumps(event)

    if severity == "CRITICAL":
        security_logger.critical(log_message)
    elif severity == "ERROR":
        security_logger.error(log_message)
    elif severity == "WARNING":
        security_logger.warning(log_message)
    else:
        security_logger.info(log_message)


def log_auth_failure(
    reason: str,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> None:
    """Log an authentication failure."""
    log_security_event(
        event_type="auth_failure",
        user_id=user_id,
        ip_address=ip_address,
        details={"reason": reason, **(details or {})},
        severity="WARNING",
    )


def log_payment_attempt(
    success: bool,
    user_id: str,
    amount: Optional[float] = None,
    currency: str = "USD",
    ip_address: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> None:
    """Log a payment attempt (success or failure)."""
    log_security_event(
        event_type="payment_attempt",
        user_id=user_id,
        ip_address=ip_address,
        details={
            "success": success,
            "amount": amount,
            "currency": currency,
            **(details or {}),
        },
        severity="INFO" if success else "WARNING",
    )


def log_webhook_event(
    event_type: str,
    verified: bool,
    ip_address: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> None:
    """Log a webhook event."""
    log_security_event(
        event_type="webhook_event",
        ip_address=ip_address,
        details={
            "webhook_type": event_type,
            "verified": verified,
            **(details or {}),
        },
        severity="INFO" if verified else "ERROR",
    )


def log_rate_limit_exceeded(
    endpoint: str,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Log a rate limit violation."""
    log_security_event(
        event_type="rate_limit_exceeded",
        user_id=user_id,
        ip_address=ip_address,
        details={"endpoint": endpoint},
        severity="WARNING",
    )


def log_suspicious_activity(
    activity_type: str,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> None:
    """Log suspicious activity that may indicate an attack."""
    log_security_event(
        event_type="suspicious_activity",
        user_id=user_id,
        ip_address=ip_address,
        details={"activity_type": activity_type, **(details or {})},
        severity="ERROR",
    )
