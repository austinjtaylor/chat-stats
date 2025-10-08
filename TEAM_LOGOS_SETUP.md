# Team Logos Setup Guide

This guide walks you through uploading team logos to Supabase Storage and configuring your application to use them.

## Overview

Team logos are stored in Supabase Storage and served via public URLs. This eliminates the need to bundle logo images with your Vercel deployment and allows for easy logo updates.

## Prerequisites

- Supabase project set up (see `SUPABASE_SETUP.md`)
- Environment variables configured (`.env` file)
- Team logos exist in `frontend/images/team_logos/` (26 PNG files)

## Step 1: Run Database Migration

Add the `logo_url` column to the teams table:

1. Go to your Supabase dashboard → **SQL Editor**
2. Create a new query
3. Copy and paste the contents of `backend/migrations/006_add_team_logo_url.sql`
4. Run the migration
5. Verify the column was added:
   ```sql
   SELECT column_name, data_type
   FROM information_schema.columns
   WHERE table_name = 'teams' AND column_name = 'logo_url';
   ```

**Expected result**: Should show `logo_url | text`

## Step 2: Create Supabase Storage Bucket (Manual)

The script will create the bucket automatically, but you can also create it manually:

1. Go to Supabase dashboard → **Storage**
2. Click **New bucket**
3. Configure:
   - **Name**: `team-logos`
   - **Public bucket**: ✅ **Yes** (important for public access)
   - **File size limit**: 5 MB
   - **Allowed MIME types**: `image/png`, `image/jpeg`, `image/jpg`
4. Click **Create bucket**

### Verify Bucket Settings

1. Click on `team-logos` bucket
2. Go to **Policies** tab
3. Ensure public read access is enabled:
   ```sql
   -- Should have a policy like:
   CREATE POLICY "Public Read Access"
   ON storage.objects FOR SELECT
   USING ( bucket_id = 'team-logos' );
   ```

If not, add it:
```sql
-- In Supabase SQL Editor:
CREATE POLICY "Public Read Access"
ON storage.objects FOR SELECT
USING ( bucket_id = 'team-logos' );
```

## Step 3: Upload Logos and Update Database

Run the upload script to upload all 26 team logos and update the database:

```bash
# From project root
uv run python scripts/upload_team_logos.py
```

**Expected output:**
```
============================================================
Team Logo Upload to Supabase Storage
============================================================

Found 26 logo files

✓ Connected to Supabase and database

✓ Bucket 'team-logos' already exists

Uploading logos and updating database...
------------------------------------------------------------
✓ atlanta_hustle.png           -> Atlanta Hustle
✓ austin_sol.png               -> Austin Sol
✓ boston_glory.png             -> Boston Glory
... (22 more)
------------------------------------------------------------

Summary:
  Successful: 26
  Errors: 0

✓ All logos uploaded successfully!
```

### Troubleshooting

**Error: "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set"**
- Make sure `.env` file exists in project root
- Verify `SUPABASE_SERVICE_KEY` is set (not just `SUPABASE_ANON_KEY`)

**Error: "No PNG files found"**
- Check that logos exist in `frontend/images/team_logos/`
- Run: `ls -l frontend/images/team_logos/*.png`

**Error: "Bucket not found"**
- Create the bucket manually (see Step 2)
- Ensure bucket name is exactly `team-logos`

## Step 4: Verify Logo URLs in Database

Check that teams now have logo URLs:

```sql
-- In Supabase SQL Editor:
SELECT team_id, full_name, logo_url
FROM teams
WHERE year = 2025 AND logo_url IS NOT NULL
ORDER BY full_name
LIMIT 5;
```

**Expected result:**
```
team_id          | full_name           | logo_url
-----------------|---------------------|------------------------------------------
ATL2025          | Atlanta Hustle      | https://xxx.supabase.co/storage/v1/object/public/team-logos/atlanta_hustle.png
AUS2025          | Austin Sol          | https://xxx.supabase.co/storage/v1/object/public/team-logos/austin_sol.png
...
```

## Step 5: Test Logo Loading

