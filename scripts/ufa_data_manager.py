#!/usr/bin/env python3
"""
Unified UFA (Ultimate Frisbee Association) Data Manager - CLI Interface.
This is a thin wrapper around the refactored UFA data management modules.
"""

import logging
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from ufa import UFADataManager

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Main function to run UFA data operations based on command line arguments."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python ufa_data_manager.py import-api [years...]")
        print(
            "  python ufa_data_manager.py import-api-parallel [--workers N] [years...]"
        )
        print("  python ufa_data_manager.py complete-missing [years...]")
        print("")
        print("Examples:")
        print(
            "  python ufa_data_manager.py import-api          # Import all years (sequential)"
        )
        print(
            "  python ufa_data_manager.py import-api 2023     # Import only 2023 (sequential)"
        )
        print(
            "  python ufa_data_manager.py import-api-parallel # Import all years (parallel, auto workers)"
        )
        print(
            "  python ufa_data_manager.py import-api-parallel --workers 4  # Import with 4 workers"
        )
        print(
            "  python ufa_data_manager.py import-api-parallel 2022 2023    # Import specific years (parallel)"
        )
        print(
            "  python ufa_data_manager.py complete-missing    # Complete missing games and season stats"
        )
        sys.exit(1)

    manager = UFADataManager()
    command = sys.argv[1]

    # Parse arguments
    years = None
    workers = None

    if command in ["import-api", "import-api-parallel", "complete-missing"]:
        args = sys.argv[2:]

        # Handle --workers option for parallel command
        if command == "import-api-parallel" and "--workers" in args:
            workers_idx = args.index("--workers")
            if workers_idx + 1 >= len(args):
                print("Error: --workers requires a number")
                sys.exit(1)
            try:
                workers = int(args[workers_idx + 1])
                # Remove --workers and its value from args
                args = args[:workers_idx] + args[workers_idx + 2 :]
            except ValueError:
                print("Error: --workers must be an integer")
                sys.exit(1)

        # Parse remaining arguments as years
        if args:
            try:
                years = [int(y) for y in args]
            except ValueError:
                print("Error: Years must be integers")
                sys.exit(1)

    try:
        if command == "import-api":
            result = manager.import_from_api(years)
            print(f"Successfully imported: {result}")

        elif command == "import-api-parallel":
            result = manager.import_from_api_parallel(years, workers=workers)
            print(f"Successfully imported (parallel): {result}")

        elif command == "complete-missing":
            result = manager.complete_missing_imports(years)
            print(f"Successfully completed missing imports: {result}")

        else:
            print(f"Unknown command: {command}")
            print(
                "Supported commands: 'import-api', 'import-api-parallel', 'complete-missing'"
            )
            sys.exit(1)

    except Exception as e:
        logger.error(f"Operation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
