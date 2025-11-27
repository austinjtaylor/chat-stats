"""
Stripe subscription event handlers.
"""

from datetime import datetime, timedelta


class SubscriptionHandler:
    """Handles Stripe subscription-related events."""

    @staticmethod
    def handle_subscription_updated(
        event, subscription_service, db, map_price_to_tier_func
    ):
        """
        Handle customer.subscription.updated event.

        This event fires when a subscription is changed (tier upgrade/downgrade,
        cancellation scheduled, or reactivation).

        Args:
            event: Stripe event object
            subscription_service: Subscription service instance
            db: Database instance
            map_price_to_tier_func: Function to map price_id to tier name

        Returns:
            dict: Result status
        """
        subscription = event.data.object
        stripe_subscription_id = subscription.id

        # Find user
        query = """
        SELECT user_id FROM user_subscriptions
        WHERE stripe_subscription_id = :subscription_id
        """
        result = db.execute_query(query, {"subscription_id": stripe_subscription_id})

        if not result:
            return {
                "status": "skipped",
                "reason": f"No user found for subscription {stripe_subscription_id}",
            }

        user_id = str(result[0]["user_id"])

        if subscription.get("cancel_at_period_end"):
            # User scheduled cancellation
            subscription_service.cancel_subscription(user_id, cancel_at_period_end=True)
            return {
                "status": "success",
                "user_id": user_id,
                "action": "scheduled_cancellation",
            }
        else:
            # Subscription reactivated or upgraded
            price_id = subscription["items"]["data"][0]["price"]["id"]
            tier = map_price_to_tier_func(price_id)

            # Get period dates with fallback
            now = datetime.now()
            period_start = subscription.get(
                "current_period_start", int(now.timestamp())
            )
            period_end = subscription.get(
                "current_period_end", int((now + timedelta(days=30)).timestamp())
            )

            subscription_service.update_subscription_from_stripe(
                user_id=user_id,
                stripe_customer_id=subscription["customer"],
                stripe_subscription_id=stripe_subscription_id,
                stripe_price_id=price_id,
                tier=tier,
                status=subscription["status"],
                current_period_start=datetime.fromtimestamp(period_start),
                current_period_end=datetime.fromtimestamp(period_end),
            )

            return {
                "status": "success",
                "user_id": user_id,
                "action": "updated",
                "tier": tier,
            }

    @staticmethod
    def handle_subscription_deleted(event, subscription_service, db):
        """
        Handle customer.subscription.deleted event.

        This event fires when a subscription is canceled or ended.

        Args:
            event: Stripe event object
            subscription_service: Subscription service instance
            db: Database instance

        Returns:
            dict: Result status
        """
        subscription = event.data.object
        stripe_subscription_id = subscription.id

        # Find user and downgrade to free
        query = """
        SELECT user_id FROM user_subscriptions
        WHERE stripe_subscription_id = :subscription_id
        """
        result = db.execute_query(query, {"subscription_id": stripe_subscription_id})

        if not result:
            return {
                "status": "skipped",
                "reason": f"No user found for subscription {stripe_subscription_id}",
            }

        user_id = str(result[0]["user_id"])
        subscription_service.downgrade_to_free(user_id)

        return {"status": "success", "user_id": user_id, "action": "downgraded_to_free"}
