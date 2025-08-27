#!/usr/bin/env python3
"""
Monitor and display UFA data import status.
Shows progress, coverage statistics, and identifies problematic games.
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Add backend to path to import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sql_database import get_db


class ImportStatusMonitor:
    """Monitor UFA data import progress and status."""
    
    def __init__(self):
        self.db = get_db()
        self.progress_file = Path('import_progress.json')
    
    def get_import_coverage(self) -> Dict[str, Any]:
        """Get detailed import coverage statistics."""
        
        # Overall statistics
        total_games_query = "SELECT COUNT(*) as count FROM games WHERE year >= 2012"
        total_games = self.db.execute_query(total_games_query)[0]["count"]
        
        imported_games_query = """
        SELECT COUNT(DISTINCT game_id) as count 
        FROM player_game_stats 
        WHERE game_id NOT LIKE '%season_summary%'
        """
        imported_games = self.db.execute_query(imported_games_query)[0]["count"]
        
        total_player_records_query = """
        SELECT COUNT(*) as count 
        FROM player_game_stats 
        WHERE game_id NOT LIKE '%season_summary%'
        """
        total_player_records = self.db.execute_query(total_player_records_query)[0]["count"]
        
        # Coverage by year
        year_coverage_query = """
        SELECT 
            g.year,
            COUNT(DISTINCT g.game_id) as total_games,
            COUNT(DISTINCT pgs.game_id) as games_with_stats,
            ROUND(COUNT(DISTINCT pgs.game_id) * 100.0 / COUNT(DISTINCT g.game_id), 1) as coverage_percent
        FROM games g
        LEFT JOIN player_game_stats pgs ON g.game_id = pgs.game_id 
            AND pgs.game_id NOT LIKE '%season_summary%'
        WHERE g.year >= 2012
        GROUP BY g.year
        ORDER BY g.year DESC
        """
        year_coverage = self.db.execute_query(year_coverage_query)
        
        return {
            "total_games": total_games,
            "imported_games": imported_games,
            "coverage_percent": round(imported_games / total_games * 100, 1) if total_games > 0 else 0,
            "total_player_records": total_player_records,
            "year_coverage": year_coverage
        }
    
    def get_progress_info(self) -> Dict[str, Any]:
        """Get progress information from the progress file."""
        if not self.progress_file.exists():
            return {
                "file_exists": False,
                "failed_games": [],
                "last_update": None
            }
        
        try:
            with open(self.progress_file, 'r') as f:
                data = json.load(f)
                return {
                    "file_exists": True,
                    "failed_games": data.get('failed_games', []),
                    "last_update": data.get('last_update'),
                    "stats_imported": data.get('stats_imported', 0),
                    "games_processed": data.get('games_processed', 0)
                }
        except Exception as e:
            return {
                "file_exists": True,
                "error": str(e),
                "failed_games": []
            }
    
    def get_sample_imported_games(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get sample of successfully imported games."""
        query = """
        SELECT 
            pgs.game_id,
            COUNT(*) as player_count,
            MIN(pgs.year) as year,
            MIN(g.start_timestamp) as game_date
        FROM player_game_stats pgs
        LEFT JOIN games g ON pgs.game_id = g.game_id
        WHERE pgs.game_id NOT LIKE '%season_summary%'
        GROUP BY pgs.game_id
        ORDER BY MIN(g.start_timestamp) DESC
        LIMIT :limit
        """
        return self.db.execute_query(query, {"limit": limit})
    
    def get_games_missing_stats(self, year: int = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get games that are missing statistics."""
        if year:
            query = """
            SELECT g.game_id, g.year, g.start_timestamp, g.home_team_id, g.away_team_id
            FROM games g
            LEFT JOIN player_game_stats pgs ON g.game_id = pgs.game_id
            WHERE pgs.game_id IS NULL AND g.year = :year
            ORDER BY g.start_timestamp DESC
            LIMIT :limit
            """
            params = {"year": year, "limit": limit}
        else:
            query = """
            SELECT g.game_id, g.year, g.start_timestamp, g.home_team_id, g.away_team_id
            FROM games g
            LEFT JOIN player_game_stats pgs ON g.game_id = pgs.game_id
            WHERE pgs.game_id IS NULL AND g.year >= 2012
            ORDER BY g.start_timestamp DESC
            LIMIT :limit
            """
            params = {"limit": limit}
        
        return self.db.execute_query(query, params)
    
    def display_status(self):
        """Display comprehensive import status."""
        print("UFA Data Import Status")
        print("=" * 50)
        
        # Get coverage data
        coverage = self.get_import_coverage()
        
        print(f"Overall Progress:")
        print(f"  Total games in database: {coverage['total_games']:,}")
        print(f"  Games with imported stats: {coverage['imported_games']:,}")
        print(f"  Coverage: {coverage['coverage_percent']}%")
        print(f"  Total player records: {coverage['total_player_records']:,}")
        print()
        
        # Year-by-year breakdown
        print("Coverage by Year:")
        print("  Year    Total   Imported   Coverage")
        print("  ----   -------  --------   --------")
        
        for year_data in coverage['year_coverage']:
            year = year_data['year']
            total = year_data['total_games']
            imported = year_data['games_with_stats'] or 0
            percent = year_data['coverage_percent'] or 0.0
            
            print(f"  {year}    {total:>4}      {imported:>4}      {percent:>5.1f}%")
        
        print()
        
        # Progress file information
        progress = self.get_progress_info()
        
        if progress['file_exists']:
            if 'error' in progress:
                print(f"Progress file error: {progress['error']}")
            else:
                print("Last Import Session:")
                if progress['last_update']:
                    update_time = datetime.fromisoformat(progress['last_update'].replace('Z', '+00:00'))
                    print(f"  Last update: {update_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                print(f"  Games processed: {progress.get('games_processed', 'Unknown')}")
                print(f"  Player records imported: {progress.get('stats_imported', 'Unknown')}")
                print(f"  Failed games logged: {len(progress.get('failed_games', []))}")
                
                if progress.get('failed_games'):
                    print(f"  Sample failed games: {', '.join(progress['failed_games'][:5])}")
                    if len(progress['failed_games']) > 5:
                        print(f"    ... and {len(progress['failed_games']) - 5} more")
        else:
            print("No progress file found (no previous import sessions)")
        
        print()
        
        # Sample imported games
        sample_games = self.get_sample_imported_games(5)
        if sample_games:
            print("Recently Imported Games:")
            for game in sample_games:
                game_id = game['game_id']
                player_count = game['player_count']
                year = game.get('year', 'Unknown')
                print(f"  {game_id} ({year}): {player_count} players")
        
        print()
        
        # Missing stats for recent years
        print("Recent Games Missing Stats:")
        missing_recent = self.get_games_missing_stats(2025, 5)
        if missing_recent:
            for game in missing_recent:
                game_id = game['game_id']
                teams = f"{game['away_team_id']} @ {game['home_team_id']}"
                date = game.get('start_timestamp', 'Unknown date')
                print(f"  {game_id}: {teams} ({date[:10] if date else 'No date'})")
        else:
            print("  All 2025 games have stats!")
        
        print()
        
        # Recommendations
        print("Recommendations:")
        
        if coverage['coverage_percent'] < 80:
            print("  • Run full import: python scripts/fetch_ufa_game_stats.py")
        
        if progress.get('failed_games'):
            print("  • Retry failed games: python scripts/fetch_ufa_game_stats.py --retry-failed")
        
        if coverage['year_coverage'] and coverage['year_coverage'][0]['coverage_percent'] < 90:
            recent_year = coverage['year_coverage'][0]['year']
            print(f"  • Focus on recent year: python scripts/fetch_ufa_game_stats.py --limit 200")
            print(f"    (prioritizes {recent_year} games first)")
        
        print("  • Check this status: python scripts/import_status.py")


def main():
    """Main function to show import status."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Show UFA data import status")
    parser.add_argument("--year", type=int, help="Focus on specific year")
    parser.add_argument("--missing", type=int, default=10, help="Number of missing games to show")
    args = parser.parse_args()
    
    monitor = ImportStatusMonitor()
    
    try:
        monitor.display_status()
        
        if args.year:
            print(f"\nDetailed view for {args.year}:")
            missing = monitor.get_games_missing_stats(args.year, args.missing)
            print(f"Games missing stats in {args.year}: {len(missing)}")
            for game in missing[:args.missing]:
                teams = f"{game['away_team_id']} @ {game['home_team_id']}"
                date = game.get('start_timestamp', 'No date')
                print(f"  {game['game_id']}: {teams} ({date[:10] if date else 'No date'})")
            
    except Exception as e:
        print(f"Error generating status report: {e}")
        raise
    finally:
        monitor.db.close()


if __name__ == "__main__":
    main()