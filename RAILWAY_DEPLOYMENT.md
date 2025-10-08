# Railway Backend Deployment Guide

This guide walks you through deploying the Sports Stats Chat backend to Railway.

## Prerequisites

- [Railway account](https://railway.app/) (sign up for free)
- Railway CLI installed (optional but recommended)
- Supabase database setup complete (see `SUPABASE_SETUP.md`)
- Stripe account with products configured

## Deployment Files

The following files are configured for Railway deployment:

- **`requirements.txt`** - Python dependencies
- **`railway.toml`** - Railway configuration
- **`nixpacks.toml`** - Nixpacks configuration (explicit build/start commands)
- **`Procfile`** - Process start command
- **`start.sh`** - Startup script for the FastAPI backend

## Step-by-Step Deployment

### 1. Install Railway CLI (Optional)

```bash
# macOS
brew install railway

# npm
npm i -g @railway/cli

# Or use the Railway web dashboard instead
```

### 2. Login to Railway

```bash
railway login
```

### 3. Create New Railway Project

**Option A: Via CLI**
```bash
# From project root
railway init

# Follow prompts to create new project
```

**Option B: Via Web Dashboard**
1. Go to [railway.app/new](https://railway.app/new)
2. Click "Deploy from GitHub repo"
3. Select your repository
4. Railway will auto-detect Python and use our configuration

### 4. Configure Environment Variables

Add the following environment variables in Railway dashboard or via CLI:

#### Required Environment Variables

```bash
# Anthropic API
ANTHROPIC_API_KEY=sk-ant-...

# Supabase Database (Primary - PostgreSQL)
DATABASE_URL=postgresql://postgres:[password]@[host]:[port]/postgres
SUPABASE_URL=https://[project-id].supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...

# Stripe Payment Processing
STRIPE_SECRET_KEY=sk_live_...  # or sk_test_... for testing
STRIPE_PUBLISHABLE_KEY=pk_live_...  # or pk_test_... for testing
STRIPE_WEBHOOK_SECRET=whsec_...  # Get this after creating webhook endpoint
```

**Via CLI:**
```bash
railway variables set ANTHROPIC_API_KEY=sk-ant-...
railway variables set DATABASE_URL=postgresql://...
railway variables set SUPABASE_URL=https://...
railway variables set SUPABASE_ANON_KEY=eyJ...
railway variables set SUPABASE_SERVICE_KEY=eyJ...
railway variables set STRIPE_SECRET_KEY=sk_live_...
railway variables set STRIPE_PUBLISHABLE_KEY=pk_live_...
railway variables set STRIPE_WEBHOOK_SECRET=whsec_...
```

**Via Web Dashboard:**
1. Go to your project on Railway
2. Click on your service
3. Navigate to "Variables" tab
4. Add each variable

### 5. Deploy the Backend

**Option A: Automatic Deployment (GitHub)**
- Railway will automatically deploy when you push to your main branch
- Configure branch in Railway project settings

**Option B: Manual Deployment (CLI)**
```bash
# From project root
railway up
```

### 6. Set Up Stripe Webhook Endpoint

After deployment, configure Stripe webhook to receive subscription events:

#### Step 1: Get Railway Backend URL
```bash
railway domain
# Example output: https://your-app.railway.app
```

#### Step 2: Create Webhook in Stripe
1. Go to [Stripe Dashboard](https://dashboard.stripe.com/) → **Developers** → **Webhooks**
2. Click **"Add endpoint"** or **"+ Add an endpoint"**
3. Enter endpoint URL: `https://[your-app].railway.app/api/stripe/webhook`
   - Replace `[your-app]` with your actual Railway domain
4. Click **"Select events"** and choose:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
5. Click **"Add endpoint"**

#### Step 3: Get Webhook Signing Secret
1. Click on the newly created webhook endpoint
2. Find the **"Signing secret"** section
3. Click **"Reveal"** or **"Click to reveal"**
4. Copy the secret (starts with `whsec_...`)

#### Step 4: Add to Railway
```bash
railway variables set STRIPE_WEBHOOK_SECRET=whsec_your_actual_secret_here
```

**Important**:
- For testing, use Stripe **Test mode** (toggle in top right of Stripe dashboard)
- Test webhooks still use `whsec_...` format
- Never commit webhook secrets to Git

### 7. Run Database Migrations

Your Supabase database should already have the schema from `SUPABASE_SETUP.md`.

If not, run the migrations:

1. Go to Supabase SQL Editor
2. Run `backend/migrations/001_sports_stats_schema.sql`
3. Run `backend/migrations/002_user_tables.sql`

### 8. Verify Deployment

Check deployment status:

```bash
# Via CLI
railway status
railway logs

# Or visit Railway dashboard to view logs
```

Test the API:

```bash
# Health check
curl https://[your-app].railway.app/api/stats

# Should return stats summary
```

### 9. Get Your Backend URL

```bash
# Via CLI
railway domain

# Or check Railway dashboard under "Deployment" → "Domain"
```

Save this URL - you'll need it for frontend deployment (Vercel).

## Environment Variables Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Claude AI API key | `sk-ant-...` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:...` |
| `SUPABASE_URL` | Supabase project URL | `https://xxx.supabase.co` |
| `SUPABASE_ANON_KEY` | Supabase anonymous key | `eyJ...` |
| `SUPABASE_SERVICE_KEY` | Supabase service key | `eyJ...` |
| `STRIPE_SECRET_KEY` | Stripe secret API key | `sk_live_...` |
| `STRIPE_PUBLISHABLE_KEY` | Stripe publishable key | `pk_live_...` |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret | `whsec_...` |

### Auto-Configured Variables (by Railway)

| Variable | Description | Value |
|----------|-------------|-------|
| `PORT` | HTTP port | Auto-assigned by Railway |
| `RAILWAY_ENVIRONMENT` | Deployment environment | `production` |

## Configuration Details

### railway.toml

```toml
[build]
builder = "nixpacks"
buildCommand = "pip install -r requirements.txt"

[deploy]
startCommand = "cd backend && uvicorn app:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/api/stats"
healthcheckTimeout = 100
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 10
```

### Procfile

```
web: cd backend && uvicorn app:app --host 0.0.0.0 --port $PORT
```

## Deployment Architecture

```
┌─────────────────────────────────────────────┐
│                 Railway                      │
│  ┌──────────────────────────────────────┐  │
│  │   FastAPI Backend (Python 3.13)      │  │
│  │   • Uvicorn ASGI server              │  │
│  │   • Claude AI integration            │  │
│  │   • Supabase PostgreSQL DB           │  │
│  │   • Stripe payment processing        │  │
│  │   • JWT authentication               │  │
│  └──────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│              Supabase                        │
│  • PostgreSQL Database                       │
│  • Authentication (JWT)                      │
│  • Row-Level Security (RLS)                  │
└─────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│               Stripe                         │
│  • Payment processing                        │
│  • Subscription management                   │
│  • Webhook events                            │
└─────────────────────────────────────────────┘
```

## Monitoring & Logs

### View Logs

**Via CLI:**
```bash
railway logs
railway logs --follow  # Follow logs in real-time
```

**Via Dashboard:**
1. Go to your Railway project
2. Click on your service
3. Navigate to "Logs" tab

### Health Checks

Railway automatically monitors the `/api/stats` endpoint:
- **Timeout**: 100 seconds
- **Restart Policy**: On failure
- **Max Retries**: 10

## Troubleshooting

### Common Issues

#### 1. No Start Command Found

**Error**: `No start command was found`

**Solution**: This happens when Railway/Nixpacks can't auto-detect how to start your app because the FastAPI app is in a subdirectory (`backend/app.py`).

**Fix**: We've created several files to solve this:
- `start.sh` - Startup script that Railway will execute
- `nixpacks.toml` - Explicit Nixpacks configuration with start command
- Updated `railway.toml` and `Procfile` to use `start.sh`

Make sure to commit and push these files:
```bash
git add start.sh nixpacks.toml railway.toml Procfile
git commit -m "Add Railway deployment configuration with explicit start command"
git push
```

Or redeploy via CLI:
```bash
railway up
```

#### 2. Build Fails - Python Version Mismatch

**Error**: `Python 3.13 not found`

**Solution**: Railway uses Python 3.13 as specified in `railway.toml` and `nixpacks.toml`:
```toml
[env]
NIXPACKS_PYTHON_VERSION = "3.13"
```

#### 3. Database Connection Fails

**Error**: `could not connect to database`

**Solution**: Verify `DATABASE_URL` is correctly set:
```bash
railway variables get DATABASE_URL
# Should be: postgresql://postgres:[password]@[host]:[port]/postgres
```

#### 4. Module Import Errors

**Error**: `ModuleNotFoundError: No module named 'backend'`

**Solution**: The start command includes `cd backend`:
```
web: cd backend && uvicorn app:app --host 0.0.0.0 --port $PORT
```

#### 5. Port Binding Issues

**Error**: `Address already in use`

**Solution**: Railway auto-assigns `$PORT`. The `start.sh` script handles this:
```bash
cd backend && uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}
```

#### 6. Stripe Webhook Signature Verification Fails

**Error**: `Invalid signature`

**Solution**:
1. Verify `STRIPE_WEBHOOK_SECRET` matches Stripe dashboard
2. Ensure webhook endpoint URL is correct
3. Check that webhook is sending to production URL (not localhost)

#### 7. Authentication Fails

**Error**: `Invalid JWT token`

**Solution**: Verify Supabase keys:
```bash
railway variables get SUPABASE_SERVICE_KEY
railway variables get SUPABASE_URL
```

#### 8. GitHub Repository Not Found

**Error**: "No repositories found" when trying to deploy from GitHub

**Solution**: Railway doesn't have permission to access your repository.

**Fix via GitHub Settings**:
1. Go to https://github.com/settings/installations
2. Find "Railway" in the Applications list
3. Click **"Configure"**
4. Under "Repository access":
   - Select "All repositories" OR
   - Select "Only select repositories" and add `chat-stats`
5. Click **"Save"**

**Fix via Railway Dashboard**:
1. Go to Railway Account Settings
2. Navigate to "Integrations" or "Connected Services"
3. Disconnect and reconnect GitHub with full permissions

**Alternative**: Use Railway CLI instead of GitHub UI:
```bash
railway init    # Creates project without GitHub
railway up      # Deploys from local code
```

### Debug Mode

Enable verbose logging by adding to Railway environment variables:

```bash
railway variables set LOG_LEVEL=DEBUG
railway variables set PYTHONUNBUFFERED=1
```

## Updating the Deployment

### Update Code

**Via Git (Automatic):**
```bash
git add .
git commit -m "Update backend"
git push origin main
# Railway auto-deploys
```

**Via CLI (Manual):**
```bash
railway up
```

### Update Environment Variables

```bash
railway variables set VARIABLE_NAME=new_value
```

### Rollback

```bash
# Via CLI
railway rollback

# Or via dashboard: Deployments → Select previous version → Redeploy
```

## Cost Optimization

Railway offers:
- **Free Tier**: $5 of usage credits per month
- **Pro Plan**: $20/month (includes $20 credits)

**Tips to reduce costs:**
1. Use PostgreSQL (Supabase) instead of Railway's database plugin
2. Enable auto-sleep for development environments
3. Use Railway's built-in caching

## Security Checklist

- [ ] All environment variables set correctly
- [ ] `STRIPE_WEBHOOK_SECRET` configured
- [ ] `SUPABASE_SERVICE_KEY` is service role key (not anon key)
- [ ] Database RLS policies active (see `SUPABASE_SETUP.md`)
- [ ] HTTPS enabled (Railway provides this automatically)
- [ ] Webhook endpoints secured with signature verification

## Next Steps

After backend deployment:

1. **Frontend Deployment**: See `VERCEL_DEPLOYMENT.md` (Phase 6)
2. **Configure CORS**: Update allowed origins in `backend/middleware.py`
3. **Test End-to-End**: Verify authentication, payments, and queries work
4. **Production Hardening**: See Phase 7 in `IMPLEMENTATION_PROGRESS.md`

## Support

- **Railway Docs**: https://docs.railway.app/
- **Railway Discord**: https://discord.gg/railway
- **Supabase Docs**: https://supabase.com/docs
- **Stripe Docs**: https://stripe.com/docs

## Quick Reference Commands

```bash
# Login
railway login

# Deploy
railway up

# View logs
railway logs --follow

# Check status
railway status

# Get domain
railway domain

# Set environment variable
railway variables set KEY=value

# View all variables
railway variables

# Rollback
railway rollback
```
