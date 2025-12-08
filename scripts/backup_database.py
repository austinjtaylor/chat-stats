#!/usr/bin/env python3
"""
Database backup utility for sports stats application.

This script creates timestamped backups of the PostgreSQL database (Supabase)
and manages backup retention to prevent storage bloat.

Requires: pg_dump and psql (install via: brew install libpq)
"""

import argparse
import gzip
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def get_database_url() -> str:
    """Get the DATABASE_URL from environment."""
    load_dotenv(get_project_root() / ".env")
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL not set in environment")
    return url


def get_backups_dir() -> Path:
    """Get the backups directory."""
    backups_dir = get_project_root() / "backups"
    backups_dir.mkdir(exist_ok=True)
    return backups_dir


def find_pg_dump() -> str:
    """Find pg_dump executable path."""
    # Check common locations
    paths = [
        "/opt/homebrew/opt/libpq/bin/pg_dump",  # macOS Homebrew (Apple Silicon)
        "/usr/local/opt/libpq/bin/pg_dump",  # macOS Homebrew (Intel)
        "/opt/homebrew/bin/pg_dump",
        "/usr/local/bin/pg_dump",
        "/usr/bin/pg_dump",
    ]
    for path in paths:
        if Path(path).exists():
            return path
    # Try to find in PATH
    result = shutil.which("pg_dump")
    if result:
        return result
    raise FileNotFoundError(
        "pg_dump not found. Install PostgreSQL client tools: brew install libpq"
    )


def find_psql() -> str:
    """Find psql executable path."""
    paths = [
        "/opt/homebrew/opt/libpq/bin/psql",
        "/usr/local/opt/libpq/bin/psql",
        "/opt/homebrew/bin/psql",
        "/usr/local/bin/psql",
        "/usr/bin/psql",
    ]
    for path in paths:
        if Path(path).exists():
            return path
    result = shutil.which("psql")
    if result:
        return result
    raise FileNotFoundError(
        "psql not found. Install PostgreSQL client tools: brew install libpq"
    )


def create_backup(compress: bool = False) -> Path:
    """
    Create a timestamped backup of the PostgreSQL database using pg_dump.

    Args:
        compress: Whether to compress the backup with gzip

    Returns:
        Path to the created backup file
    """
    pg_dump = find_pg_dump()
    db_url = get_database_url()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backups_dir = get_backups_dir()

    if compress:
        # Create uncompressed first, then compress
        temp_path = backups_dir / f"sports_stats_{timestamp}.sql"
        backup_path = backups_dir / f"sports_stats_{timestamp}.sql.gz"

        result = subprocess.run(
            [pg_dump, db_url, "--no-owner", "--no-acl", "-f", str(temp_path)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"pg_dump failed: {result.stderr}")

        # Compress the file
        with open(temp_path, "rb") as f_in:
            with gzip.open(backup_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        temp_path.unlink()  # Remove uncompressed file
    else:
        backup_path = backups_dir / f"sports_stats_{timestamp}.sql"
        result = subprocess.run(
            [pg_dump, db_url, "--no-owner", "--no-acl", "-f", str(backup_path)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"pg_dump failed: {result.stderr}")

    size_mb = backup_path.stat().st_size / (1024 * 1024)
    print(f"Backup created: {backup_path} ({size_mb:.1f} MB)")
    return backup_path


def list_backups() -> list[Path]:
    """List all backup files sorted by creation time (newest first)."""
    backups_dir = get_backups_dir()
    backups = []

    for pattern in ["sports_stats_*.sql", "sports_stats_*.sql.gz"]:
        backups.extend(backups_dir.glob(pattern))

    return sorted(backups, key=lambda p: p.stat().st_mtime, reverse=True)


def cleanup_old_backups(keep_count: int = 5) -> None:
    """
    Remove old backup files, keeping only the most recent ones.

    Args:
        keep_count: Number of recent backups to keep
    """
    backups = list_backups()

    if len(backups) <= keep_count:
        print(f"Found {len(backups)} backups, keeping all (limit: {keep_count})")
        return

    to_remove = backups[keep_count:]
    print(f"Removing {len(to_remove)} old backups (keeping {keep_count} most recent)")

    for backup_path in to_remove:
        backup_path.unlink()
        print(f"Removed: {backup_path.name}")


def restore_backup(backup_path: Path) -> None:
    """
    Restore PostgreSQL database from a SQL dump.

    WARNING: This will overwrite existing data in the database.

    Args:
        backup_path: Path to the backup file to restore
    """
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")

    psql = find_psql()
    db_url = get_database_url()

    # Create backup of current database before restore
    print("Creating safety backup before restore...")
    safety_backup = create_backup(compress=True)
    print(f"Safety backup created: {safety_backup}")

    print(f"\nRestoring from: {backup_path}")
    print("WARNING: This will overwrite existing data!")

    if backup_path.suffix == ".gz":
        # Decompress and pipe to psql
        with gzip.open(backup_path, "rt") as f:
            result = subprocess.run(
                [psql, db_url],
                input=f.read(),
                capture_output=True,
                text=True,
            )
    else:
        result = subprocess.run(
            [psql, db_url, "-f", str(backup_path)],
            capture_output=True,
            text=True,
        )

    if result.returncode != 0:
        print(f"Restore completed with warnings/errors:\n{result.stderr}")
    else:
        print("Database restored successfully")


def main():
    """Main command-line interface."""
    parser = argparse.ArgumentParser(
        description="PostgreSQL database backup utility for Supabase"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Backup command
    backup_parser = subparsers.add_parser(
        "backup", help="Create PostgreSQL database backup using pg_dump"
    )
    backup_parser.add_argument(
        "--compress", "-c", action="store_true", help="Compress backup with gzip"
    )
    backup_parser.add_argument(
        "--cleanup",
        "-k",
        type=int,
        default=None,
        help="Keep N most recent backups after creating new one",
    )

    # List command
    subparsers.add_parser("list", help="List all backups")

    # Restore command
    restore_parser = subparsers.add_parser(
        "restore", help="Restore database from backup (WARNING: overwrites data)"
    )
    restore_parser.add_argument("backup_file", help="Backup file to restore from")

    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Remove old backups")
    cleanup_parser.add_argument(
        "--keep",
        "-k",
        type=int,
        default=5,
        help="Number of backups to keep (default: 5)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == "backup":
            create_backup(compress=args.compress)
            if args.cleanup:
                cleanup_old_backups(keep_count=args.cleanup)

        elif args.command == "list":
            backups = list_backups()
            if not backups:
                print("No backups found")
            else:
                print(f"Found {len(backups)} backup(s):")
                for backup in backups:
                    size_mb = backup.stat().st_size / (1024 * 1024)
                    mtime = datetime.fromtimestamp(backup.stat().st_mtime)
                    print(
                        f"  {backup.name} ({size_mb:.1f} MB, "
                        f"{mtime.strftime('%Y-%m-%d %H:%M:%S')})"
                    )

        elif args.command == "restore":
            backup_path = Path(args.backup_file)
            if not backup_path.is_absolute():
                backup_path = get_backups_dir() / backup_path
            restore_backup(backup_path)

        elif args.command == "cleanup":
            cleanup_old_backups(keep_count=args.keep)

    except Exception as e:
        print(f"Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