### Test in Browser

1. Open a Supabase logo URL directly in your browser:
   ```
   https://zqyzqhginapevimhsqyx.supabase.co/storage/v1/object/public/team-logos/boston_glory.png
   ```
   (Replace with your actual Supabase URL)

2. You should see the logo image load

### Test API Response

```bash
# Test that API returns logo URLs
curl http://localhost:8000/api/games/GAME_ID/box-score | jq '.home_team.logo_url'
```

Should return:
```
"https://xxx.supabase.co/storage/v1/object/public/team-logos/team_name.png"
```

### Test in Application

1. Start the development server:
   ```bash
   ./run-dev.sh
   ```

2. Navigate to game stats page:
   ```
   http://localhost:3000/stats/game-detail.html
   ```

3. Inspect Network tab - logos should load from Supabase, not return 404

## Step 6: Deploy Changes

### Commit and Push

```bash
git add .
git commit -m "Add Supabase Storage for team logos"
git push
```

This will trigger:
- Vercel redeploy (frontend changes)
- Railway redeploy (backend changes)

### Run Migration in Production

**Important**: Don't forget to run the migration in your production Supabase:

1. Log into production Supabase dashboard
2. Go to SQL Editor
3. Run `backend/migrations/006_add_team_logo_url.sql`
4. Re-run the upload script to populate production database:
   ```bash
   # Make sure .env has PRODUCTION Supabase credentials
   uv run python scripts/upload_team_logos.py
   ```

## Maintenance

### Adding New Team Logos

1. Add PNG file to `frontend/images/team_logos/`
   - Naming format: `city_teamname.png` (lowercase, underscores)
   - Example: `toronto_rush.png`

2. Run upload script:
   ```bash
   uv run python scripts/upload_team_logos.py
   ```

3. The script will automatically upload and update the database

### Updating Existing Logos

1. Replace the PNG file in `frontend/images/team_logos/`
2. Run upload script (it will overwrite existing files)
3. Clear cache if needed:
   ```bash
   curl -X POST http://localhost:8000/api/cache/clear
   ```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│           Vercel (Frontend)                         │
│  ┌─────────────────────────────────────────┐       │
│  │  Game Stats Page                        │       │
│  │  - Loads game data from Railway API     │       │
│  │  - Gets logo_url from team data         │       │
│  │  - Displays logo from Supabase Storage  │       │
│  └─────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────┘
                          │
                          │ API Request
                          ▼
┌─────────────────────────────────────────────────────┐
│           Railway (Backend)                         │
│  ┌─────────────────────────────────────────┐       │
│  │  /api/games/{id}/box-score              │       │
│  │  - Queries Supabase PostgreSQL          │       │
│  │  - Returns team data with logo_url      │       │
│  └─────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────┘
                          │
                          │ SQL Query
                          ▼
┌─────────────────────────────────────────────────────┐
│           Supabase                                  │
│  ┌─────────────────────┐  ┌─────────────────────┐ │
│  │  PostgreSQL DB       │  │  Storage Bucket     │ │
│  │  teams table         │  │  team-logos/        │ │
│  │  - logo_url column   │  │  - PNG files        │ │
│  └─────────────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

## Summary

✅ **What was done:**
1. Added `logo_url` column to teams table
2. Created Supabase Storage bucket for team logos
3. Uploaded 26 team logos to Supabase Storage
4. Updated teams table with public URLs
5. Modified frontend to use logo URLs from API
6. Modified backend to return logo URLs in team data

✅ **Benefits:**
- No need to bundle logos with Vercel deployment
- Logos can be updated without redeploying frontend
- Scalable cloud-native architecture
- Automatic fallback to team initials if logo fails

✅ **Deployment checklist:**
- [ ] Run migration in production Supabase
- [ ] Run upload script in production
- [ ] Deploy frontend to Vercel
- [ ] Deploy backend to Railway
- [ ] Test logos appear in production

## Questions?

- Supabase Storage docs: https://supabase.com/docs/guides/storage
- Troubleshooting: Check Supabase logs and browser console
