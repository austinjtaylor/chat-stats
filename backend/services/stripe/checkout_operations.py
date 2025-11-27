"""
Stripe checkout and billing portal operations.
"""

import stripe
from fastapi import HTTPException


class CheckoutOperations:
    """Handles checkout and billing portal-related Stripe operations."""

    @staticmethod
    def create_checkout_session(
        price_id: str,
        customer_email: str,
        user_id: str,
        success_url: str,
        cancel_url: str,
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

    @staticmethod
    def create_billing_portal_session(
        stripe_customer_id: str, return_url: str
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
