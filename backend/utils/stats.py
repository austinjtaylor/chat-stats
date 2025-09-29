"""
Shared utilities for sports statistics tools.
Contains common formatting, validation, and helper functions.
"""

from typing import Any


def format_numeric_value(key: str, value: float) -> Any:
    """
    Format numeric values based on their type.

    Args:
        key: The field name (used to determine formatting rules)
        value: The numeric value to format

    Returns:
        Formatted value (int or float with appropriate precision)
    """
    if isinstance(value, float):
        # For percentages and efficiency metrics, use more precision
        if (
            "percentage" in key.lower()
            or "per_" in key.lower()
            or "efficiency" in key.lower()
        ):
            rounded = round(value, 3) if value < 1 else round(value, 1)
            # Only show decimal if needed
            return int(rounded) if rounded == int(rounded) else rounded
        else:
            # Round to 1 decimal place
            rounded = round(value, 1)
            # Only show decimal if the value actually has a fractional part
            return int(rounded) if rounded == int(rounded) else rounded
    return value


def format_results(
    results: list[dict[str, Any]], max_rows: int = 100
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Format query results with proper numeric formatting and row limiting.

    Args:
        results: Raw query results
        max_rows: Maximum number of rows to return

    Returns:
        Tuple of (formatted_results, metadata)
    """
    formatted_results = []
    for row in results[:max_rows]:
        formatted_row = {}
        for key, value in row.items():
            formatted_row[key] = format_numeric_value(key, value)
        formatted_results.append(formatted_row)

    metadata: dict[str, Any] = {"row_count": len(formatted_results)}
    if len(results) > max_rows:
        metadata["note"] = f"Results limited to first {max_rows} rows"

    return formatted_results, metadata


def validate_query_safety(query: str) -> tuple[bool, str]:
    """
    Validate that a SQL query is safe to execute.

    Args:
        query: SQL query string to validate

    Returns:
        Tuple of (is_safe, error_message)
    """
    query_upper = query.strip().upper()

    # Only allow SELECT statements (including WITH CTEs)
    if not (query_upper.startswith("SELECT") or query_upper.startswith("WITH")):
        return (
            False,
            "Only SELECT queries (including WITH clauses) are allowed for safety",
        )

    # Prevent potentially dangerous operations
    dangerous_keywords = [
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "CREATE",
        "ALTER",
        "TRUNCATE",
    ]

    for keyword in dangerous_keywords:
        if keyword in query_upper:
            return False, f"Query contains forbidden keyword: {keyword}"

    return True, ""


def get_current_season(db: Any) -> int:
    """
    Get the current/latest season from the database.

    Args:
        db: Database connection

    Returns:
        Current season year (defaults to 2025 if not found)
    """
    season_query = "SELECT MAX(year) as current_year FROM player_season_stats"
    season_result = db.execute_query(season_query)

    if season_result and season_result[0].get("current_year"):
        return season_result[0]["current_year"]
    return 2025


def calculate_percentage(
    numerator: int, denominator: int, precision: int = 1
) -> tuple[float, str]:
    """
    Calculate percentage with display string.

    Args:
        numerator: The numerator value
        denominator: The denominator value
        precision: Decimal places for percentage

    Returns:
        Tuple of (percentage_value, display_string)
    """
    if denominator > 0:
        pct = round(numerator / denominator * 100, precision)
        return pct, f"{pct}% ({numerator}/{denominator})"
    return 0.0, "0% (0/0)"
