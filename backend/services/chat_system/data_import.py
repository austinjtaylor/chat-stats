"""
Data import service.
"""


class DataImportService:
    """Service for importing sports data from various sources."""

    def __init__(self, stats_processor):
        """
        Initialize the data import service.

        Args:
            stats_processor: StatsProcessor instance
        """
        self.stats_processor = stats_processor

    def import_data(self, data_source: str, data_type: str) -> dict[str, int]:
        """
        Import sports data from various sources.

        Args:
            data_source: Path to data file or API endpoint
            data_type: Type of data ('csv', 'json', 'api')

        Returns:
            Dictionary with import statistics
        """
        if data_type == "csv":
            return self._import_csv(data_source)
        elif data_type == "json":
            return self.stats_processor.import_from_json(data_source)
        else:
            raise ValueError(f"Unsupported data type: {data_type}")

    def _import_csv(self, data_source: str) -> dict[str, int]:
        """
        Import CSV data based on filename pattern.

        Args:
            data_source: Path to CSV file

        Returns:
            Dictionary with import count
        """
        # Determine what kind of CSV it is based on filename
        source_lower = data_source.lower()

        if "teams" in source_lower:
            count = self.stats_processor.import_from_csv(data_source, "teams")
            return {"teams_imported": count}
        elif "players" in source_lower:
            count = self.stats_processor.import_from_csv(data_source, "players")
            return {"players_imported": count}
        elif "games" in source_lower:
            count = self.stats_processor.import_from_csv(data_source, "games")
            return {"games_imported": count}
        elif "stats" in source_lower:
            count = self.stats_processor.import_from_csv(data_source, "stats")
            return {"stats_imported": count}
        else:
            raise ValueError(f"Could not determine data type from filename: {data_source}")

    def calculate_season_stats(self, season: str):
        """
        Calculate and store aggregated season statistics.

        Args:
            season: Season identifier (e.g., "2023-24")
        """
        self.stats_processor.calculate_season_stats(season)
