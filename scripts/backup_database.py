#!/usr/bin/env python3
"""
Database backup utility for sports stats application.

This script creates timestamped backups of the SQLite database and manages
backup retention to prevent storage bloat.
"""

import argparse
import gzip
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def get_database_path() -> Path:
    """Get the path to the main database."""
    return get_project_root() / "db" / "sports_stats.db"


def get_backups_dir() -> Path:
    """Get the backups directory."""
    backups_dir = get_project_root() / "backups"
    backups_dir.mkdir(exist_ok=True)
    return backups_dir


def create_backup(compress: bool = False) -> Path:
    """
    Create a timestamped backup of the database.
    
    Args:
        compress: Whether to compress the backup with gzip
        
    Returns:
        Path to the created backup file
    """
    db_path = get_database_path()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found at {db_path}")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backups_dir = get_backups_dir()
    
    if compress:
        backup_path = backups_dir / f"sports_stats_{timestamp}.db.gz"
        with open(db_path, 'rb') as f_in:
            with gzip.open(backup_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
    else:
        backup_path = backups_dir / f"sports_stats_{timestamp}.db"
        shutil.copy2(db_path, backup_path)
    
    print(f"Backup created: {backup_path}")
    return backup_path


def export_sql_dump() -> Path:
    """
    Export database as SQL dump (version-control friendly).
    
    Returns:
        Path to the created SQL dump file
    """
    db_path = get_database_path()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found at {db_path}")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backups_dir = get_backups_dir()
    dump_path = backups_dir / f"database_dump_{timestamp}.sql"
    
    with sqlite3.connect(db_path) as conn:
        with open(dump_path, 'w') as f:
            for line in conn.iterdump():
                f.write(f"{line}\n")
    
    print(f"SQL dump created: {dump_path}")
    return dump_path


def list_backups() -> List[Path]:
    """List all backup files sorted by creation time (newest first)."""
    backups_dir = get_backups_dir()
    backups = []
    
    for pattern in ["sports_stats_*.db", "sports_stats_*.db.gz", "database_dump_*.sql"]:
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
    Restore database from a backup file.
    
    Args:
        backup_path: Path to the backup file to restore
    """
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")
    
    db_path = get_database_path()
    
    # Create backup of current database before restore
    if db_path.exists():
        current_backup = get_backups_dir() / f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2(db_path, current_backup)
        print(f"Current database backed up to: {current_backup}")
    
    # Restore from backup
    if backup_path.suffix == '.gz':
        with gzip.open(backup_path, 'rb') as f_in:
            with open(db_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
    else:
        shutil.copy2(backup_path, db_path)
    
    print(f"Database restored from: {backup_path}")


def main():
    """Main command-line interface."""
    parser = argparse.ArgumentParser(description="Database backup utility")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Create database backup")
    backup_parser.add_argument("--compress", "-c", action="store_true", help="Compress backup with gzip")
    backup_parser.add_argument("--cleanup", "-k", type=int, default=5, help="Keep N most recent backups (default: 5)")
    
    # SQL dump command
    subparsers.add_parser("dump", help="Export database as SQL dump")
    
    # List command
    subparsers.add_parser("list", help="List all backups")
    
    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore from backup")
    restore_parser.add_argument("backup_file", help="Backup file to restore from")
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Remove old backups")
    cleanup_parser.add_argument("--keep", "-k", type=int, default=5, help="Number of backups to keep (default: 5)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == "backup":
            create_backup(compress=args.compress)
            if args.cleanup:
                cleanup_old_backups(keep_count=args.cleanup)
        
        elif args.command == "dump":
            export_sql_dump()
        
        elif args.command == "list":
            backups = list_backups()
            if not backups:
                print("No backups found")
            else:
                print(f"Found {len(backups)} backup(s):")
                for backup in backups:
                    size_mb = backup.stat().st_size / (1024 * 1024)
                    mtime = datetime.fromtimestamp(backup.stat().st_mtime)
                    print(f"  {backup.name} ({size_mb:.1f} MB, {mtime.strftime('%Y-%m-%d %H:%M:%S')})")
        
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