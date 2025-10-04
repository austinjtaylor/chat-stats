"""
Subscription and payment data models.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SubscriptionTier(BaseModel):
    """Subscription tier details."""

    name: str  # 'free', 'pro'
    monthly_price: float
    query_limit: int
    features: list[str]


class UserSubscription(BaseModel):
    """User subscription details."""

    user_id: str
    tier: str  # 'free', 'pro'
    status: str  # 'active', 'canceled', 'past_due', 'incomplete'
    queries_this_month: int
    query_limit: int
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False
    at_query_limit: bool


class StripeCheckoutRequest(BaseModel):
    """Request to create Stripe checkout session."""

    price_id: str  # Stripe Price ID
    success_url: str
    cancel_url: str


class StripeCheckoutResponse(BaseModel):
    """Response with Stripe checkout session URL."""

    checkout_url: str
    session_id: str


class StripeBillingPortalRequest(BaseModel):
    """Request to create Stripe billing portal session."""

    return_url: str


class StripeBillingPortalResponse(BaseModel):
    """Response with Stripe billing portal URL."""

    portal_url: str


# Subscription tier configurations
SUBSCRIPTION_TIERS = {
    "free": SubscriptionTier(
        name="free",
        monthly_price=0.0,
        query_limit=10,
        features=[
            "10 AI queries per month",
            "Access to all UFA statistics",
            "Save favorite players and teams",
            "Basic query history",
        ],
    ),
    "pro": SubscriptionTier(
        name="pro",
        monthly_price=4.99,
        query_limit=200,
        features=[
            "200 AI queries per month",
            "Priority response times",
            "Advanced analytics",
            "Export data to CSV",
            "Extended query history",
            "Email support",
        ],
    ),
}
