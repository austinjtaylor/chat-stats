"""
Pass type classification utility.

Classifies throws based on horizontal and vertical distance.
Priority order (evaluated in sequence):
1. Huck: >= 40 vertical yards (long downfield pass)
2. Swing: >= 10 horizontal yards AND primarily lateral (horiz > 2 * |vert|)
3. Gainer: >= 4 vertical yards (forward pass)
4. Dump: < -4 vertical yards (backward pass)
5. Dish: everything else (short pass near the disc)
"""

from typing import Literal

PassType = Literal["dish", "swing", "dump", "huck", "gainer"]

PASS_TYPES: list[PassType] = ["dish", "swing", "dump", "huck", "gainer"]

PASS_TYPE_DISPLAY_NAMES: dict[PassType, str] = {
    "dish": "Dish",
    "swing": "Swing",
    "dump": "Dump",
    "huck": "Huck",
    "gainer": "Gainer",
}


def classify_pass(
    thrower_x: float | None,
    thrower_y: float | None,
    receiver_x: float | None,
    receiver_y: float | None,
) -> PassType | None:
    """
    Classify a pass based on thrower and receiver coordinates.

    Args:
        thrower_x: X coordinate of the thrower
        thrower_y: Y coordinate of the thrower (0-120 yard field)
        receiver_x: X coordinate of the receiver
        receiver_y: Y coordinate of the receiver (0-120 yard field)

    Returns:
        Pass type string ('dish', 'swing', 'dump', 'huck', 'gainer') or None if
        coordinates are missing.

    Classification rules (evaluated in order):
        1. Huck: vertical >= 40 yards (long downfield pass)
        2. Swing: horizontal >= 10 yards AND primarily lateral (horiz > 2*|vert|)
        3. Gainer: vertical >= 4 yards (forward pass)
        4. Dump: vertical < -4 yards (backward pass)
        5. Dish: everything else (short pass near the disc)
    """
    if None in (thrower_x, thrower_y, receiver_x, receiver_y):
        return None

    vertical = receiver_y - thrower_y  # type: ignore[operator]
    horizontal = abs(receiver_x - thrower_x)  # type: ignore[operator]

    # Evaluate in priority order
    # Swing requires the throw to be primarily lateral (horiz > 2 * |vert|)
    if vertical >= 40:
        return "huck"
    elif horizontal >= 10 and horizontal > 2 * abs(vertical):
        return "swing"
    elif vertical >= 4:
        return "gainer"
    elif vertical < -4:
        return "dump"
    else:
        return "dish"


def get_display_name(pass_type: PassType | None) -> str:
    """Get the display name for a pass type."""
    if pass_type is None:
        return "Pass"
    return PASS_TYPE_DISPLAY_NAMES.get(pass_type, "Pass")
