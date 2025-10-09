# Database Migration Guide

## How to Apply Migrations to Supabase

### Using the Supabase Dashboard (Recommended)

1. **Go to your Supabase project**
   - Navigate to https://supabase.com/dashboard
   - Select your project

2. **Open the SQL Editor**
   - Click on "SQL Editor" in the left sidebar
   - Click "New query"

3. **Copy and paste the migration SQL**
   - Open the migration file (e.g., `003_fix_query_limits.sql`)
   - Copy all contents
   - Paste into the SQL Editor

4. **Run the migration**
   - Click "Run" (or press Cmd/Ctrl + Enter)
   - Check for success message
   - Review any output or errors

### Using the Supabase CLI (Alternative)

```bash
# Install Supabase CLI (if not already installed)
npm install -g supabase

# Login to Supabase
supabase login

# Link to your project
supabase link --project-ref your-project-ref

# Run migration
supabase db push

# Or run specific migration file
psql $DATABASE_URL -f backend/migrations/003_fix_query_limits.sql
```

### Using Direct PostgreSQL Connection

```bash
# Get your DATABASE_URL from Supabase Settings → Database → Connection String
# Then run:
psql "$DATABASE_URL" -f backend/migrations/003_fix_query_limits.sql
```

## Current Migrations

### 001_initial_schema.sql
- Creates all sports statistics tables (teams, players, games, etc.)
- Initial schema for UFA statistics

### 002_user_tables.sql
- Creates user authentication tables
- Sets up subscription system
- Implements RLS (Row Level Security) policies
- **Updated**: Fixed free tier query limit from 50 → 10

### 003_fix_query_limits.sql
- **NEW**: Fixes existing user records with wrong query limits
- Updates all free tier users from 50 to 10 queries
- Ensures consistency across database

## Verifying Migration Success

After running migration `003_fix_query_limits.sql`, verify:

```sql
-- Check all subscription tiers and their query limits
SELECT tier, query_limit, COUNT(*) as user_count
FROM user_subscriptions
GROUP BY tier, query_limit
ORDER BY tier, query_limit;

-- Expected output:
-- tier  | query_limit | user_count
-- free  |          10 |          X
-- pro   |         200 |          Y
```

## Troubleshooting

### Error: "relation does not exist"
- Make sure you've run previous migrations first
- Run migrations in order: 001 → 002 → 003

### Error: "permission denied"
- Make sure you're connected with the correct credentials
- Use the service role key for admin operations

### Changes not reflecting in app
1. Clear the backend cache/restart the server
2. Refresh the frontend
3. Check browser console for errors
4. Verify the database was actually updated (run verification query above)
