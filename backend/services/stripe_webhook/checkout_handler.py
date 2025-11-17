"""
Stripe checkout event handler.
"""

from datetime import datetime, timedelta


class CheckoutHandler:
    """Handles Stripe checkout.session.completed events."""

    @staticmethod
    def handle_checkout_completed(event, subscription_service, map_price_to_tier_func):
        """
        Handle checkout.session.completed event.

        This event fires when a customer successfully completes a Stripe Checkout session.

        Args:
            event: Stripe event object
            subscription_service: Subscription service instance
            map_price_to_tier_func: Function to map price_id to tier name

        Returns:
            dict: Result status
        """
        import stripe

        session = event.data.object
        user_id = session.metadata.get("user_id")
        stripe_customer_id = session.customer
        stripe_subscription_id = session.subscription

        if not (user_id and stripe_subscription_id):
            return {"status": "skipped", "reason": "Missing user_id or subscription_id"}

        # Get price from checkout session line items (more reliable than subscription)
        line_items = stripe.checkout.Session.list_line_items(session.id, limit=1)
        price_id = line_items.data[0].price.id

        # Map price_id to tier
        tier = map_price_to_tier_func(price_id)

        # Fetch the subscription to get accurate period dates
        subscription = stripe.Subscription.retrieve(stripe_subscription_id)

        # Set the payment method as customer's default (so it shows in payment settings)
        if subscription.get("default_payment_method"):
            try:
                stripe.Customer.modify(
                    stripe_customer_id,
                    invoice_settings={
                        "default_payment_method": subscription["default_payment_method"]
                    },
                )
            except Exception as e:
                # Log but don't fail the webhook if setting default payment method fails
                print(f"Warning: Failed to set default payment method: {e}")

        # Get period dates with fallback (Stripe may not populate these immediately)
        now = datetime.now()
        period_start = subscription.get("current_period_start")
        period_end = subscription.get("current_period_end")

        # Calculate defaults if not available (30 days for monthly subscriptions)
        if not period_start:
            period_start = int(now.timestamp())
        if not period_end:
            period_end = int((now + timedelta(days=30)).timestamp())

        # Update user subscription
        subscription_service.update_subscription_from_stripe(
            user_id=user_id,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            stripe_price_id=price_id,
            tier=tier,
            status="active",
            current_period_start=datetime.fromtimestamp(period_start),
            current_period_end=datetime.fromtimestamp(period_end),
        )

        return {"status": "success", "user_id": user_id, "tier": tier}
