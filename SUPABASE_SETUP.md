# Supabase Setup Guide

This guide walks you through setting up Supabase for authentication and database management.

## 1. Create Supabase Project

1. Go to [supabase.com](https://supabase.com)
2. Sign up or log in
3. Click "New Project"
4. Fill in project details:
   - **Name**: chat-stats (or your preferred name)
   - **Database Password**: Generate a strong password (save this!)
   - **Region**: Choose closest to your users (e.g., US East, US West, Europe)
   - **Pricing Plan**: Start with Free tier

5. Wait for project to initialize (1-2 minutes)

## 2. Get Your Supabase Credentials

Once your project is ready, get these values from the Supabase dashboard:

1. Go to **Settings** → **API**
2. Copy these values:
   - **Project URL**: `https://xxxxxxxxxxxxx.supabase.co`
   - **anon/public key**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
   - **service_role key**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` (keep this secret!)

3. Also get the **Database Connection String**:
   - Go to **Settings** → **Database**
   - Copy **Connection string** → **URI** (for Python/Backend)
   - Should look like: `postgresql://postgres:[YOUR-PASSWORD]@db.xxxxxxxxxxxxx.supabase.co:5432/postgres`

## 3. Configure Environment Variables

Add these to your `.env` file:

```env
# Supabase Configuration
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.xxxxxxxxxxxxx.supabase.co:5432/postgres

# Existing configuration
ANTHROPIC_API_KEY=sk-ant-...
```

## 4. Run Database Migrations

Execute the migration scripts in your Supabase SQL Editor:

1. Go to **SQL Editor** in Supabase dashboard
2. Create a new query
3. Run migrations in order:

### Step 1: Run sports stats schema (includes RLS policies)
```bash
# In Supabase SQL Editor, paste contents of:
backend/migrations/001_sports_stats_schema.sql
```

This creates all sports statistics tables with:
- Public read access (anyone can query stats)
- Service role write access (for data imports)
- Row-Level Security enabled

### Step 2: Run user tables schema (includes RLS policies)
```bash
# In Supabase SQL Editor, paste contents of:
backend/migrations/002_user_tables.sql
```

This creates user-specific tables with:
- User-specific read/write access (users can only see their own data)
- Automatic user creation trigger
- Row-Level Security policies

## 5. Verify Row-Level Security

After running the migrations, you can verify RLS is enabled:

1. Go to **Database** → **Tables** in Supabase dashboard
2. Click on any table (e.g., `user_subscriptions`)
3. Go to **Policies** tab
4. You should see policies like "Users can view their own subscription"

**What's Protected:**
- ✅ Sports stats tables: Public read, service-role write
- ✅ User tables: User-specific read/write (can only access own data)
- ✅ Auth tokens validated on all protected endpoints

## 6. Configure Authentication Providers

### Enable Email/Password Auth (Already enabled by default)
1. Go to **Authentication** → **Providers**
2. Email provider should be enabled

### Enable Google OAuth (Optional but recommended)
1. Go to **Authentication** → **Providers**
2. Click on **Google**
3. Enable the provider
4. Follow instructions to:
   - Create Google OAuth credentials at [Google Cloud Console](https://console.cloud.google.com/)
   - Add authorized redirect URI: `https://xxxxxxxxxxxxx.supabase.co/auth/v1/callback`
   - Copy Client ID and Client Secret to Supabase

### Configure Email Templates (Optional)
1. Go to **Authentication** → **Email Templates**
2. Customize confirmation, password reset, and magic link emails

## 7. Migrate Data from SQLite to Supabase

If you have existing data in SQLite, run the migration script:

```bash
# From project root
uv run python scripts/migrate_to_supabase.py
```

This will:
- Connect to your local SQLite database
- Read all sports statistics data
- Upload to Supabase PostgreSQL
- Verify data integrity

## 8. Test Your Connection

Run the test script to verify everything is working:

```bash
uv run python scripts/test_supabase_connection.py
```

This will test:
- ✅ Database connection
- ✅ Table existence
- ✅ Query execution
- ✅ Auth token validation

## 9. Update Your Frontend

Add Supabase credentials to frontend environment:

Create `frontend/.env.local`:
```env
VITE_SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
VITE_API_URL=http://localhost:8000
```

## Common Issues & Solutions

### Issue: "relation does not exist"
**Solution**: Make sure you've run all migration scripts in order

### Issue: "JWT expired"
**Solution**: Restart your backend server to refresh the service key

### Issue: "permission denied for table"
**Solution**: Check that RLS policies are configured correctly (run migration 003)

### Issue: Can't connect to database
**Solution**:
- Verify DATABASE_URL is correct
- Check that password doesn't have special characters that need URL encoding
- Try connection from Supabase dashboard's SQL Editor first

## Next Steps

Once Supabase is configured:

1. ✅ Your database is ready
2. ✅ Authentication is set up
3. Continue to: **Stripe Integration** (see STRIPE_SETUP.md)
4. Then: **Deploy to Railway** (see RAILWAY_DEPLOYMENT.md)

## Useful Supabase Features

- **Table Editor**: Visual interface to browse/edit data
- **SQL Editor**: Run custom queries
- **Auth**: View users, send password resets
- **Logs**: Monitor database queries and errors
- **Database > Backups**: Automatic daily backups on paid plans
