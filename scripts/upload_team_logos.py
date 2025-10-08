#!/usr/bin/env python3
"""
Upload Team Logos to Supabase Storage

This script uploads team logo images from the local filesystem to Supabase Storage
and updates the teams table with the public URLs.

Usage:
    python scripts/upload_team_logos.py

    # Or with uv:
    uv run python scripts/upload_team_logos.py

Prerequisites:
    1. Run migration 006_add_team_logo_url.sql first
    2. Ensure SUPABASE_URL and SUPABASE_SERVICE_KEY are in .env
    3. Team logos must exist in frontend/images/team_logos/
"""

import os
import sys
from pathlib import Path

# Add backend to path for imports
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv
from supabase import create_client, Client
from data.database import SQLDatabase
from config import config

# Load environment variables
load_dotenv()

BUCKET_NAME = "team-logos"
LOGOS_DIR = Path(__file__).parent.parent / "frontend" / "images" / "team_logos"


def get_supabase_client() -> Client:
    """Create Supabase client with service role key"""
    supabase_url = config.SUPABASE_URL
    supabase_key = config.SUPABASE_SERVICE_KEY

    if not supabase_url or not supabase_key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment")

    return create_client(supabase_url, supabase_key)


def create_bucket_if_not_exists(supabase: Client):
    """Create the team-logos bucket if it doesn't exist"""
    try:
        # Try to get bucket info
        bucket = supabase.storage.get_bucket(BUCKET_NAME)
        print(f"✓ Bucket '{BUCKET_NAME}' already exists")
        return bucket
    except Exception:
        # Bucket doesn't exist, create it
        print(f"Creating bucket '{BUCKET_NAME}'...")
        bucket = supabase.storage.create_bucket(
            BUCKET_NAME,
            options={
                "public": True,  # Make bucket publicly accessible
                "file_size_limit": 5242880,  # 5MB limit
                "allowed_mime_types": ["image/png", "image/jpeg", "image/jpg"]
            }
        )
        print(f"✓ Created bucket '{BUCKET_NAME}'")
        return bucket


def upload_logo(supabase: Client, file_path: Path) -> str:
    """
    Upload a single logo file to Supabase Storage

    Returns:
        Public URL of the uploaded file
    """
    filename = file_path.name

    # Read file contents
    with open(file_path, 'rb') as f:
        file_contents = f.read()

    # Upload to Supabase Storage
    try:
        # Remove existing file if it exists
        try:
            supabase.storage.from_(BUCKET_NAME).remove([filename])
        except Exception:
            pass  # File doesn't exist, that's fine

        # Upload new file
        result = supabase.storage.from_(BUCKET_NAME).upload(
            filename,
            file_contents,
            file_options={"content-type": "image/png", "upsert": "true"}
        )

        # Get public URL
        public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(filename)

        return public_url
    except Exception as e:
        print(f"✗ Error uploading {filename}: {e}")
        raise


def parse_team_from_filename(filename: str) -> tuple[str, str]:
    """
    Parse city and team name from logo filename

    Example:
        'boston_glory.png' -> ('Boston', 'Glory')
        'los_angeles_aviators.png' -> ('LA', 'Aviators')
        'indianapolis_alley_cats.png' -> ('Indianapolis', 'Alleycats')
    """
    # Remove .png extension
    name = filename.replace('.png', '')

    # Special case mappings (filename -> database values)
    city_mappings = {
        'los_angeles': 'LA',
        'las_angeles': 'LA',  # Handle both spellings
        'salt_lake': 'Salt Lake',
        'san_diego': 'San Diego',
        'new_york': 'New York'
    }

    team_mappings = {
        'alley_cats': 'alleycats',  # Database has 'Alleycats' not 'Alley Cats'
        'wind_chill': 'wind chill'
    }

    parts = name.split('_')

    # Handle multi-word cities
    if '_'.join(parts[:2]) in city_mappings:
        city = city_mappings['_'.join(parts[:2])]
        team = '_'.join(parts[2:])
    else:
        city = parts[0]
        team = '_'.join(parts[1:])

    # Apply team name mappings
    team = team_mappings.get(team, team)

    # Capitalize properly
    city = city.title() if city not in city_mappings.values() else city
    team = team.title()

    return city, team


def update_team_logo_url(db: SQLDatabase, city: str, team_name: str, logo_url: str, year: int = 2025):
    """Update the teams table with the logo URL"""
    query = """
    UPDATE teams
    SET logo_url = :logo_url
    WHERE LOWER(city) = LOWER(:city)
      AND (LOWER(name) = LOWER(:team_name) OR LOWER(name) = LOWER(:team_name_spaces))
      AND year = :year
    """

    # Handle team names with underscores -> spaces
    team_name_spaces = team_name.replace('_', ' ')

    params = {
        "logo_url": logo_url,
        "city": city,
        "team_name": team_name,
        "team_name_spaces": team_name_spaces,
        "year": year
    }

    result = db.execute_query(query, params)
    return result


def main():
    """Main execution function"""
    print("=" * 60)
    print("Team Logo Upload to Supabase Storage")
    print("=" * 60)
    print()

    # Validate logos directory exists
    if not LOGOS_DIR.exists():
        print(f"✗ Error: Logos directory not found: {LOGOS_DIR}")
        return 1

    # Get all PNG files
    logo_files = list(LOGOS_DIR.glob("*.png"))
    if not logo_files:
        print(f"✗ Error: No PNG files found in {LOGOS_DIR}")
        return 1

    print(f"Found {len(logo_files)} logo files")
    print()

    # Initialize Supabase client and database
    try:
        supabase = get_supabase_client()
        db = SQLDatabase(config.DATABASE_URL)
        print("✓ Connected to Supabase and database")
        print()
    except Exception as e:
        print(f"✗ Error connecting to Supabase: {e}")
        return 1

    # Create bucket
    try:
        create_bucket_if_not_exists(supabase)
        print()
    except Exception as e:
        print(f"✗ Error creating bucket: {e}")
        return 1

    # Upload logos and update database
    success_count = 0
    error_count = 0

    print("Uploading logos and updating database...")
    print("-" * 60)

    for logo_file in sorted(logo_files):
        try:
            filename = logo_file.name

            # Upload to Supabase Storage
            public_url = upload_logo(supabase, logo_file)

            # Parse team info from filename
            city, team_name = parse_team_from_filename(filename)

            # Update database
            update_team_logo_url(db, city, team_name, public_url)

            print(f"✓ {filename:35s} -> {city} {team_name}")
            success_count += 1

        except Exception as e:
            print(f"✗ {filename:35s} -> Error: {e}")
            error_count += 1

    print("-" * 60)
    print()
    print("Summary:")
    print(f"  Successful: {success_count}")
    print(f"  Errors: {error_count}")
    print()

    if error_count == 0:
        print("✓ All logos uploaded successfully!")
        return 0
    else:
        print(f"⚠ {error_count} logos failed to upload")
        return 1


if __name__ == "__main__":
    sys.exit(main())
