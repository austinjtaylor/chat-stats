"""
Custom SQL query execution tools for sports statistics.
Handles query validation, execution, and result formatting.
"""

from typing import Any

from utils.stats import format_results, validate_query_safety


def execute_custom_query(
    db,
    query: str,
    parameters: dict[str, Any] | None = None,
    explanation: str | None = None,
) -> dict[str, Any]:
    """
    Execute a custom SQL query with safety checks.

    Args:
        db: Database connection
        query: SQL SELECT query to execute
        parameters: Optional parameters for parameterized queries
        explanation: Explanation of what the query does

    Returns:
        Query results as a dictionary
    """
    # Validate query safety
    is_safe, error_message = validate_query_safety(query)
    if not is_safe:
        return {
            "error": error_message,
            "query": query,
        }

    try:
        # Execute the query
        if parameters:
            # Use parameterized query if parameters provided
            results = db.execute_query(query, parameters)
        else:
            # Direct query execution
            results = db.execute_query(query)

        # Format results with row limiting
        formatted_results, metadata = format_results(results)

        return {
            "explanation": explanation or "Custom query results",
            "query": query,
            "parameters": parameters,
            "results": formatted_results,
            **metadata,
        }

    except Exception as e:
        return {
            "error": f"Query execution failed: {str(e)}",
            "query": query,
            "parameters": parameters,
            "explanation": explanation,
        }
