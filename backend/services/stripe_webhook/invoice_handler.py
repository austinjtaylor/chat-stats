"""
Stripe invoice event handler.
"""


class InvoiceHandler:
    """Handles Stripe invoice.payment_succeeded events."""

    @staticmethod
    def handle_payment_succeeded(event, subscription_service, db):
        """
        Handle invoice.payment_succeeded event.

        This event fires when a recurring payment is successful.

        Args:
            event: Stripe event object
            subscription_service: Subscription service instance
            db: Database instance

        Returns:
            dict: Result status
        """
        invoice = event.data.object
        stripe_subscription_id = invoice.get("subscription")

        if not stripe_subscription_id:
            return {"status": "skipped", "reason": "No subscription_id in invoice"}

        # Reset monthly query count
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
        subscription_service.reset_monthly_queries(user_id)

        return {"status": "success", "user_id": user_id, "action": "reset_queries"}
