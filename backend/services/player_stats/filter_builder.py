"""
Filter building utilities for player stats queries.
"""


class FilterBuilder:
    """Builds SQL filter clauses for player statistics queries."""

    # Stats that should not be divided (already percentages/ratios or special fields)
    NON_COUNTING_STATS = {
        "completion_percentage",
        "huck_percentage",
        "offensive_efficiency",
        "yards_per_turn",
        "yards_per_completion",
        "yards_per_reception",
        "assists_per_turnover",
        "games_played",
        "full_name",
    }

    # Valid operators for security
    VALID_OPERATORS = {">", "<", ">=", "<=", "="}

    @staticmethod
    def build_having_clause(
        custom_filters: list,
        per_game: bool = False,
        table_prefix: str = "",
        alias_mapping: dict = None,
    ) -> str:
        """
        Build a HAVING clause from custom filters.

        Args:
            custom_filters: List of filter dicts with 'field', 'operator', and 'value'
            per_game: Whether to apply per-game conversion to counting stats
            table_prefix: Prefix for field names (e.g., 'tcs.' for team_career_stats CTE)
            alias_mapping: Optional dict mapping field aliases to full SQL expressions

        Returns:
            HAVING clause string (without "HAVING" keyword) or empty string
        """
        if not custom_filters:
            return ""

        conditions = []
        for f in custom_filters:
            field = f.get("field", "")
            operator = f.get("operator", "")
            value = f.get("value", 0)

            # Validate operator
            if operator not in FilterBuilder.VALID_OPERATORS:
                continue

            # Validate field (basic SQL injection protection)
            if not field or not field.replace("_", "").isalnum():
                continue

            # Build field reference
            field_ref = FilterBuilder._build_field_reference(
                field, per_game, table_prefix, alias_mapping
            )

            # Build condition
            try:
                # Ensure value is numeric
                numeric_value = float(value)
                conditions.append(f"{field_ref} {operator} {numeric_value}")
            except (ValueError, TypeError):
                continue

        return " AND ".join(conditions) if conditions else ""

    @staticmethod
    def _build_field_reference(
        field: str,
        per_game: bool,
        table_prefix: str,
        alias_mapping: dict = None,
    ) -> str:
        """
        Build the field reference for a filter condition.

        Args:
            field: Field name
            per_game: Whether to apply per-game conversion
            table_prefix: Prefix for field names
            alias_mapping: Optional alias to SQL expression mapping

        Returns:
            Field reference string
        """
        # Check if this field has an alias mapping (for calculated columns)
        if alias_mapping and field in alias_mapping:
            return alias_mapping[field]

        # For per-game filters on counting stats, divide by games_played
        if per_game and field not in FilterBuilder.NON_COUNTING_STATS:
            if table_prefix:
                return f"CASE WHEN COALESCE(gc.games_played, 0) > 0 THEN CAST({table_prefix}{field} AS NUMERIC) / gc.games_played ELSE 0 END"
            else:
                return f"CASE WHEN games_played > 0 THEN CAST({field} AS NUMERIC) / games_played ELSE 0 END"

        # Otherwise use the column directly
        return f"{table_prefix}{field}" if table_prefix else field

    @staticmethod
    def get_team_career_sort_column(sort_key: str, per_game: bool = False) -> str:
        """
        Get the sort column for team career stats queries.
        Handles per-game sorting by dividing counting stats by games_played.

        Args:
            sort_key: Field to sort by
            per_game: Whether to apply per-game conversion

        Returns:
            Sort column SQL expression
        """
        # If per_game mode and this is a counting stat, divide by games_played
        if per_game and sort_key not in FilterBuilder.NON_COUNTING_STATS:
            # Use COALESCE to handle the LEFT JOIN case where gc.games_played might be NULL
            return f"CASE WHEN COALESCE(gc.games_played, 0) > 0 THEN CAST(tcs.{sort_key} AS NUMERIC) / gc.games_played ELSE 0 END"

        # Otherwise use the column directly from team_career_stats CTE
        return f"tcs.{sort_key}"
