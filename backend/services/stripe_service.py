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
            print(f"Getting payment methods for customer: {stripe_customer_id}")

            # Get customer to find default payment method
            # Try expanding to get full Link data including card details
            customer = stripe.Customer.retrieve(
                stripe_customer_id,
                expand=[
                    "invoice_settings.default_payment_method",
                    "invoice_settings.default_payment_method.link"
                ]
            )

            # Get the default payment method
            payment_method = customer.invoice_settings.default_payment_method

            print(f"Customer default payment method: {payment_method.id if payment_method else 'None'}")

            # If no default payment method set, try to get from active subscription
            if not payment_method and stripe_subscription_id:
                print(f"No default payment method, checking subscription: {stripe_subscription_id}")
                try:
                    subscription = stripe.Subscription.retrieve(stripe_subscription_id)
                    payment_method_id = subscription.get('default_payment_method')

                    if payment_method_id:
                        print(f"Found payment method on subscription: {payment_method_id}")
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
                            print(f"Set {payment_method_id} as customer default")
                        except Exception as e:
                            # Log but don't fail if setting default fails
                            print(f"Warning: Failed to set default payment method: {e}")
                except Exception as e:
                    print(f"Warning: Failed to retrieve payment method from subscription: {e}")

            if not payment_method:
                print("No payment method found - returning None")
                return None

            print(f"Payment method found - ID: {payment_method.id}, Type: {payment_method.type}")

            # Debug: Print the entire payment method object structure
            print(f"Payment method attributes: {dir(payment_method)}")
            print(f"Payment method dict: {payment_method.to_dict() if hasattr(payment_method, 'to_dict') else 'N/A'}")

            # Check if Link object has card details
            if hasattr(payment_method, 'link') and payment_method.link:
                print(f"Link object: {payment_method.link}")
                print(f"Link attributes: {dir(payment_method.link)}")
                if hasattr(payment_method.link, 'to_dict'):
                    print(f"Link dict: {payment_method.link.to_dict()}")

            # Check if payment method has card details
            card_info = None
            link_info = None

            if hasattr(payment_method, 'card') and payment_method.card:
                # Regular card payment method
                print(f"Payment method has card details: {payment_method.card.brand} ending in {payment_method.card.last4}")
                card_info = {
                    "brand": payment_method.card.brand,
                    "last4": payment_method.card.last4,
                    "exp_month": payment_method.card.exp_month,
                    "exp_year": payment_method.card.exp_year,
                }
            elif payment_method.type == 'link':
                # Link payment methods don't expose card details for security/privacy
                # Return Link-specific info instead
                print(f"Payment method is type 'link' - returning Link info")
                if hasattr(payment_method, 'link') and payment_method.link:
                    link_info = {
                        "email": payment_method.link.get('email') if hasattr(payment_method.link, 'get') else getattr(payment_method.link, 'email', None)
                    }
                    print(f"Link email: {link_info['email']}")
            else:
                print(f"Warning: Payment method type '{payment_method.type}' has no card details")
                print(f"Has 'card' attribute: {hasattr(payment_method, 'card')}")
                if hasattr(payment_method, 'card'):
                    print(f"Card value: {payment_method.card}")

            # Return simplified payment method info with billing details
            result = {
                "id": payment_method.id,
                "type": payment_method.type,
                "card": card_info,
                "link": link_info,  # Include Link info if available
                "billing_details": {
                    "name": payment_method.billing_details.name,
                    "email": payment_method.billing_details.email,
                    "phone": payment_method.billing_details.phone,
                    "address": {
                        "line1": payment_method.billing_details.address.line1,
                        "line2": payment_method.billing_details.address.line2,
                        "city": payment_method.billing_details.address.city,
                        "state": payment_method.billing_details.address.state,
                        "postal_code": payment_method.billing_details.address.postal_code,
                        "country": payment_method.billing_details.address.country,
                    } if payment_method.billing_details.address else None
                } if payment_method.billing_details else None
            }

            print(f"Returning payment method - card: {result['card'] is not None}, link: {result['link'] is not None}")
            return result

        except Exception as e:
            print(f"Error in get_payment_methods: {str(e)}")
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
            # Check if this is a Link payment method - if so, find the associated card instead
            try:
                pm = stripe.PaymentMethod.retrieve(payment_method_id)
                if pm.type == 'link':
                    print(f"Payment method {payment_method_id} is type 'link' - searching for associated card")

                    # List card payment methods for this customer
                    card_pms = stripe.PaymentMethod.list(
                        customer=stripe_customer_id,
                        type='card',
                        limit=10
                    )

                    # Find the most recently created card (Link should have just created it)
                    if card_pms.data:
                        card_pm = card_pms.data[0]
                        print(f"Found card payment method {card_pm.id} - using this instead of Link PM")
                        payment_method_id = card_pm.id
                    else:
                        print(f"Warning: No card payment methods found for Link PM {payment_method_id}")
            except Exception as retrieve_error:
                print(f"Warning: Could not check payment method type: {retrieve_error}")

            # Try to attach payment method to customer
            # Note: This may fail if payment method is already attached (e.g., from SetupIntent or previous Link session)
            attach_successful = False
            try:
                stripe.PaymentMethod.attach(
                    payment_method_id,
                    customer=stripe_customer_id,
                )
                attach_successful = True
                print(f"Successfully attached payment method {payment_method_id} to customer {stripe_customer_id}")
            except Exception as attach_error:
                # Payment method might already be attached - this is OK
                # Common scenarios:
                # 1. SetupIntent already attached it during confirmation
                # 2. Payment method was saved from previous Link session
                # 3. Payment method was manually attached elsewhere
                error_message = str(attach_error).lower()
                if "already attached" in error_message or "cannot be attached" in error_message:
                    print(f"Payment method {payment_method_id} already attached to customer {stripe_customer_id} - continuing to set as default")
                else:
                    # Log unexpected attach errors but continue anyway
                    # The payment method might still be attachable as default even if attach failed
                    print(f"Warning: Unexpected error attaching payment method {payment_method_id}: {attach_error}")

            # Set as default payment method for invoices
            # This is the critical step - even if attach failed, try to set as default
            customer = stripe.Customer.modify(
                stripe_customer_id,
                invoice_settings={
                    "default_payment_method": payment_method_id,
                },
            )

            print(f"Successfully set payment method {payment_method_id} as default for customer {stripe_customer_id}")

            return customer

        except Exception as e:
            # Log the error for debugging
            print(f"Error in update_payment_method: {str(e)}")
            raise HTTPException(
                status_code=400, detail=f"Failed to update payment method: {str(e)}"
            )

    def remove_payment_method(self, stripe_customer_id: str, payment_method_id: str) -> dict[str, str]:
        """
        Remove (detach) a payment method from a customer.

        Args:
            stripe_customer_id: Stripe Customer ID
            payment_method_id: Stripe Payment Method ID to remove

        Returns:
            Dictionary with success message

        Raises:
            HTTPException: If Stripe API call fails
        """
        try:
            # Get customer to check if this is the default payment method
            customer = stripe.Customer.retrieve(
                stripe_customer_id,
                expand=["invoice_settings.default_payment_method"]
            )

            # If removing the default payment method, clear it first
            if (customer.invoice_settings.default_payment_method and
                customer.invoice_settings.default_payment_method.id == payment_method_id):
                stripe.Customer.modify(
                    stripe_customer_id,
                    invoice_settings={"default_payment_method": None}
                )

            # Detach payment method from customer
            stripe.PaymentMethod.detach(payment_method_id)

            return {"message": "Payment method removed successfully"}

        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to remove payment method: {str(e)}"
            )

    def create_setup_intent(self, stripe_customer_id: str) -> dict[str, str]:
        """
        Create a SetupIntent for collecting payment method with Payment Element.

        Args:
            stripe_customer_id: Stripe Customer ID

        Returns:
            Dictionary with client_secret for Payment Element

        Raises:
            HTTPException: If Stripe API call fails
        """
        try:
            setup_intent = stripe.SetupIntent.create(
                customer=stripe_customer_id,
                payment_method_types=["card", "link"],  # Match Payment Element configuration
                usage="off_session",  # For future payments
            )

            return {"client_secret": setup_intent.client_secret}

        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to create setup intent: {str(e)}"
            )


# Singleton instance
_stripe_service = None


def get_stripe_service() -> StripeService:
    """Get the singleton Stripe service instance."""
    global _stripe_service
    if _stripe_service is None:
        _stripe_service = StripeService()
    return _stripe_service
