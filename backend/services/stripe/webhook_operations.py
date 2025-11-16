"""
Stripe webhook operations.
"""

import os
from typing import Any

import stripe
from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()

STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")


class WebhookOperations:
    """Handles webhook-related Stripe operations."""

    @staticmethod
    def construct_webhook_event(payload: bytes, sig_header: str) -> Any:
        """
        Verify and construct a Stripe webhook event.

        Args:
            payload: Raw request body
            sig_header: Stripe signature header

        Returns:
            Verified Stripe event object

        Raises:
            HTTPException: If signature verification fails
        """
        if not STRIPE_WEBHOOK_SECRET:
            raise HTTPException(
                status_code=500, detail="Webhook secret not configured"
            )

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
            return event
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid payload")
        except Exception as e:
            if "signature" in str(e).lower():
                raise HTTPException(status_code=400, detail="Invalid signature")
            raise HTTPException(status_code=400, detail=f"Webhook error: {str(e)}")
