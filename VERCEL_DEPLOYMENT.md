# Vercel Frontend Deployment Guide

This guide walks you through deploying the Sports Stats Chat frontend to Vercel.

## Prerequisites

- [Vercel account](https://vercel.com/signup) (sign up for free)
- Railway backend deployed and running (see `RAILWAY_DEPLOYMENT.md`)
- GitHub repository with your code

## Deployment Files

The following files are configured for Vercel deployment:

- **`vercel.json`** - Vercel configuration (build settings, routing, caching)
  - All paths are relative to the `frontend` root directory
  - Configures SPA routing (all routes → `/index.html`)
  - Sets asset caching headers for optimal performance
- **`frontend/package.json`** - Dependencies and build scripts
- **`frontend/.env.example`** - Template for environment variables

## Step-by-Step Deployment

### 1. Prepare Environment Variables

You'll need these values ready:

- **Railway Backend URL**: `https://chat-with-stats-production.up.railway.app`
- **Supabase URL**: From your Supabase project settings
- **Supabase Anon Key**: From your Supabase project settings
- **Stripe Publishable Key**: From your Stripe dashboard

### 2. Deploy to Vercel

#### Option A: Via Vercel Dashboard (Recommended)

1. Go to [vercel.com/new](https://vercel.com/new)
2. Click **"Import Git Repository"**
3. Select your `chat-with-stats` repository
4. Configure project settings:
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend` (IMPORTANT: set this to the frontend subdirectory)
   - **Build Command**: Leave default (`npm run build`) or override if needed
   - **Output Directory**: Leave default (`dist`)
   - **Install Command**: Leave default (`npm install`)

5. Click **"Deploy"** (it will fail - this is expected, we need to add env vars first)

#### Option B: Via Vercel CLI

```bash
# Install Vercel CLI
npm i -g vercel

# Login
vercel login

# Deploy from project root
vercel

# Follow prompts:
# - Link to existing project or create new
# - Set up and deploy
```

### 3. Configure Environment Variables

After creating the project (even if the first deploy failed):

1. Go to your Vercel project dashboard
2. Navigate to **Settings** → **Environment Variables**
3. Add the following variables:

#### Required Environment Variables

| Variable | Value | Example |
|----------|-------|---------|
| `VITE_API_URL` | Your Railway backend URL | `https://chat-with-stats-production.up.railway.app` |
| `VITE_SUPABASE_URL` | Your Supabase project URL | `https://xxx.supabase.co` |
| `VITE_SUPABASE_ANON_KEY` | Your Supabase anonymous key | `eyJ...` |
| `VITE_STRIPE_PUBLISHABLE_KEY` | Your Stripe publishable key | `pk_test_...` or `pk_live_...` |

**Adding via Dashboard:**
1. Click **"Add New"**
2. Enter **Key** (e.g., `VITE_API_URL`)
3. Enter **Value** (e.g., `https://chat-with-stats-production.up.railway.app`)
4. Select **"Production"**, **"Preview"**, and **"Development"** (all environments)
5. Click **"Save"**
6. Repeat for all variables

**Adding via CLI:**
```bash
vercel env add VITE_API_URL production
# Paste value when prompted
# Repeat for other variables
```

### 4. Redeploy with Environment Variables

After adding all environment variables:

**Via Dashboard:**
1. Go to **Deployments** tab
2. Click **"Redeploy"** on the latest deployment
3. Check **"Use existing Build Cache"** or uncheck to rebuild fresh
4. Click **"Redeploy"**

**Via CLI:**
```bash
vercel --prod
```

### 5. Update Backend CORS Settings

Your frontend will be deployed at a Vercel URL like:
- `https://chat-with-stats.vercel.app` (production)
- `https://chat-with-stats-xxx.vercel.app` (preview deployments)

**Update Railway backend to allow your Vercel domain:**

1. Get your Vercel domain from the deployment
2. Update `backend/middleware.py` to include Vercel domains in CORS
3. Push changes to trigger Railway redeploy

See the CORS configuration section below for details.

### 6. Verify Deployment

Once deployed, test your application:

1. **Visit your Vercel URL** (e.g., `https://chat-with-stats.vercel.app`)
2. **Test authentication**:
   - Click "Sign Up" to create an account
   - Verify you receive confirmation email
   - Log in with your credentials
3. **Test API connectivity**:
   - Try asking a stats query
   - Check browser console for errors
4. **Test pricing page**:
   - Visit `/pricing.html`
   - Verify Stripe checkout works
5. **Test user menu**:
   - Check subscription tier displays correctly
   - Verify query usage tracking works

## CORS Configuration

Update `backend/middleware.py` to allow your Vercel domain:

```python
def configure_cors(app: FastAPI):
    """Configure CORS middleware."""
    origins = [
        "http://localhost:3000",  # Local development
        "http://localhost:4173",  # Local production preview
        "https://chat-with-stats.vercel.app",  # Vercel production
        "https://chat-with-stats-*.vercel.app",  # Vercel preview deployments
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
```

**Note**: Vercel preview deployments have dynamic URLs. You can either:
- Use a wildcard pattern (less secure but convenient)
- Configure specific preview URLs as needed
- Use Vercel's production URL only for maximum security

After updating, commit and push to trigger Railway redeploy.

## Custom Domain (Optional)

### Add Custom Domain to Vercel

1. Go to your Vercel project → **Settings** → **Domains**
2. Click **"Add"**
3. Enter your domain (e.g., `chat.yourdomain.com`)
4. Follow DNS configuration instructions
5. Vercel will automatically provision SSL certificate

### Update CORS for Custom Domain

Add your custom domain to the CORS origins list in `backend/middleware.py`:

```python
origins = [
    # ... existing origins
    "https://chat.yourdomain.com",  # Your custom domain
]
```

## Environment Variables Reference

### Frontend Environment Variables

All frontend environment variables must be prefixed with `VITE_` to be accessible in the Vite build.

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `VITE_API_URL` | Backend API base URL | Yes | `https://chat-with-stats-production.up.railway.app` |
| `VITE_SUPABASE_URL` | Supabase project URL | Yes | `https://xxx.supabase.co` |
| `VITE_SUPABASE_ANON_KEY` | Supabase anonymous key (public) | Yes | `eyJhbGci...` |
| `VITE_STRIPE_PUBLISHABLE_KEY` | Stripe publishable key (public) | Yes | `pk_test_...` or `pk_live_...` |

**Important Security Notes:**
- Only the **anon key** should be used in frontend (not service key)
- Only the **publishable key** should be used for Stripe (not secret key)
- These keys are safe to expose in client-side code
- Secret keys should NEVER be in frontend code or environment variables

## Deployment Architecture

```
┌─────────────────────────────────────────────┐
│                 Vercel                       │
│  ┌──────────────────────────────────────┐  │
│  │   Frontend (Vite + TypeScript)       │  │
│  │   • Supabase Auth                    │  │
│  │   • Stripe Checkout                  │  │
│  │   • SPA Routing                      │  │
│  └──────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│                 Railway                      │
│  ┌──────────────────────────────────────┐  │
│  │   Backend (FastAPI)                  │  │
│  │   • Claude AI integration            │  │
│  │   • JWT authentication               │  │
│  │   • Stripe webhooks                  │  │
│  └──────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│              Supabase                        │
│  • PostgreSQL Database                       │
│  • Authentication (JWT)                      │
│  • Row-Level Security                        │
└─────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│               Stripe                         │
│  • Payment processing                        │
│  • Subscription management                   │
│  • Webhook events                            │
└─────────────────────────────────────────────┘
```

## Troubleshooting

### Common Issues

#### 1. Build Fails - Module Not Found

**Error**: `Cannot find module 'xyz'`

**Solution**: Ensure all dependencies are in `frontend/package.json`:
```bash
cd frontend
npm install
npm run build  # Test locally
```

#### 2. Environment Variables Not Working

**Error**: `undefined` when accessing `import.meta.env.VITE_API_URL`

**Solution**:
- Verify variables are prefixed with `VITE_`
- Check they're set in Vercel dashboard
- Redeploy after adding variables
- Clear build cache if needed

#### 3. API Calls Failing (CORS Errors)

**Error**: `CORS policy: No 'Access-Control-Allow-Origin' header`

**Solution**:
- Update `backend/middleware.py` with your Vercel domain
- Push changes to trigger Railway redeploy
- Clear browser cache
- Check browser console for exact domain being blocked

#### 4. Blank Page After Deployment

**Error**: White screen, no errors in console

**Solution**:
- Check Vercel deployment logs for build errors
- Verify `vercel.json` output directory is correct (`frontend/dist`)
- Check if routing is configured (SPA rewrites)
- Inspect Network tab for 404 errors on assets

#### 5. Authentication Not Working

**Error**: Login/signup fails silently

**Solution**:
- Verify `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` are correct
- Check Supabase dashboard → Authentication → URL Configuration
- Add Vercel domain to Supabase allowed redirect URLs
- Test with browser dev tools network tab

#### 6. Stripe Checkout Not Loading

**Error**: Stripe checkout fails to redirect

**Solution**:
- Verify `VITE_STRIPE_PUBLISHABLE_KEY` is correct (starts with `pk_`)
- Check browser console for Stripe errors
- Ensure backend `STRIPE_SECRET_KEY` is set in Railway
- Test with Stripe test keys first (`pk_test_...`)

## Monitoring & Logs

### View Deployment Logs

**Via Dashboard:**
1. Go to your Vercel project
2. Click **"Deployments"** tab
3. Click on a deployment
4. View **"Build Logs"** and **"Function Logs"**

**Via CLI:**
```bash
vercel logs [deployment-url]
vercel logs --follow  # Follow logs in real-time
```

### Analytics

Vercel provides built-in analytics:
1. Go to your project → **"Analytics"** tab
2. View page views, unique visitors, top pages
3. Monitor performance metrics

## Updating the Deployment

### Automatic Deployments (Recommended)

Vercel automatically deploys when you push to GitHub:

```bash
git add .
git commit -m "Update frontend"
git push origin main
# Vercel automatically deploys
```

### Manual Redeploy

**Via Dashboard:**
1. Go to **Deployments** tab
2. Find the deployment you want to redeploy
3. Click **"..."** menu → **"Redeploy"**

**Via CLI:**
```bash
vercel --prod
```

### Rollback to Previous Deployment

1. Go to **Deployments** tab
2. Find a previous successful deployment
3. Click **"..."** menu → **"Promote to Production"**

## Preview Deployments

Vercel automatically creates preview deployments for:
- Pull requests
- Non-production branches

Each preview gets a unique URL:
- `https://chat-with-stats-git-[branch]-[username].vercel.app`

Perfect for testing changes before merging to production!

## Performance Optimization

### Build Optimization

Vercel automatically:
- ✅ Minifies JavaScript/CSS
- ✅ Optimizes images
- ✅ Enables HTTP/2
- ✅ Provides CDN caching
- ✅ Compresses assets (Gzip/Brotli)

### Caching Strategy

From `vercel.json`:
```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ],
  "headers": [
    {
      "source": "/assets/(.*)",
      "headers": [
        {
          "key": "Cache-Control",
          "value": "public, max-age=31536000, immutable"
        }
      ]
    }
  ]
}
```

- All routes rewrite to `/index.html` for SPA routing
- Static assets in `/assets/*` are cached for 1 year
- Build outputs to `dist` directory (relative to `frontend` root)

## Security Checklist

- [ ] All environment variables set correctly
- [ ] Using Supabase **anon key** (not service key) in frontend
- [ ] Using Stripe **publishable key** (not secret key) in frontend
- [ ] CORS configured in backend for Vercel domain
- [ ] Supabase RLS policies active
- [ ] HTTPS enabled (Vercel provides automatically)
- [ ] Custom domain has SSL certificate (automatic)

## Cost

Vercel Pricing:
- **Hobby (Free)**: Perfect for personal projects
  - Unlimited deployments
  - 100 GB bandwidth/month
  - Automatic HTTPS
  - Preview deployments

- **Pro ($20/month)**: For production apps
  - 1 TB bandwidth/month
  - Team collaboration
  - Custom domains
  - Priority support

Most personal projects fit within the free tier!

## Next Steps

After frontend deployment:

1. **Test End-to-End**: Verify all features work in production
2. **Configure Custom Domain** (optional): Add your own domain
3. **Set Up Monitoring**: Use Vercel Analytics or third-party tools
4. **Production Hardening**: See Phase 7 in `IMPLEMENTATION_PROGRESS.md`

## Support

- **Vercel Docs**: https://vercel.com/docs
- **Vercel Community**: https://github.com/vercel/vercel/discussions
- **Supabase Docs**: https://supabase.com/docs
- **Stripe Docs**: https://stripe.com/docs

## Quick Reference Commands

```bash
# Install Vercel CLI
npm i -g vercel

# Login
vercel login

# Deploy to production
vercel --prod

# View logs
vercel logs --follow

# List deployments
vercel ls

# Remove deployment
vercel rm [deployment-url]

# Link local project to Vercel
vercel link

# Pull environment variables to local
vercel env pull
```
