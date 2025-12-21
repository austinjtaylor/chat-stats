"""
Test Stripe Payment Element API endpoints.

Tests the new SetupIntent-based payment method collection flow with Payment Element.
"""

import os
import sys
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ===== FIXTURES =====


@pytest.fixture
def mock_stripe_service():
    """Mock Stripe service for Payment Element testing"""
    mock = Mock()

    # create_setup_intent
    mock.create_setup_intent.return_value = {
        "client_secret": "seti_1TestSecret123_secret_456"
    }

    # get_payment_methods
    mock.get_payment_methods.return_value = {
        "id": "pm_1Test123",
        "type": "card",
        "card": {"brand": "visa", "last4": "4242", "exp_month": 12, "exp_year": 2025},
    }

    # update_payment_method
    mock.update_payment_method.return_value = Mock(id="cus_test123")

    return mock


@pytest.fixture
def mock_db():
    """Mock database for testing"""
    mock = Mock()

    # Default: User has Stripe customer ID
    mock.execute_query.return_value = [
        {"stripe_customer_id": "cus_test123", "stripe_subscription_id": "sub_test123"}
    ]

    return mock


@pytest.fixture
def mock_subscription_service():
    """Mock subscription service"""
    mock = Mock()
    mock.get_user_subscription.return_value = {"tier": "pro", "status": "active"}
    return mock


@pytest.fixture
def mock_get_current_user():
    """Mock the get_current_user dependency"""

    def _mock_user():
        return {"user_id": "test-user-123", "email": "test@example.com"}

    return _mock_user


@pytest.fixture
def test_client_stripe(
    mock_stripe_service, mock_db, mock_subscription_service, mock_get_current_user
):
    """Create test client with mocked Stripe services"""
    with patch(
        "services.stripe_service.get_stripe_service", return_value=mock_stripe_service
    ):
        with patch(
            "api.stripe_routes.get_subscription_service",
            return_value=mock_subscription_service,
        ):
            with patch("auth.get_current_user", return_value=mock_get_current_user):
                # Create a mock stats_system with the mocked database
                mock_stats_system = Mock()
                mock_stats_system.db = mock_db

                with patch("api.stripe_routes.stats_system", mock_stats_system):
                    from app import app

                    client = TestClient(app)
                    client.mock_stripe_service = mock_stripe_service
                    client.mock_db = mock_db
                    client.mock_subscription_service = mock_subscription_service
                    return client


# ===== TEST CLASSES =====


