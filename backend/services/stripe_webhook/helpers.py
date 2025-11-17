"""
Stripe webhook helper functions.
"""


def map_price_to_tier(price_id: str) -> str:
    """
    Map Stripe Price ID to subscription tier.

    TODO: Configure these in your environment variables or database.
    Create prices in Stripe dashboard and map them here.

    Args:
        price_id: Stripe price ID

    Returns:
        str: Tier name (pro, free, etc.)
    """
    # Map your actual Stripe price IDs
    price_tier_map = {
        "price_1SHunhFDSSUl9V6nc8jPnWX7": "pro",  # Pro plan: $4.99/month (PRODUCTION)
        "price_1SIsmsFDSSUl9V6nwVqyHUGY": "pro",  # Pro plan: $0.10/month (TEST - LIVE MODE)
    }

    return price_tier_map.get(price_id, "free")
