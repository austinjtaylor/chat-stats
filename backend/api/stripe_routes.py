"""
Stripe payment and subscription API routes.
"""

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from auth import get_current_user
from core.chat_system import get_stats_system
from middleware.rate_limit import auth_limit, public_limit, no_limit
from models.subscription import (
    StripeBillingPortalRequest,
    StripeBillingPortalResponse,
    StripeCheckoutRequest,
    StripeCheckoutResponse,
    StripeSetupIntentResponse,
    SUBSCRIPTION_TIERS,
)
from services.stripe_service import get_stripe_service
from services.subscription_service import get_subscription_service
from services.stripe_webhook import (
    CheckoutHandler,
    InvoiceHandler,
    SubscriptionHandler,
    map_price_to_tier,
)
from utils.security_logger import log_webhook_event, log_payment_attempt
from utils.validators import validate_price_id, validate_redirect_url, validate_customer_email


def create_stripe_routes(stats_system):
    """Create and configure Stripe-related routes."""
    router = APIRouter(prefix="/api/stripe", tags=["stripe"])

    stripe_service = get_stripe_service()

    @router.post("/create-checkout-session", response_model=StripeCheckoutResponse)
    @auth_limit
    async def create_checkout_session(
        request: Request,
        checkout_request: StripeCheckoutRequest,
        user: dict = Depends(get_current_user),
    ):
        """
        Create a Stripe Checkout session for subscription payment.

        Requires authentication.
        """
        user_id = user["user_id"]
        user_email = user.get("email", "")

        # Validate inputs
        validate_price_id(checkout_request.price_id)
        validate_redirect_url(checkout_request.success_url)
        validate_redirect_url(checkout_request.cancel_url)
        validate_customer_email(user_email)

        # Create checkout session
        result = stripe_service.create_checkout_session(
            price_id=checkout_request.price_id,
            customer_email=user_email,
            user_id=user_id,
            success_url=checkout_request.success_url,
            cancel_url=checkout_request.cancel_url,
        )

        return StripeCheckoutResponse(
            checkout_url=result["checkout_url"], session_id=result["session_id"]
        )

    @router.post("/create-billing-portal-session", response_model=StripeBillingPortalResponse)
    @auth_limit
    async def create_billing_portal_session(
        request: Request,
        portal_request: StripeBillingPortalRequest,
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
        # Note: This may fail if switching from test to live keys
        try:
            portal = stripe_service.create_billing_portal_session(
                stripe_customer_id=stripe_customer_id, return_url=portal_request.return_url
            )
            return StripeBillingPortalResponse(portal_url=portal["portal_url"])
        except HTTPException as e:
            # If customer not found in Stripe (e.g., test customer with live keys)
            if "customer" in str(e.detail).lower() or "not found" in str(e.detail).lower():
                raise HTTPException(
                    status_code=400,
                    detail="Unable to access billing portal. Please cancel your current subscription and subscribe again with live payment information."
                )
            raise

    @router.post("/webhook")
    @no_limit
    async def stripe_webhook(
        request: Request, stripe_signature: str = Header(None, alias="Stripe-Signature")
    ):
        """
        Handle Stripe webhook events.

        This endpoint receives notifications from Stripe about subscription events.
        """
        ip_address = request.client.host if request.client else None

        if not stripe_signature:
            log_webhook_event(
                event_type="unknown",
                verified=False,
                ip_address=ip_address,
                details={"error": "Missing Stripe signature"}
            )
            raise HTTPException(status_code=400, detail="Missing Stripe signature")

        # Get raw body
        payload = await request.body()

        # Verify and construct the event
        try:
            event = stripe_service.construct_webhook_event(payload, stripe_signature)
        except HTTPException as e:
            log_webhook_event(
                event_type="unknown",
                verified=False,
                ip_address=ip_address,
                details={"error": str(e.detail)}
            )
            raise

        # Log successful webhook verification
        log_webhook_event(
            event_type=event.type,
            verified=True,
            ip_address=ip_address,
            details={"event_id": event.id}
        )

        subscription_service = get_subscription_service(stats_system.db)

        # Handle different event types using specialized handlers
        if event.type == "checkout.session.completed":
            CheckoutHandler.handle_checkout_completed(
                event, subscription_service, map_price_to_tier
            )
        elif event.type == "invoice.payment_succeeded":
            InvoiceHandler.handle_payment_succeeded(
                event, subscription_service, stats_system.db
            )
        elif event.type == "customer.subscription.updated":
            SubscriptionHandler.handle_subscription_updated(
                event, subscription_service, stats_system.db, map_price_to_tier
            )
        elif event.type == "customer.subscription.deleted":
            SubscriptionHandler.handle_subscription_deleted(
                event, subscription_service, stats_system.db
            )

        return {"status": "success"}

    @router.get("/pricing")
    @public_limit
    async def get_pricing(request: Request):
        """Get available subscription tiers and pricing."""
        return {"tiers": SUBSCRIPTION_TIERS}

    @router.get("/payment-methods")
    @auth_limit
    async def get_payment_methods(request: Request, user: dict = Depends(get_current_user)):
        """
        Get the user's default payment method from Stripe.

        Requires authentication and an existing Stripe customer.
        """
        user_id = user["user_id"]

        # Get Stripe customer ID and subscription ID from database
        query = """
        SELECT stripe_customer_id, stripe_subscription_id
        FROM user_subscriptions
        WHERE user_id = :user_id
        """
        result = stats_system.db.execute_query(query, {"user_id": user_id})

        if not result or not result[0].get("stripe_customer_id"):
            return {"payment_method": None}

        stripe_customer_id = result[0]["stripe_customer_id"]
        stripe_subscription_id = result[0].get("stripe_subscription_id")

        # Get payment method from Stripe (pass subscription ID for fallback)
        payment_method = stripe_service.get_payment_methods(
            stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id
        )

        return {"payment_method": payment_method}

    @router.get("/invoices")
    @auth_limit
    async def get_invoices(request: Request, user: dict = Depends(get_current_user)):
        """
        Get the user's invoice history from Stripe.

        Requires authentication and an existing Stripe customer.
        """
        user_id = user["user_id"]

        # Get Stripe customer ID from database
        query = """
        SELECT stripe_customer_id
        FROM user_subscriptions
        WHERE user_id = :user_id
        """
        result = stats_system.db.execute_query(query, {"user_id": user_id})

        if not result or not result[0].get("stripe_customer_id"):
            return {"invoices": []}

        stripe_customer_id = result[0]["stripe_customer_id"]

        # Get invoices from Stripe
        invoices = stripe_service.get_invoices(stripe_customer_id, limit=10)

        return {"invoices": invoices}

    @router.post("/cancel-subscription")
    @auth_limit
    async def cancel_subscription_endpoint(request: Request, user: dict = Depends(get_current_user)):
        """
        Cancel the user's subscription (at period end).

        Requires authentication and an active subscription.
        Optionally accepts cancellation_reason and cancellation_feedback.
        """
        user_id = user["user_id"]

        # Parse request body for cancellation feedback
        body = await request.json()
        cancellation_reason = body.get("cancellation_reason", "")
        cancellation_feedback = body.get("cancellation_feedback", "")

        # Get user's subscription
        subscription_service = get_subscription_service(stats_system.db)
        subscription = subscription_service.get_user_subscription(user_id)

        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        # Get Stripe subscription ID from database
        query = """
        SELECT stripe_subscription_id
        FROM user_subscriptions
        WHERE user_id = :user_id
        """
        result = stats_system.db.execute_query(query, {"user_id": user_id})

        if not result or not result[0].get("stripe_subscription_id"):
            raise HTTPException(
                status_code=400, detail="No active subscription found"
            )

        stripe_subscription_id = result[0]["stripe_subscription_id"]

        # Cancel subscription in Stripe
        # Note: This may fail if switching from test to live keys, which is okay
        try:
            stripe_service.cancel_subscription(
                stripe_subscription_id,
                cancellation_reason=cancellation_reason,
                cancellation_feedback=cancellation_feedback
            )
            # Update local database to mark as canceling at period end
            subscription_service.cancel_subscription(user_id, cancel_at_period_end=True)
            return {"status": "success", "message": "Subscription will be canceled at period end"}
        except HTTPException as e:
            # If subscription not found in Stripe (e.g., test subscription with live keys),
            # downgrade to free tier to fully clear the orphaned subscription
            if "subscription" in str(e.detail).lower() or "not found" in str(e.detail).lower():
                subscription_service.downgrade_to_free(user_id)
                return {"status": "success", "message": "Old subscription cleared. You have been moved to the free tier."}
            raise

    @router.post("/update-payment-method")
    @auth_limit
    async def update_payment_method(
        request: Request,
        user: dict = Depends(get_current_user),
    ):
        """
        Update the user's default payment method.

        Requires authentication and an existing Stripe customer.
        """
        user_id = user["user_id"]

        # Parse request body
        body = await request.json()
        payment_method_id = body.get("payment_method_id")

        print(f"Update payment method called - User: {user_id}, Payment Method: {payment_method_id}")

        if not payment_method_id:
            raise HTTPException(status_code=400, detail="payment_method_id is required")

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

        print(f"Updating payment method for customer: {stripe_customer_id}")

        # Update payment method in Stripe
        try:
            stripe_service.update_payment_method(stripe_customer_id, payment_method_id)
            print(f"Payment method updated successfully for customer: {stripe_customer_id}")
            return {"status": "success", "message": "Payment method updated successfully"}
        except HTTPException as e:
            print(f"Error updating payment method: {e.detail}")
            raise

    @router.post("/remove-payment-method")
    @auth_limit
    async def remove_payment_method(
        request: Request,
        user: dict = Depends(get_current_user),
    ):
        """
        Remove (detach) a payment method from the user's Stripe customer.

        Requires authentication and an existing Stripe customer.
        """
        user_id = user["user_id"]

        # Parse request body
        body = await request.json()
        payment_method_id = body.get("payment_method_id")

        if not payment_method_id:
            raise HTTPException(status_code=400, detail="payment_method_id is required")

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

        # Remove payment method in Stripe
        try:
            response = stripe_service.remove_payment_method(stripe_customer_id, payment_method_id)
            return {"status": "success", **response}
        except HTTPException as e:
            raise

    @router.post("/create-setup-intent", response_model=StripeSetupIntentResponse)
    @auth_limit
    async def create_setup_intent(
        request: Request,
        user: dict = Depends(get_current_user),
    ):
        """
        Create a SetupIntent for collecting payment method with Stripe Payment Element.

        Requires authentication and an existing Stripe customer.
        """
        user_id = user["user_id"]

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

        # Create SetupIntent in Stripe
        setup_intent = stripe_service.create_setup_intent(stripe_customer_id)

        return StripeSetupIntentResponse(client_secret=setup_intent["client_secret"])

    return router
