"""
Stripe invoice operations.
"""

from typing import Any

import stripe
from fastapi import HTTPException


class InvoiceOperations:
    """Handles invoice-related Stripe operations."""

    @staticmethod
    def get_invoices(stripe_customer_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get recent invoices for a customer.

        Args:
            stripe_customer_id: Stripe Customer ID
            limit: Maximum number of invoices to return (default 10)

        Returns:
            List of invoice dictionaries with id, date, amount, status, invoice_pdf
        """
        try:
            # Get invoices for customer
            invoices = stripe.Invoice.list(customer=stripe_customer_id, limit=limit)

            # Format invoice data
            result = []
            for invoice in invoices.data:
                result.append(
                    {
                        "id": invoice.id,
                        "date": invoice.created,
                        "amount_paid": invoice.amount_paid / 100,  # Convert from cents
                        "currency": invoice.currency.upper(),
                        "status": invoice.status,
                        "invoice_pdf": invoice.invoice_pdf,
                        "hosted_invoice_url": invoice.hosted_invoice_url,
                    }
                )

            return result

        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to retrieve invoices: {str(e)}"
            )
