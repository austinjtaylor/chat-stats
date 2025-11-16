"""
Stripe payment integration service.

This file now serves as an orchestrator delegating to specialized operation modules.
The original 555-line service has been refactored into focused operation modules for
better organization and testability.

Refactored from monolithic StripeService into focused operation modules:
- payment_methods.py: Payment method operations (335 lines)
- subscription_operations.py: Subscription management (120 lines)
- invoice_operations.py: Invoice retrieval (49 lines)
- checkout_operations.py: Checkout and billing portal (81 lines)
- webhook_operations.py: Webhook event construction (51 lines)

Total: 636 lines across 5 operation modules
"""

import os
from typing import Any

import stripe
from dotenv import load_dotenv

from services.stripe import (
    PaymentMethodOperations,
    SubscriptionOperations,
    InvoiceOperations,
    CheckoutOperations,
    WebhookOperations,
)

load_dotenv()

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


class StripeService:
    """Service for handling Stripe payment operations."""

    def __init__(self):
        """Initialize Stripe service."""
        if not stripe.api_key:
            print("WARNING: STRIPE_SECRET_KEY not set - payment features disabled")

        # Initialize operation modules
        self.payment_methods = PaymentMethodOperations()
        self.subscriptions = SubscriptionOperations()
        self.invoices = InvoiceOperations()
        self.checkout = CheckoutOperations()
        self.webhooks = WebhookOperations()

    def create_checkout_session(
        self, price_id: str, customer_email: str, user_id: str, success_url: str, cancel_url: str
    ) -> dict[str, str]:
        """
        Create a Stripe Checkout session - delegated to CheckoutOperations.

        Args:
            price_id: Stripe Price ID for the subscription
            customer_email: User's email address
            user_id: User ID to associate with subscription
            success_url: URL to redirect on successful payment
            cancel_url: URL to redirect on canceled payment

        Returns:
            Dictionary with checkout_url and session_id
        """
        return self.checkout.create_checkout_session(
            price_id, customer_email, user_id, success_url, cancel_url
        )

    def create_billing_portal_session(
        self, stripe_customer_id: str, return_url: str
    ) -> dict[str, str]:
        """
        Create a Stripe Billing Portal session - delegated to CheckoutOperations.

        Args:
            stripe_customer_id: Stripe Customer ID
            return_url: URL to return to after managing subscription

        Returns:
            Dictionary with portal_url
        """
        return self.checkout.create_billing_portal_session(stripe_customer_id, return_url)

    def construct_webhook_event(self, payload: bytes, sig_header: str) -> Any:
        """
        Verify and construct a Stripe webhook event - delegated to WebhookOperations.

        Args:
            payload: Raw request body
            sig_header: Stripe signature header

        Returns:
            Verified Stripe event object
        """
        return self.webhooks.construct_webhook_event(payload, sig_header)

    def get_subscription(self, subscription_id: str) -> Any:
        """
        Retrieve a subscription - delegated to SubscriptionOperations.

        Args:
            subscription_id: Stripe Subscription ID

        Returns:
            Stripe Subscription object
        """
        return self.subscriptions.get_subscription(subscription_id)

    def cancel_subscription(
        self,
        subscription_id: str,
        cancellation_reason: str = "",
        cancellation_feedback: str = ""
    ) -> Any:
        """
        Cancel a subscription (at period end).

        Args:
            subscription_id: Stripe Subscription ID
            cancellation_reason: Reason for cancellation
            cancellation_feedback: Additional feedback about cancellation

        Returns:
            Updated Stripe Subscription object
        """
        try:
            # Build metadata dict with cancellation info
            metadata = {}
            if cancellation_reason:
                metadata["cancellation_reason"] = cancellation_reason
            if cancellation_feedback:
                metadata["cancellation_feedback"] = cancellation_feedback

            # Modify subscription with cancellation and metadata
            params = {"cancel_at_period_end": True}
            if metadata:
                params["metadata"] = metadata

            return stripe.Subscription.modify(subscription_id, **params)
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to cancel subscription: {str(e)}"
            )

    def cancel_subscription_immediately(self, stripe_customer_id: str) -> Any:
        """Cancel subscriptions immediately - delegated to SubscriptionOperations."""
        return self.subscriptions.cancel_subscription_immediately(stripe_customer_id)

    def reactivate_subscription(self, subscription_id: str) -> Any:
        """Reactivate a subscription - delegated to SubscriptionOperations."""
        return self.subscriptions.reactivate_subscription(subscription_id)

    def get_payment_methods(self, stripe_customer_id: str, stripe_subscription_id: str = None) -> dict[str, Any]:
        """Get payment methods - delegated to PaymentMethodOperations."""
        return self.payment_methods.get_payment_methods(stripe_customer_id, stripe_subscription_id)

    def get_invoices(self, stripe_customer_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get invoices - delegated to InvoiceOperations."""
        return self.invoices.get_invoices(stripe_customer_id, limit)

    def update_payment_method(self, stripe_customer_id: str, payment_method_id: str) -> Any:
        """Update payment method - delegated to PaymentMethodOperations."""
        return self.payment_methods.update_payment_method(stripe_customer_id, payment_method_id)

    def remove_payment_method(self, stripe_customer_id: str, payment_method_id: str) -> dict[str, str]:
        """Remove payment method - delegated to PaymentMethodOperations."""
        return self.payment_methods.remove_payment_method(stripe_customer_id, payment_method_id)

    def create_setup_intent(self, stripe_customer_id: str) -> dict[str, str]:
        """Create setup intent - delegated to PaymentMethodOperations."""
        return self.payment_methods.create_setup_intent(stripe_customer_id)


# Singleton instance
_stripe_service = None


def get_stripe_service() -> StripeService:
    """Get the singleton Stripe service instance."""
    global _stripe_service
    if _stripe_service is None:
        _stripe_service = StripeService()
    return _stripe_service

