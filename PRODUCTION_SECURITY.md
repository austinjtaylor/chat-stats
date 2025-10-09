# Production Security Guide

This document outlines the security measures, configurations, and best practices for deploying the Sports Statistics Chat System to production.

## Table of Contents

- [Security Architecture Overview](#security-architecture-overview)
- [Authentication & Authorization](#authentication--authorization)
- [Subscription Quotas vs Rate Limiting](#subscription-quotas-vs-rate-limiting)
- [Security Headers](#security-headers)
- [CORS Configuration](#cors-configuration)
- [Request Logging & Monitoring](#request-logging--monitoring)
- [Environment Configuration](#environment-configuration)
- [Pre-Deployment Security Checklist](#pre-deployment-security-checklist)
- [API Key Rotation](#api-key-rotation)
- [Incident Response](#incident-response)

---

## Security Architecture Overview

The application implements multiple layers of security:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Security Headers (HSTS, CSP, X-Frame-Options, etc.)     │
├─────────────────────────────────────────────────────────────┤
│ 2. Request Logging (All requests, auth failures, quotas)   │
├─────────────────────────────────────────────────────────────┤
│ 3. Rate Limiting (DOS prevention, anti-abuse)              │
├─────────────────────────────────────────────────────────────┤
│ 4. CORS (Restrict allowed origins)                         │
├─────────────────────────────────────────────────────────────┤
│ 5. Authentication (JWT tokens from Supabase)               │
├─────────────────────────────────────────────────────────────┤
│ 6. Subscription Quotas (10/month free, 200/month pro)      │
└─────────────────────────────────────────────────────────────┘
```

---

## Authentication & Authorization

### How It Works

1. **User Authentication**: Powered by Supabase Auth
   - Email/password authentication
   - JWT tokens for session management
   - Automatic token refresh

2. **Token Validation**: `backend/auth.py`
   - Validates JWT signature using Supabase service key
   - Extracts user ID and email from token
   - Returns 401 Unauthorized for invalid/expired tokens

3. **Protected Endpoints**:
   - `/api/query` - Requires authentication + enforces subscription quota
   - `/api/cache/clear` - Requires authentication (admin function)
   - `/api/data/import` - Requires authentication (admin function)
   - `/api/stripe/create-checkout-session` - Requires authentication
   - `/api/stripe/create-billing-portal-session` - Requires authentication

4. **Public Endpoints** (no authentication required):
   - `/api/stats` - Public stats summary
   - `/api/players/*` - Player search and stats
   - `/api/teams/*` - Team search and stats
   - `/api/games/*` - Game results and box scores
   - `/api/stripe/pricing` - Public pricing information

### Implementation Example

```python
from auth import get_current_user
from fastapi import Depends

@router.post("/api/query")
async def query_stats(
    request: QueryRequest,
    user: dict = Depends(get_current_user),  # Requires authentication
):
    user_id = user["user_id"]
    # Process query...
```

---

## Subscription Quotas vs Rate Limiting

### Subscription Quotas (Primary Control)

**Purpose**: Enforce monthly query limits based on subscription tier

**Implementation**: `backend/services/subscription_service.py`

**Tiers**:
- **Free**: 10 queries/month, $0
- **Pro**: 200 queries/month, $4.99/month

**How It Works**:
1. Before processing `/api/query`, check user's remaining queries
2. If limit reached, return `429 Too Many Requests` with upgrade message
3. After successful query, increment `queries_this_month` counter
4. Counter resets monthly via Stripe webhook events

**Database**: `user_subscriptions` table tracks usage

```sql
SELECT queries_this_month, query_limit
FROM user_subscriptions
WHERE user_id = 'xxx';
```

### Rate Limiting (Secondary Protection)

**Purpose**: Prevent API abuse and DOS attacks

**Implementation**: `backend/middleware/rate_limit.py` (SlowAPI)

**Limits**:
- Public endpoints: 100 requests/minute
- Authenticated endpoints: 200 requests/hour per user
- Query endpoint: 30 requests/minute (in addition to subscription quotas)
- Webhooks: No limit

**Key Difference**:
- **Subscription quotas**: Business logic (how many AI queries per month)
- **Rate limiting**: Security measure (prevent spamming/abuse)

**Example**: A Pro user with 200 queries/month can still only make 30 requests/minute to prevent scripts from spamming the API.

---

## Security Headers

Implemented in `backend/middleware/security.py`

### Headers Applied

| Header | Purpose | Configuration |
|--------|---------|---------------|
| `Strict-Transport-Security` | Force HTTPS | `max-age=31536000; includeSubDomains` (production only) |
| `Content-Security-Policy` | Prevent XSS | Restricts script/style sources |
| `X-Frame-Options` | Prevent clickjacking | `DENY` |
| `X-Content-Type-Options` | Prevent MIME sniffing | `nosniff` |
| `X-XSS-Protection` | Browser XSS protection | `1; mode=block` |
| `Referrer-Policy` | Control referrer info | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | Disable unused features | Disables geolocation, camera, etc. |

### HSTS (HTTP Strict Transport Security)

**Important**: Only enabled in production with HTTPS

```python
# In Railway, set environment variable:
ENVIRONMENT=production
```

This ensures HSTS is only active when serving over HTTPS.

---

## CORS Configuration

Implemented in `backend/middleware.py`

### Allowed Origins

**Development**:
```python
origins = [
    "http://localhost:3000",  # Vite dev server
    "http://localhost:4173",  # Production preview
]
```

**Production**:
```python
origins = [
    "http://localhost:3000",  # Still allow local dev
    "https://chat-frisbee-stats.vercel.app",  # Vercel production
]

# Regex for preview deployments:
allow_origin_regex = r"https://chat-frisbee-stats.*\.vercel\.app"
```

### After Vercel Deployment

1. Get your Vercel URL (e.g., `https://your-app.vercel.app`)
2. Update `backend/middleware.py`:
   ```python
   origins = [
       # ... existing origins
       "https://your-app.vercel.app",  # Add your Vercel URL
   ]
   ```
3. Commit and push to trigger Railway redeploy

---

## Request Logging & Monitoring

Implemented in `backend/middleware/logging_middleware.py`

### What Gets Logged

1. **All API Requests**:
   ```json
   {
     "method": "POST",
     "path": "/api/query",
     "status_code": 200,
     "duration_ms": 1234.56,
     "user_id": "uuid-here",
     "client_ip": "192.168.1.1"
   }
   ```

2. **Authentication Failures** (401/403):
   ```json
   {
     "event": "auth_failure",
     "status_code": 401,
     "path": "/api/query",
     "client_ip": "192.168.1.1"
   }
   ```

3. **Quota Limit Hits** (429):
   ```json
   {
     "event": "quota_limit_hit",
     "user_id": "uuid-here",
     "path": "/api/query"
   }
   ```

### Log Formats

- **Development**: Human-readable text
- **Production**: Structured JSON (for log aggregation)

### Viewing Logs

**Railway**:
```bash
railway logs
```

**Local Development**:
Logs appear in terminal running `./run-dev.sh`

---

## Environment Configuration

### Required Environment Variables

```env
# CRITICAL: Set this in Railway
ENVIRONMENT=production

# Database & Auth
DATABASE_URL=postgresql://postgres:xxx@db.xxx.supabase.co:5432/postgres
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...

# API Keys
ANTHROPIC_API_KEY=sk-ant-...

# Stripe
STRIPE_SECRET_KEY=sk_live_...  # Use sk_live_ in production!
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

### Environment-Specific Behavior

| Feature | Development | Production |
|---------|-------------|------------|
| HSTS | Disabled | Enabled |
| Log Format | Text | JSON |
| Allowed Hosts | `*` (all) | Specific domains |
| Error Details | Full stack traces | Sanitized messages |

---

## Pre-Deployment Security Checklist

Before deploying to production, ensure:

### Backend (Railway)

- [ ] `ENVIRONMENT=production` set in Railway
- [ ] All environment variables configured (see `.env.example`)
- [ ] Using Stripe **live** keys (not test keys)
- [ ] Database migrations applied in Supabase
- [ ] CORS origins updated with Vercel URL
- [ ] Allowed hosts updated in `middleware.py`
- [ ] SSL/TLS enabled (Railway does this automatically)

### Frontend (Vercel)

- [ ] Environment variables configured:
  - `VITE_API_URL` - Railway backend URL
  - `VITE_SUPABASE_URL`
  - `VITE_SUPABASE_ANON_KEY`
  - `VITE_STRIPE_PUBLISHABLE_KEY` (live key)
- [ ] Build successful (`npm run build`)
- [ ] API calls use HTTPS URLs

### Database (Supabase)

- [ ] Row-Level Security (RLS) policies enabled
- [ ] User tables created (`user_subscriptions`, etc.)
- [ ] Backups configured
- [ ] SSL required for connections

### Stripe

- [ ] Products created (Pro tier)
- [ ] Webhook endpoint configured: `https://your-backend.railway.app/api/stripe/webhook`
- [ ] Webhook signing secret updated in Railway
- [ ] Using **live** API keys (not test)

### Monitoring

- [ ] Railway logs accessible
- [ ] Supabase logs accessible
- [ ] Error tracking configured (optional: Sentry)
- [ ] Uptime monitoring (optional: UptimeRobot)

---

## API Key Rotation

### When to Rotate

- Every 90 days (recommended)
- After a security incident
- When an employee leaves
- If a key is accidentally exposed

### How to Rotate

#### Anthropic API Key

1. Generate new key: https://console.anthropic.com/settings/keys
2. Update Railway: `ANTHROPIC_API_KEY=new-key`
3. Deploy and verify
4. Delete old key from Anthropic console

#### Supabase Keys

1. **DO NOT rotate the anon key** - breaks frontend auth
2. Rotate service key if compromised:
   - Generate new service role key in Supabase
   - Update Railway: `SUPABASE_SERVICE_KEY=new-key`
   - Deploy immediately

#### Stripe Keys

1. Generate new keys in Stripe Dashboard
2. Update both Railway (backend) and Vercel (frontend)
3. Update webhook signing secret
4. Deploy both services
5. Deactivate old keys

### Zero-Downtime Rotation

For critical services:
1. Add new key alongside old key (if supported)
2. Deploy with both keys active
3. Verify new key works
4. Remove old key
5. Deploy again

---

## Incident Response

### Suspected API Key Compromise

1. **Immediate Actions**:
   - Rotate all affected API keys
   - Review logs for unauthorized access
   - Notify affected users if data exposed

2. **Investigation**:
   - Check Railway logs for unusual activity
   - Review Supabase logs for unauthorized queries
   - Analyze Stripe webhook logs

3. **Prevention**:
   - Enable IP restrictions (if service supports)
   - Add additional monitoring
   - Review access control policies

### DOS Attack

1. **Symptoms**:
   - Sudden spike in 429 errors
   - Slow response times
   - High CPU/memory usage

2. **Mitigation**:
   - Rate limits already in place
   - Railway auto-scales if needed
   - Consider adding Cloudflare (DDoS protection)

3. **Analysis**:
   - Review logs for attack patterns
   - Identify attacking IPs
   - Consider IP blocking at infrastructure level

### Data Breach

1. **Immediate Actions**:
   - Revoke all access tokens
   - Rotate all API keys
   - Force password reset for all users (via Supabase)

2. **Legal Requirements**:
   - Notify users within 72 hours (GDPR)
   - Report to authorities if required
   - Document the incident

3. **Post-Mortem**:
   - Identify root cause
   - Implement additional security measures
   - Update security policies

---

## Additional Security Recommendations

### For Production Deployment

1. **Redis for Rate Limiting**: Replace in-memory rate limiting with Redis
   ```python
   # In backend/middleware/rate_limit.py
   storage_uri="redis://redis-host:6379"
   ```

2. **Error Tracking**: Add Sentry for error monitoring
   ```bash
   uv add sentry-sdk[fastapi]
   ```

3. **DDoS Protection**: Use Cloudflare in front of Railway

4. **Database Connection Pooling**: Already configured via SQLAlchemy

5. **Secret Scanning**: Enable GitHub secret scanning

6. **Dependency Updates**: Run `uv sync` weekly to get security patches

### Security Testing

Before launch:
- [ ] Test authentication bypass attempts
- [ ] Test SQL injection on all endpoints
- [ ] Test XSS in query input
- [ ] Test CSRF (not applicable - using JWT)
- [ ] Test quota bypass attempts
- [ ] Load test with realistic traffic

---

## Support & Questions

For security issues:
- **DO NOT** open public GitHub issues
- Email: [your-security-email]
- Report via: [your-security-reporting-channel]

For general questions:
- See main README.md
- Check deployment guides (RAILWAY_DEPLOYMENT.md, VERCEL_DEPLOYMENT.md)

---

**Last Updated**: October 2025
**Version**: 1.0
