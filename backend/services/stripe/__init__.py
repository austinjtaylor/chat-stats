"""
Stripe service operations.

Refactored from a 555-line StripeService class into focused operation modules:
- payment_methods.py: Payment method operations (335 lines)
- subscription_operations.py: Subscription management (120 lines)
- invoice_operations.py: Invoice retrieval (49 lines)
- checkout_operations.py: Checkout and billing portal (81 lines)
- webhook_operations.py: Webhook event construction (51 lines)

Total: 636 lines across 5 operation modules
Extracted from monolithic service for better organization and testability.
"""

from .payment_methods import PaymentMethodOperations
from .subscription_operations import SubscriptionOperations
from .invoice_operations import InvoiceOperations
from .checkout_operations import CheckoutOperations
from .webhook_operations import WebhookOperations

__all__ = [
    "PaymentMethodOperations",
    "SubscriptionOperations",
    "InvoiceOperations",
    "CheckoutOperations",
    "WebhookOperations",
]