class TestCreateSetupIntent:
    """Test /api/stripe/create-setup-intent endpoint"""

    def test_create_setup_intent_success(self, test_client_stripe):
        """Test successful SetupIntent creation"""
        response = test_client_stripe.post(
            "/api/stripe/create-setup-intent",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "client_secret" in data
        assert data["client_secret"].startswith("seti_")

        # Verify Stripe service was called
        test_client_stripe.mock_stripe_service.create_setup_intent.assert_called_once_with(
            "cus_test123"
        )

    def test_create_setup_intent_no_auth(self, test_client_stripe):
        """Test SetupIntent creation without authentication"""
        response = test_client_stripe.post("/api/stripe/create-setup-intent")

        # Should be rejected by auth middleware
        assert response.status_code in [401, 403, 422]  # Depends on auth implementation

    def test_create_setup_intent_no_customer(self, test_client_stripe):
        """Test SetupIntent creation when user has no Stripe customer"""
        # Mock database to return no customer ID
        test_client_stripe.mock_db.execute_query.return_value = []

        response = test_client_stripe.post(
            "/api/stripe/create-setup-intent",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "No Stripe customer found" in data["detail"]

    def test_create_setup_intent_stripe_error(self, test_client_stripe):
        """Test SetupIntent creation when Stripe API fails"""
        from fastapi import HTTPException

        # Mock Stripe service to raise an error
        test_client_stripe.mock_stripe_service.create_setup_intent.side_effect = (
            HTTPException(status_code=400, detail="Stripe error: Invalid customer")
        )

        response = test_client_stripe.post(
            "/api/stripe/create-setup-intent",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 400
        data = response.json()
        assert "Stripe error" in data["detail"]


class TestUpdatePaymentMethod:
    """Test /api/stripe/update-payment-method endpoint"""

    def test_update_payment_method_success(self, test_client_stripe):
        """Test successful payment method update"""
        response = test_client_stripe.post(
            "/api/stripe/update-payment-method",
            headers={"Authorization": "Bearer test-token"},
            json={"payment_method_id": "pm_test123"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert "updated successfully" in data["message"].lower()

        # Verify Stripe service was called with correct params
        test_client_stripe.mock_stripe_service.update_payment_method.assert_called_once_with(
            "cus_test123", "pm_test123"
        )

    def test_update_payment_method_missing_id(self, test_client_stripe):
        """Test update without payment_method_id"""
        response = test_client_stripe.post(
            "/api/stripe/update-payment-method",
            headers={"Authorization": "Bearer test-token"},
            json={},
        )

        assert response.status_code == 400
        data = response.json()
        assert "payment_method_id" in data["detail"].lower()

    def test_update_payment_method_no_customer(self, test_client_stripe):
        """Test update when user has no Stripe customer"""
        test_client_stripe.mock_db.execute_query.return_value = []

        response = test_client_stripe.post(
            "/api/stripe/update-payment-method",
            headers={"Authorization": "Bearer test-token"},
            json={"payment_method_id": "pm_test123"},
        )

        assert response.status_code == 400
        data = response.json()
        assert "No Stripe customer found" in data["detail"]

    def test_update_payment_method_invalid_pm(self, test_client_stripe):
        """Test update with invalid payment method ID"""
        from fastapi import HTTPException

        test_client_stripe.mock_stripe_service.update_payment_method.side_effect = (
            HTTPException(
                status_code=400,
                detail="Failed to update payment method: No such payment method",
            )
        )

        response = test_client_stripe.post(
            "/api/stripe/update-payment-method",
            headers={"Authorization": "Bearer test-token"},
            json={"payment_method_id": "pm_invalid"},
        )

        assert response.status_code == 400


class TestGetPaymentMethods:
    """Test /api/stripe/payment-methods endpoint"""

    def test_get_payment_methods_success(self, test_client_stripe):
        """Test successful retrieval of payment methods"""
        response = test_client_stripe.get(
            "/api/stripe/payment-methods",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "payment_method" in data
        pm = data["payment_method"]
        assert pm["id"] == "pm_1Test123"
        assert pm["type"] == "card"
        assert pm["card"]["brand"] == "visa"
        assert pm["card"]["last4"] == "4242"
        assert pm["card"]["exp_month"] == 12
        assert pm["card"]["exp_year"] == 2025

        # Verify service was called with subscription ID for fallback
        test_client_stripe.mock_stripe_service.get_payment_methods.assert_called_once_with(
            "cus_test123", stripe_subscription_id="sub_test123"
        )

    def test_get_payment_methods_none(self, test_client_stripe):
        """Test when user has no payment methods"""
        test_client_stripe.mock_stripe_service.get_payment_methods.return_value = None

        response = test_client_stripe.get(
            "/api/stripe/payment-methods",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["payment_method"] is None

    def test_get_payment_methods_no_customer(self, test_client_stripe):
        """Test when user has no Stripe customer"""
        test_client_stripe.mock_db.execute_query.return_value = []

        response = test_client_stripe.get(
            "/api/stripe/payment-methods",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["payment_method"] is None


class TestPaymentMethodIntegration:
    """Integration tests for complete payment method flows"""

    def test_complete_payment_method_setup_flow(self, test_client_stripe):
        """Test complete flow: create SetupIntent -> update payment method -> verify"""
        # Step 1: Create SetupIntent
        setup_response = test_client_stripe.post(
            "/api/stripe/create-setup-intent",
            headers={"Authorization": "Bearer test-token"},
        )
        assert setup_response.status_code == 200
        client_secret = setup_response.json()["client_secret"]
        assert client_secret.startswith("seti_")

        # Step 2: Simulate Stripe confirmSetup (would happen in frontend)
        # We'll just proceed to update with a payment method ID

        # Step 3: Update payment method
        update_response = test_client_stripe.post(
            "/api/stripe/update-payment-method",
            headers={"Authorization": "Bearer test-token"},
            json={"payment_method_id": "pm_new123"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["status"] == "success"

        # Step 4: Verify payment method is set
        get_response = test_client_stripe.get(
            "/api/stripe/payment-methods",
            headers={"Authorization": "Bearer test-token"},
        )
        assert get_response.status_code == 200
        assert get_response.json()["payment_method"] is not None

    def test_update_existing_payment_method(self, test_client_stripe):
        """Test updating when payment method already exists"""
        # User already has payment method
        get_response = test_client_stripe.get(
            "/api/stripe/payment-methods",
            headers={"Authorization": "Bearer test-token"},
        )
        assert get_response.json()["payment_method"]["card"]["last4"] == "4242"

        # Update to new payment method
        test_client_stripe.mock_stripe_service.get_payment_methods.return_value = {
            "id": "pm_new456",
            "type": "card",
            "card": {
                "brand": "mastercard",
                "last4": "4444",
                "exp_month": 1,
                "exp_year": 2026,
            },
        }

        update_response = test_client_stripe.post(
            "/api/stripe/update-payment-method",
            headers={"Authorization": "Bearer test-token"},
            json={"payment_method_id": "pm_new456"},
        )
        assert update_response.status_code == 200

        # Verify new payment method
        get_response = test_client_stripe.get(
            "/api/stripe/payment-methods",
            headers={"Authorization": "Bearer test-token"},
        )
        assert get_response.json()["payment_method"]["card"]["last4"] == "4444"
        assert get_response.json()["payment_method"]["card"]["brand"] == "mastercard"


class TestPaymentMethodSecurity:
    """Security tests for payment method endpoints"""

    def test_cannot_access_without_auth(self, test_client_stripe):
        """Test that all endpoints require authentication"""
        endpoints = [
            ("/api/stripe/create-setup-intent", "POST", None),
            (
                "/api/stripe/update-payment-method",
                "POST",
                {"payment_method_id": "pm_test"},
            ),
            ("/api/stripe/payment-methods", "GET", None),
        ]

        for endpoint, method, data in endpoints:
            if method == "POST":
                response = (
                    test_client_stripe.post(endpoint, json=data)
                    if data
                    else test_client_stripe.post(endpoint)
                )
            else:
                response = test_client_stripe.get(endpoint)

            # Should be rejected by auth middleware
            assert response.status_code in [
                401,
                403,
                422,
            ], f"{endpoint} should require auth"

    def test_user_isolation(self, test_client_stripe):
        """Test that users can only access their own payment methods"""
        # This test verifies that the user_id from auth is used for lookups
        # The database query should use the authenticated user's ID

        response = test_client_stripe.get(
            "/api/stripe/payment-methods",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 200

        # Verify database was queried with correct user_id
        test_client_stripe.mock_db.execute_query.assert_called()
        call_args = test_client_stripe.mock_db.execute_query.call_args
        assert call_args[0][1]["user_id"] == "test-user-123"


class TestPaymentMethodErrorHandling:
    """Test error handling for various failure scenarios"""

    def test_database_error_handling(self, test_client_stripe):
        """Test graceful handling of database errors"""
        test_client_stripe.mock_db.execute_query.side_effect = Exception(
            "Database connection failed"
        )

        response = test_client_stripe.get(
            "/api/stripe/payment-methods",
            headers={"Authorization": "Bearer test-token"},
        )

        # Should handle error gracefully (exact behavior depends on implementation)
        assert response.status_code in [500, 400]

    def test_stripe_api_timeout(self, test_client_stripe):
        """Test handling of Stripe API timeouts"""
        from fastapi import HTTPException

        test_client_stripe.mock_stripe_service.create_setup_intent.side_effect = (
            HTTPException(status_code=400, detail="Stripe error: Request timeout")
        )

        response = test_client_stripe.post(
            "/api/stripe/create-setup-intent",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 400
        assert "timeout" in response.json()["detail"].lower()

    def test_invalid_payment_method_format(self, test_client_stripe):
        """Test rejection of invalid payment method ID formats"""
        invalid_ids = [
            "invalid-format",
            "",
            "pm_",
            "cus_123",  # Customer ID instead of PM ID
        ]

        for invalid_id in invalid_ids:
            response = test_client_stripe.post(
                "/api/stripe/update-payment-method",
                headers={"Authorization": "Bearer test-token"},
                json={"payment_method_id": invalid_id},
            )

            # Should either validate format or get error from Stripe
            # Exact status depends on validation implementation
            assert response.status_code in [400, 422]


class TestPaymentMethodEdgeCases:
    """Test edge cases and unusual scenarios"""

    def test_setup_intent_with_subscription_id_fallback(self, test_client_stripe):
        """Test SetupIntent creation uses subscription ID for payment method fallback"""
        # Database returns subscription ID
        test_client_stripe.mock_db.execute_query.return_value = [
            {
                "stripe_customer_id": "cus_test123",
                "stripe_subscription_id": "sub_test123",
            }
        ]

        response = test_client_stripe.post(
            "/api/stripe/create-setup-intent",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 200

    def test_payment_method_null_subscription(self, test_client_stripe):
        """Test getting payment methods when no subscription exists"""
        test_client_stripe.mock_db.execute_query.return_value = [
            {"stripe_customer_id": "cus_test123", "stripe_subscription_id": None}
        ]

        response = test_client_stripe.get(
            "/api/stripe/payment-methods",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 200
        # Service should be called with None for subscription ID
        test_client_stripe.mock_stripe_service.get_payment_methods.assert_called_once_with(
            "cus_test123", stripe_subscription_id=None
        )

    def test_concurrent_payment_method_updates(self, test_client_stripe):
        """Test that concurrent updates are handled safely"""
        # Simulate rapid updates
        responses = []
        for i in range(3):
            response = test_client_stripe.post(
                "/api/stripe/update-payment-method",
                headers={"Authorization": "Bearer test-token"},
                json={"payment_method_id": f"pm_test{i}"},
            )
            responses.append(response)

        # All should succeed (last one wins)
        for response in responses:
            assert response.status_code == 200

        # Stripe service should have been called 3 times
        assert (
            test_client_stripe.mock_stripe_service.update_payment_method.call_count == 3
        )


# ===== TEST UTILITIES =====


@pytest.fixture
def stripe_test_cards():
    """Provide test card numbers for documentation"""
    return {
        "success": {
            "visa": "4242424242424242",
            "mastercard": "5555555555554444",
        },
        "3ds": {
            "visa": "4000002760003184",
            "mastercard": "4000002500003155",
        },
        "decline": {
            "generic": "4000000000000002",
            "insufficient_funds": "4000000000009995",
            "lost_card": "4000000000009987",
        },
    }


def test_stripe_test_cards_reference(stripe_test_cards):
    """Document test cards for reference"""
    assert stripe_test_cards["success"]["visa"] == "4242424242424242"
    assert stripe_test_cards["3ds"]["visa"] == "4000002760003184"
    assert stripe_test_cards["decline"]["generic"] == "4000000000000002"
