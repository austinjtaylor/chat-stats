"""
Stripe payment and subscription API routes.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from auth import get_current_user
from core.chat_system import get_stats_system
from models.subscription import (
    StripeBillingPortalRequest,
    StripeBillingPortalResponse,
    StripeCheckoutRequest,
    StripeCheckoutResponse,
    SUBSCRIPTION_TIERS,
)
from services.stripe_service import get_stripe_service
from services.subscription_service import get_subscription_service


def create_stripe_routes(stats_system):
    """Create and configure Stripe-related routes."""
    router = APIRouter(prefix="/api/stripe", tags=["stripe"])

    stripe_service = get_stripe_service()

    @router.post("/create-checkout-session", response_model=StripeCheckoutResponse)
    async def create_checkout_session(
        request: StripeCheckoutRequest,
        user: dict = Depends(get_current_user),
    ):
        """
        Create a Stripe Checkout session for subscription payment.

        Requires authentication.
        """
        user_id = user["user_id"]
        user_email = user.get("email", "")

        # Create checkout session
        result = stripe_service.create_checkout_session(
            price_id=request.price_id,
            customer_email=user_email,
            user_id=user_id,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
        )

        return StripeCheckoutResponse(
            checkout_url=result["checkout_url"], session_id=result["session_id"]
        )

    @router.post("/create-billing-portal-session", response_model=StripeBillingPortalResponse)
    async def create_billing_portal_session(
        request: StripeBillingPortalRequest,
        user: dict = Depends(get_current_user),
    ):
        """
        Create a Stripe Billing Portal session for managing subscriptions.

        Requires authentication and an existing Stripe customer.
        """
        user_id = user["user_id"]

        # Get user's subscription to find Stripe customer ID
        subscription_service = get_subscription_service(stats_system.db)
        subscription = subscription_service.get_user_subscription(user_id)

        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        # Get Stripe customer ID from database
        query = """
        SELECT stripe_customer_id
        FROM user_subscriptions
        WHERE user_id = :user_id
        """
        result = stats_system.db.execute_query(query, {"user_id": user_id})

        if not result or not result[0].get("stripe_customer_id"):
            raise HTTPException(
                status_code=400, detail="No Stripe customer found. Please subscribe first."
            )

        stripe_customer_id = result[0]["stripe_customer_id"]

        # Create billing portal session
        portal = stripe_service.create_billing_portal_session(
            stripe_customer_id=stripe_customer_id, return_url=request.return_url
        )

        return StripeBillingPortalResponse(portal_url=portal["portal_url"])

    @router.post("/webhook")
    async def stripe_webhook(
        request: Request, stripe_signature: str = Header(None, alias="Stripe-Signature")
    ):
        """
        Handle Stripe webhook events.

        This endpoint receives notifications from Stripe about subscription events.
        """
        if not stripe_signature:
            raise HTTPException(status_code=400, detail="Missing Stripe signature")

        # Get raw body
        payload = await request.body()

        # Verify and construct the event
        event = stripe_service.construct_webhook_event(payload, stripe_signature)

        subscription_service = get_subscription_service(stats_system.db)

        # Handle different event types
        if event.type == "checkout.session.completed":
            # Payment successful - subscription created
            session = event.data.object
            user_id = session.metadata.get("user_id")
            stripe_customer_id = session.customer
            stripe_subscription_id = session.subscription

            if user_id and stripe_subscription_id:
                # Get the subscription to determine tier
                subscription = stripe_service.get_subscription(stripe_subscription_id)
                price_id = subscription.items.data[0].price.id

                # Map price_id to tier (you'll need to configure these in Stripe)
                tier = _map_price_to_tier(price_id)

                # Update user subscription
                subscription_service.update_subscription_from_stripe(
                    user_id=user_id,
                    stripe_customer_id=stripe_customer_id,
                    stripe_subscription_id=stripe_subscription_id,
                    stripe_price_id=price_id,
                    tier=tier,
                    status="active",
                    current_period_start=datetime.fromtimestamp(
                        subscription.current_period_start
                    ),
                    current_period_end=datetime.fromtimestamp(
                        subscription.current_period_end
                    ),
                )

        elif event.type == "invoice.payment_succeeded":
            # Recurring payment successful
            invoice = event.data.object
            stripe_subscription_id = invoice.subscription

            if stripe_subscription_id:
                # Reset monthly query count
                query = """
                SELECT user_id FROM user_subscriptions
                WHERE stripe_subscription_id = :subscription_id
                """
                result = stats_system.db.execute_query(
                    query, {"subscription_id": stripe_subscription_id}
                )

                if result:
                    user_id = str(result[0]["user_id"])
                    subscription_service.reset_monthly_queries(user_id)

        elif event.type == "customer.subscription.updated":
            # Subscription changed (tier upgrade/downgrade, cancellation scheduled)
            subscription = event.data.object
            stripe_subscription_id = subscription.id

            # Find user
            query = """
            SELECT user_id FROM user_subscriptions
            WHERE stripe_subscription_id = :subscription_id
            """
            result = stats_system.db.execute_query(
                query, {"subscription_id": stripe_subscription_id}
            )

            if result:
                user_id = str(result[0]["user_id"])

                if subscription.cancel_at_period_end:
                    # User scheduled cancellation
                    subscription_service.cancel_subscription(
                        user_id, cancel_at_period_end=True
                    )
                else:
                    # Subscription reactivated or upgraded
                    price_id = subscription.items.data[0].price.id
                    tier = _map_price_to_tier(price_id)

                    subscription_service.update_subscription_from_stripe(
                        user_id=user_id,
                        stripe_customer_id=subscription.customer,
                        stripe_subscription_id=stripe_subscription_id,
                        stripe_price_id=price_id,
                        tier=tier,
                        status=subscription.status,
                        current_period_start=datetime.fromtimestamp(
                            subscription.current_period_start
                        ),
                        current_period_end=datetime.fromtimestamp(
                            subscription.current_period_end
                        ),
                    )

        elif event.type == "customer.subscription.deleted":
            # Subscription canceled/ended
            subscription = event.data.object
            stripe_subscription_id = subscription.id

            # Find user and downgrade to free
            query = """
            SELECT user_id FROM user_subscriptions
            WHERE stripe_subscription_id = :subscription_id
            """
            result = stats_system.db.execute_query(
                query, {"subscription_id": stripe_subscription_id}
            )

            if result:
                user_id = str(result[0]["user_id"])
                subscription_service.downgrade_to_free(user_id)

        return {"status": "success"}

    @router.get("/pricing")
    async def get_pricing():
        """Get available subscription tiers and pricing."""
        return {"tiers": SUBSCRIPTION_TIERS}

    return router


def _map_price_to_tier(price_id: str) -> str:
    """
    Map Stripe Price ID to subscription tier.

    TODO: Configure these in your environment variables or database.
    Create prices in Stripe dashboard and map them here.
    """
    # Example mapping (replace with your actual Stripe price IDs)
    price_tier_map = {
        "price_1234_pro_monthly": "pro",
        "price_5678_enterprise_monthly": "enterprise",
    }

    return price_tier_map.get(price_id, "free")
