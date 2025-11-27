"""
Stripe payment method operations.
"""

from typing import Any

import stripe
from fastapi import HTTPException


class PaymentMethodOperations:
    """Handles payment method-related Stripe operations."""

    @staticmethod
    def get_payment_methods(
        stripe_customer_id: str, stripe_subscription_id: str = None
    ) -> dict[str, Any]:
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
                    "invoice_settings.default_payment_method.link",
                ],
            )

            # Get the default payment method
            payment_method = customer.invoice_settings.default_payment_method

            print(
                f"Customer default payment method: {payment_method.id if payment_method else 'None'}"
            )

            # If no default payment method set, try to get from active subscription
            if not payment_method and stripe_subscription_id:
                print(
                    f"No default payment method, checking subscription: {stripe_subscription_id}"
                )
                try:
                    subscription = stripe.Subscription.retrieve(stripe_subscription_id)
                    payment_method_id = subscription.get("default_payment_method")

                    if payment_method_id:
                        print(
                            f"Found payment method on subscription: {payment_method_id}"
                        )
                        # Retrieve the full payment method object
                        payment_method = stripe.PaymentMethod.retrieve(
                            payment_method_id
                        )

                        # Set it as customer's default for future use
                        try:
                            stripe.Customer.modify(
                                stripe_customer_id,
                                invoice_settings={
                                    "default_payment_method": payment_method_id
                                },
                            )
                            print(f"Set {payment_method_id} as customer default")
                        except Exception as e:
                            # Log but don't fail if setting default fails
                            print(f"Warning: Failed to set default payment method: {e}")
                except Exception as e:
                    print(
                        f"Warning: Failed to retrieve payment method from subscription: {e}"
                    )

            if not payment_method:
                print("No payment method found - returning None")
                return None

            print(
                f"Payment method found - ID: {payment_method.id}, Type: {payment_method.type}"
            )

            # Debug: Print the entire payment method object structure
            print(f"Payment method attributes: {dir(payment_method)}")
            print(
                f"Payment method dict: {payment_method.to_dict() if hasattr(payment_method, 'to_dict') else 'N/A'}"
            )

            # Check if Link object has card details
            if hasattr(payment_method, "link") and payment_method.link:
                print(f"Link object: {payment_method.link}")
                print(f"Link attributes: {dir(payment_method.link)}")
                if hasattr(payment_method.link, "to_dict"):
                    print(f"Link dict: {payment_method.link.to_dict()}")

            # Check if payment method has card details
            card_info = None
            link_info = None

            if hasattr(payment_method, "card") and payment_method.card:
                # Regular card payment method
                print(
                    f"Payment method has card details: {payment_method.card.brand} ending in {payment_method.card.last4}"
                )
                card_info = {
                    "brand": payment_method.card.brand,
                    "last4": payment_method.card.last4,
                    "exp_month": payment_method.card.exp_month,
                    "exp_year": payment_method.card.exp_year,
                }
            elif payment_method.type == "link":
                # NOTE: Stripe Link payment methods intentionally hide card details for security/privacy
                # Once a card is saved to Link, Stripe no longer exposes the underlying card information
                # This is a Stripe security feature, not a bug
                print(
                    f"Payment method is type 'link' - card details not available (Stripe security limitation)"
                )

                # Get Link email info
                if hasattr(payment_method, "link") and payment_method.link:
                    link_info = {
                        "email": (
                            payment_method.link.get("email")
                            if hasattr(payment_method.link, "get")
                            else getattr(payment_method.link, "email", None)
                        )
                    }
                    print(
                        f"Link email: {link_info.get('email') if link_info else 'N/A'}"
                    )
            else:
                print(
                    f"Warning: Payment method type '{payment_method.type}' has no card details"
                )
                print(f"Has 'card' attribute: {hasattr(payment_method, 'card')}")
                if hasattr(payment_method, "card"):
                    print(f"Card value: {payment_method.card}")

            # Return simplified payment method info with billing details
            result = {
                "id": payment_method.id,
                "type": payment_method.type,
                "card": card_info,
                "link": link_info,  # Include Link info if available
                "billing_details": (
                    {
                        "name": payment_method.billing_details.name,
                        "email": payment_method.billing_details.email,
                        "phone": payment_method.billing_details.phone,
                        "address": (
                            {
                                "line1": payment_method.billing_details.address.line1,
                                "line2": payment_method.billing_details.address.line2,
                                "city": payment_method.billing_details.address.city,
                                "state": payment_method.billing_details.address.state,
                                "postal_code": payment_method.billing_details.address.postal_code,
                                "country": payment_method.billing_details.address.country,
                            }
                            if payment_method.billing_details.address
                            else None
                        ),
                    }
                    if payment_method.billing_details
                    else None
                ),
            }

            print(
                f"Returning payment method - card: {result['card'] is not None}, link: {result['link'] is not None}"
            )
            return result

        except Exception as e:
            print(f"Error in get_payment_methods: {str(e)}")
            raise HTTPException(
                status_code=400, detail=f"Failed to retrieve payment methods: {str(e)}"
            )

    @staticmethod
    def update_payment_method(stripe_customer_id: str, payment_method_id: str) -> Any:
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
                if pm.type == "link":
                    print(
                        f"Payment method {payment_method_id} is type 'link' - searching for associated card"
                    )

                    # List card payment methods for this customer
                    card_pms = stripe.PaymentMethod.list(
                        customer=stripe_customer_id, type="card", limit=10
                    )

                    # Find the most recently created card (Link should have just created it)
                    if card_pms.data:
                        card_pm = card_pms.data[0]
                        print(
                            f"Found card payment method {card_pm.id} - using this instead of Link PM"
                        )
                        payment_method_id = card_pm.id
                    else:
                        print(
                            f"Warning: No card payment methods found for Link PM {payment_method_id}"
                        )
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
                print(
                    f"Successfully attached payment method {payment_method_id} to customer {stripe_customer_id}"
                )
            except Exception as attach_error:
                # Payment method might already be attached - this is OK
                # Common scenarios:
                # 1. SetupIntent already attached it during confirmation
                # 2. Payment method was saved from previous Link session
                # 3. Payment method was manually attached elsewhere
                error_message = str(attach_error).lower()
                if (
                    "already attached" in error_message
                    or "cannot be attached" in error_message
                ):
                    print(
                        f"Payment method {payment_method_id} already attached to customer {stripe_customer_id} - continuing to set as default"
                    )
                else:
                    # Log unexpected attach errors but continue anyway
                    # The payment method might still be attachable as default even if attach failed
                    print(
                        f"Warning: Unexpected error attaching payment method {payment_method_id}: {attach_error}"
                    )

            # Set as default payment method for invoices
            # This is the critical step - even if attach failed, try to set as default
            customer = stripe.Customer.modify(
                stripe_customer_id,
                invoice_settings={
                    "default_payment_method": payment_method_id,
                },
            )

            print(
                f"Successfully set payment method {payment_method_id} as default for customer {stripe_customer_id}"
            )

            return customer

        except Exception as e:
            # Log the error for debugging
            print(f"Error in update_payment_method: {str(e)}")
            raise HTTPException(
                status_code=400, detail=f"Failed to update payment method: {str(e)}"
            )

    @staticmethod
    def remove_payment_method(
        stripe_customer_id: str, payment_method_id: str
    ) -> dict[str, str]:
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
                stripe_customer_id, expand=["invoice_settings.default_payment_method"]
            )

            # If removing the default payment method, clear it first
            if (
                customer.invoice_settings.default_payment_method
                and customer.invoice_settings.default_payment_method.id
                == payment_method_id
            ):
                stripe.Customer.modify(
                    stripe_customer_id,
                    invoice_settings={"default_payment_method": None},
                )

            # Detach payment method from customer
            stripe.PaymentMethod.detach(payment_method_id)

            return {"message": "Payment method removed successfully"}

        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to remove payment method: {str(e)}"
            )

    @staticmethod
    def create_setup_intent(stripe_customer_id: str) -> dict[str, str]:
        """
        Create a SetupIntent for securely collecting payment method details.

        Args:
            stripe_customer_id: Stripe Customer ID

        Returns:
            Dictionary with client_secret

        Raises:
            HTTPException: If Stripe API call fails
        """
        try:
            setup_intent = stripe.SetupIntent.create(
                customer=stripe_customer_id,
                payment_method_types=["card"],
                # Don't automatically set as default - let update_payment_method handle it
                usage="off_session",
            )

            return {"client_secret": setup_intent["client_secret"]}

        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to create setup intent: {str(e)}"
            )
