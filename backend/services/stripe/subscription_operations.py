"""
Stripe subscription operations.
"""

from typing import Any

import stripe
from fastapi import HTTPException


class SubscriptionOperations:
    """Handles subscription-related Stripe operations."""

    @staticmethod
    def get_subscription(subscription_id: str) -> Any:
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

    @staticmethod
    def cancel_subscription(
        subscription_id: str, cancellation_reason: str = "", cancellation_feedback: str = ""
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

    @staticmethod
    def cancel_subscription_immediately(stripe_customer_id: str) -> Any:
        """
        Cancel all subscriptions for a customer immediately (for account deletion).

        Args:
            stripe_customer_id: Stripe Customer ID

        Returns:
            List of canceled subscription objects
        """
        try:
            # Get all active subscriptions for the customer
            subscriptions = stripe.Subscription.list(
                customer=stripe_customer_id, status="active"
            )

            canceled_subs = []
            for sub in subscriptions.data:
                # Cancel immediately (not at period end)
                canceled_sub = stripe.Subscription.cancel(sub.id)
                canceled_subs.append(canceled_sub)

            return canceled_subs
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to cancel subscriptions immediately: {str(e)}",
            )

    @staticmethod
    def reactivate_subscription(subscription_id: str) -> Any:
        """
        Reactivate a subscription that was set to cancel.

        Args:
            subscription_id: Stripe Subscription ID

        Returns:
            Updated Stripe Subscription object
        """
        try:
            return stripe.Subscription.modify(subscription_id, cancel_at_period_end=False)
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to reactivate subscription: {str(e)}"
            )
