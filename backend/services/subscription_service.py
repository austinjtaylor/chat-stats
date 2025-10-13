"""
Subscription management service.
Handles tier validation, query limits, and subscription updates.
"""

from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import text

from data.database import SQLDatabase
from models.subscription import SUBSCRIPTION_TIERS, UserSubscription


class SubscriptionService:
    """Service for managing user subscriptions and access control."""

    def __init__(self, db: SQLDatabase):
        """Initialize subscription service."""
        self.db = db

    def get_user_subscription(self, user_id: str) -> Optional[UserSubscription]:
        """
        Get a user's subscription details.

        Args:
            user_id: User's UUID

        Returns:
            UserSubscription or None if not found
        """
        query = """
        SELECT
            user_id,
            tier,
            status,
            queries_this_month,
            query_limit,
            current_period_end,
            cancel_at_period_end
        FROM user_subscriptions
        WHERE user_id = :user_id
        """

        results = self.db.execute_query(query, {"user_id": user_id})

        if not results:
            return None

        sub = results[0]
        return UserSubscription(
            user_id=str(sub["user_id"]),
            tier=sub["tier"],
            status=sub["status"],
            queries_this_month=sub["queries_this_month"],
            query_limit=sub["query_limit"],
            current_period_end=sub.get("current_period_end"),
            cancel_at_period_end=sub.get("cancel_at_period_end", False),
            at_query_limit=sub["queries_this_month"] >= sub["query_limit"],
        )

    def check_query_limit(self, user_id: str) -> bool:
        """
        Check if user has queries remaining.

        Args:
            user_id: User's UUID

        Returns:
            True if user can make more queries

        Raises:
            HTTPException: If user is at query limit
        """
        subscription = self.get_user_subscription(user_id)

        if not subscription:
            raise HTTPException(
                status_code=404, detail="Subscription not found"
            )

        if subscription.at_query_limit:
            # Format reset date for display
            reset_date = None
            if subscription.current_period_end:
                reset_date = subscription.current_period_end.strftime("%B %d, %Y")

            # Customize message based on tier
            if subscription.tier == "free":
                message = f"Query limit reached ({subscription.query_limit}/month). Upgrade to continue."
            else:
                # Pro tier - no upgrade option, show reset date
                if reset_date:
                    message = f"Query limit reached ({subscription.query_limit}/month). Your queries will reset on {reset_date}."
                else:
                    message = f"Query limit reached ({subscription.query_limit}/month). Your queries will reset on the 1st of next month."

            raise HTTPException(
                status_code=429,
                detail={
                    "message": message,
                    "tier": subscription.tier,
                    "queries_used": subscription.queries_this_month,
                    "query_limit": subscription.query_limit,
                    "reset_date": reset_date,
                },
            )

        return True

    def increment_query_count(self, user_id: str) -> None:
        """
        Increment the user's query count for the current month.

        Args:
            user_id: User's UUID
        """
        query = """
        UPDATE user_subscriptions
        SET queries_this_month = queries_this_month + 1
        WHERE user_id = :user_id
        """

        self.db.execute_query(query, {"user_id": user_id})

    def reset_monthly_queries(self, user_id: str) -> None:
        """
        Reset the user's monthly query count (called on billing cycle).

        Args:
            user_id: User's UUID
        """
        query = """
        UPDATE user_subscriptions
        SET queries_this_month = 0
        WHERE user_id = :user_id
        """

        self.db.execute_query(query, {"user_id": user_id})

    def update_subscription_from_stripe(
        self,
        user_id: str,
        stripe_customer_id: str,
        stripe_subscription_id: str,
        stripe_price_id: str,
        tier: str,
        status: str,
        current_period_start: datetime,
        current_period_end: datetime,
    ) -> None:
        """
        Update subscription details from Stripe webhook.

        Args:
            user_id: User's UUID
            stripe_customer_id: Stripe Customer ID
            stripe_subscription_id: Stripe Subscription ID
            stripe_price_id: Stripe Price ID
            tier: Subscription tier ('free', 'pro', 'enterprise')
            status: Subscription status
            current_period_start: Current billing period start
            current_period_end: Current billing period end
        """
        tier_config = SUBSCRIPTION_TIERS.get(tier)
        if not tier_config:
            raise ValueError(f"Invalid tier: {tier}")

        query = """
        UPDATE user_subscriptions
        SET
            tier = :tier,
            status = :status,
            stripe_customer_id = :stripe_customer_id,
            stripe_subscription_id = :stripe_subscription_id,
            stripe_price_id = :stripe_price_id,
            current_period_start = :current_period_start,
            current_period_end = :current_period_end,
            query_limit = :query_limit,
            queries_this_month = 0,
            updated_at = NOW()
        WHERE user_id = :user_id
        """

        self.db.execute_query(
            query,
            {
                "user_id": user_id,
                "tier": tier,
                "status": status,
                "stripe_customer_id": stripe_customer_id,
                "stripe_subscription_id": stripe_subscription_id,
                "stripe_price_id": stripe_price_id,
                "current_period_start": current_period_start,
                "current_period_end": current_period_end,
                "query_limit": tier_config.query_limit,
            },
        )

    def cancel_subscription(self, user_id: str, cancel_at_period_end: bool = True) -> None:
        """
        Mark subscription as canceled.

        Args:
            user_id: User's UUID
            cancel_at_period_end: If True, cancel at end of billing period
        """
        query = """
        UPDATE user_subscriptions
        SET
            cancel_at_period_end = :cancel_at_period_end,
            canceled_at = :canceled_at,
            updated_at = NOW()
        WHERE user_id = :user_id
        """

        self.db.execute_query(
            query,
            {
                "user_id": user_id,
                "cancel_at_period_end": cancel_at_period_end,
                "canceled_at": datetime.now() if cancel_at_period_end else None,
            },
        )

    def reactivate_subscription(self, user_id: str) -> None:
        """
        Reactivate a canceled subscription.

        Args:
            user_id: User's UUID
        """
        query = """
        UPDATE user_subscriptions
        SET
            cancel_at_period_end = FALSE,
            canceled_at = NULL,
            status = 'active',
            updated_at = NOW()
        WHERE user_id = :user_id
        """

        self.db.execute_query(query, {"user_id": user_id})

    def downgrade_to_free(self, user_id: str) -> None:
        """
        Downgrade user to free tier (when subscription ends).

        Args:
            user_id: User's UUID
        """
        free_tier = SUBSCRIPTION_TIERS["free"]

        query = """
        UPDATE user_subscriptions
        SET
            tier = 'free',
            status = 'active',
            stripe_subscription_id = NULL,
            query_limit = :query_limit,
            queries_this_month = 0,
            cancel_at_period_end = FALSE,
            updated_at = NOW()
        WHERE user_id = :user_id
        """

        self.db.execute_query(
            query, {"user_id": user_id, "query_limit": free_tier.query_limit}
        )


def get_subscription_service(db: SQLDatabase) -> SubscriptionService:
    """Factory function to get subscription service instance."""
    return SubscriptionService(db)
