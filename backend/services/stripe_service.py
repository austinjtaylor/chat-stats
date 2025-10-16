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

        except Exception as e:
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

        except Exception as e:
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
        except Exception as e:
            if "signature" in str(e).lower():
                raise HTTPException(status_code=400, detail="Invalid signature")
            raise HTTPException(status_code=400, detail=f"Webhook error: {str(e)}")

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
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to retrieve subscription: {str(e)}"
            )

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
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to reactivate subscription: {str(e)}"
            )

    def get_payment_methods(self, stripe_customer_id: str, stripe_subscription_id: str = None) -> dict[str, Any]:
        """
        Get the default payment method for a customer.

        Args:
            stripe_customer_id: Stripe Customer ID
            stripe_subscription_id: Optional Stripe Subscription ID to fallback to

        Returns:
            Dictionary with payment method details (brand, last4, exp_month, exp_year)
        """
        try:
            # Get customer to find default payment method
            customer = stripe.Customer.retrieve(
                stripe_customer_id,
                expand=["invoice_settings.default_payment_method"]
            )

            # Get the default payment method
            payment_method = customer.invoice_settings.default_payment_method

            # If no default payment method set, try to get from active subscription
            if not payment_method and stripe_subscription_id:
                try:
                    subscription = stripe.Subscription.retrieve(stripe_subscription_id)
                    payment_method_id = subscription.get('default_payment_method')

                    if payment_method_id:
                        # Retrieve the full payment method object
                        payment_method = stripe.PaymentMethod.retrieve(payment_method_id)

                        # Set it as customer's default for future use
                        try:
                            stripe.Customer.modify(
                                stripe_customer_id,
                                invoice_settings={
                                    'default_payment_method': payment_method_id
                                }
                            )
                        except Exception as e:
                            # Log but don't fail if setting default fails
                            print(f"Warning: Failed to set default payment method: {e}")
                except Exception as e:
                    print(f"Warning: Failed to retrieve payment method from subscription: {e}")

            if not payment_method:
                return None

            # Return simplified payment method info
            return {
                "id": payment_method.id,
                "type": payment_method.type,
                "card": {
                    "brand": payment_method.card.brand,
                    "last4": payment_method.card.last4,
                    "exp_month": payment_method.card.exp_month,
                    "exp_year": payment_method.card.exp_year,
                } if payment_method.type == "card" else None
            }

        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to retrieve payment methods: {str(e)}"
            )

    def get_invoices(self, stripe_customer_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get recent invoices for a customer.

        Args:
            stripe_customer_id: Stripe Customer ID
            limit: Maximum number of invoices to return (default 10)

        Returns:
            List of invoice dictionaries with id, date, amount, status, invoice_pdf
        """
        try:
            # Get invoices for customer
            invoices = stripe.Invoice.list(
                customer=stripe_customer_id,
                limit=limit
            )

            # Format invoice data
            result = []
            for invoice in invoices.data:
                result.append({
                    "id": invoice.id,
                    "date": invoice.created,
                    "amount_paid": invoice.amount_paid / 100,  # Convert from cents
                    "currency": invoice.currency.upper(),
                    "status": invoice.status,
                    "invoice_pdf": invoice.invoice_pdf,
                    "hosted_invoice_url": invoice.hosted_invoice_url
                })

            return result

        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to retrieve invoices: {str(e)}"
            )

    def update_payment_method(self, stripe_customer_id: str, payment_method_id: str) -> Any:
        """
        Update the default payment method for a customer.

        Args:
            stripe_customer_id: Stripe Customer ID
            payment_method_id: Stripe Payment Method ID

        Returns:
            Updated Stripe Customer object
        """
        try:
            # Attach payment method to customer
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=stripe_customer_id,
            )

            # Set as default payment method for invoices
            customer = stripe.Customer.modify(
                stripe_customer_id,
                invoice_settings={
                    "default_payment_method": payment_method_id,
                },
            )

            return customer

        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to update payment method: {str(e)}"
            )


# Singleton instance
_stripe_service = None


def get_stripe_service() -> StripeService:
    """Get the singleton Stripe service instance."""
    global _stripe_service
    if _stripe_service is None:
        _stripe_service = StripeService()
    return _stripe_service
