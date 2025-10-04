"""
Stripe payment integration service.
Handles checkout, subscriptions, and webhooks.
"""

import os
from typing import Any

import stripe
from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")


class StripeService:
    """Service for handling Stripe payment operations."""

    def __init__(self):
        """Initialize Stripe service."""
        if not stripe.api_key:
            print("WARNING: STRIPE_SECRET_KEY not set - payment features disabled")

    def create_checkout_session(
        self, price_id: str, customer_email: str, user_id: str, success_url: str, cancel_url: str
    ) -> dict[str, str]:
        """
        Create a Stripe Checkout session for subscription payment.

        Args:
            price_id: Stripe Price ID for the subscription
            customer_email: User's email address
            user_id: User ID to associate with subscription
            success_url: URL to redirect on successful payment
            cancel_url: URL to redirect on canceled payment

        Returns:
            Dictionary with checkout_url and session_id

        Raises:
            HTTPException: If Stripe API call fails
        """
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        "price": price_id,
                        "quantity": 1,
                    }
                ],
                mode="subscription",
                success_url=success_url,
                cancel_url=cancel_url,
                customer_email=customer_email,
                client_reference_id=user_id,  # Link back to our user
                metadata={"user_id": user_id},
            )

            return {"checkout_url": session.url, "session_id": session.id}

        except stripe.error.StripeError as e:
            raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")

    def create_billing_portal_session(
        self, stripe_customer_id: str, return_url: str
    ) -> dict[str, str]:
        """
        Create a Stripe Billing Portal session for managing subscriptions.

        Args:
            stripe_customer_id: Stripe Customer ID
            return_url: URL to return to after managing subscription

        Returns:
            Dictionary with portal_url

        Raises:
            HTTPException: If Stripe API call fails
        """
        try:
            session = stripe.billing_portal.Session.create(
                customer=stripe_customer_id, return_url=return_url
            )

            return {"portal_url": session.url}

        except stripe.error.StripeError as e:
            raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")

    def construct_webhook_event(self, payload: bytes, sig_header: str) -> Any:
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
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")

    def get_subscription(self, subscription_id: str) -> Any:
        """
        Retrieve a subscription from Stripe.

        Args:
            subscription_id: Stripe Subscription ID

        Returns:
            Stripe Subscription object
        """
        try:
            return stripe.Subscription.retrieve(subscription_id)
        except stripe.error.StripeError as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to retrieve subscription: {str(e)}"
            )

    def cancel_subscription(self, subscription_id: str) -> Any:
        """
        Cancel a subscription (at period end).

        Args:
            subscription_id: Stripe Subscription ID

        Returns:
            Updated Stripe Subscription object
        """
        try:
            return stripe.Subscription.modify(
                subscription_id, cancel_at_period_end=True
            )
        except stripe.error.StripeError as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to cancel subscription: {str(e)}"
            )

    def reactivate_subscription(self, subscription_id: str) -> Any:
        """
        Reactivate a subscription that was set to cancel.

        Args:
            subscription_id: Stripe Subscription ID

        Returns:
            Updated Stripe Subscription object
        """
        try:
            return stripe.Subscription.modify(
                subscription_id, cancel_at_period_end=False
            )
        except stripe.error.StripeError as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to reactivate subscription: {str(e)}"
            )


# Singleton instance
_stripe_service = None


def get_stripe_service() -> StripeService:
    """Get the singleton Stripe service instance."""
    global _stripe_service
    if _stripe_service is None:
        _stripe_service = StripeService()
    return _stripe_service
