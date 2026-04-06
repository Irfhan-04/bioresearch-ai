# 🚀 Deployment Guide

Complete guide for deploying Biotech Lead Generator to production.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Platform Options](#platform-options)
3. [Deploy to Render](#deploy-to-render)
4. [Deploy to Railway](#deploy-to-railway)
5. [Deploy to Fly.io](#deploy-to-flyio)
6. [Environment Variables](#environment-variables)
7. [Database Setup](#database-setup)
8. [Post-Deployment](#post-deployment)
9. [Monitoring](#monitoring)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before deploying, ensure you have:

- ✅ GitHub repository with your code
- ✅ Supabase account (for PostgreSQL database)
- ✅ Upstash account (for Redis)
- ✅ Resend account (for emails)
- ✅ Domain name (optional, but recommended)
- ✅ Sentry account (for error tracking)

---

## Platform Options

### Recommended Platforms

| Platform | Best For | Free Tier | Ease of Use | Cost (Pro) |
|----------|----------|-----------|-------------|------------|
| **Render** | Production apps | ✅ Yes | ⭐⭐⭐⭐⭐ | $7/mo |
| **Railway** | Developer-friendly | ✅ Yes (trial) | ⭐⭐⭐⭐⭐ | $5/mo |
| **Fly.io** | Global edge deployment | ✅ Yes | ⭐⭐⭐⭐ | $3/mo |

We recommend **Render** for beginners and **Railway** for developers.

---

## Deploy to Render

### Step 1: Create Render Account

1. Go to [render.com](https://render.com)
2. Sign up with GitHub
3. Authorize Render to access your repositories

### Step 2: Create Web Service

1. Click **"New +"** → **"Web Service"**
2. Connect your GitHub repository
3. Configure:
   - **Name**: `biotech-lead-generator-api`
   - **Region**: Choose closest to your users
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Step 3: Add Environment Variables

Go to **Environment** tab and add:

```bash
# App Configuration
APP_NAME=Biotech Lead Generator API
APP_VERSION=2.0.0
DEBUG=False

# Security
SECRET_KEY=your-super-secret-key-here-min-32-chars
ALGORITHM=HS256

# Database (Supabase)
DATABASE_URL=postgresql+asyncpg://user:pass@aws-0-region.pooler.supabase.com:5432/postgres
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_SERVICE_KEY=your-supabase-service-key

# Redis (Upstash)
REDIS_URL=rediss://default:xxx@region.upstash.io:6379
CELERY_BROKER_URL=rediss://default:xxx@region.upstash.io:6379
CELERY_RESULT_BACKEND=rediss://default:xxx@region.upstash.io:6379

# Email (Resend)
RESEND_API_KEY=re_xxx
RESEND_FROM_EMAIL=noreply@yourdomain.com

# External APIs
PUBMED_EMAIL=your.email@example.com

# Monitoring (Sentry)
SENTRY_DSN=https://xxx@sentry.io/xxx
SENTRY_ENVIRONMENT=production

# Stripe
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_PRO_PRICE_ID=price_xxx
STRIPE_TEAM_PRICE_ID=price_xxx
STRIPE_SUCCESS_URL=https://your-frontend.example.com/settings/billing?session_id={CHECKOUT_SESSION_ID}
STRIPE_CANCEL_URL=https://your-frontend.example.com/settings/billing?cancelled=true
```

### Step 4: Deploy

1. Click **"Create Web Service"**
2. Wait for build to complete (5-10 minutes)
3. Your API will be live at `https://your-service.onrender.com`

### Step 5: Set Up Background Workers

For Celery workers, create another service:

1. **New +** → **Background Worker**
2. Same repository and settings
3. **Start Command**: `celery -A app.workers.celery_app worker --loglevel=info`
4. Add same environment variables

For Celery Beat (scheduler):

1. Another **Background Worker**
2. **Start Command**: `celery -A app.workers.celery_app beat --loglevel=info`

---

## Deploy to Railway

### Step 1: Install Railway CLI

```bash
npm install -g @railway/cli
railway login
```

### Step 2: Initialize Project

```bash
cd backend
railway init
```

### Step 3: Create Services

```bash
# Create main API service
railway up

# Add environment variables
railway variables set \
  DATABASE_URL="your-database-url" \
  REDIS_URL="your-redis-url" \
  # ... other variables
```

### Step 4: Deploy

```bash
railway up
```

Your API will be live at `https://your-project.up.railway.app`

### Alternative: Deploy via Dashboard

1. Go to [railway.app](https://railway.app)
2. **New Project** → **Deploy from GitHub repo**
3. Select your repository
4. Add environment variables in **Variables** tab
5. Deploy automatically happens on push to main

---

## Deploy to Fly.io

### Step 1: Install Fly CLI

```bash
# macOS
brew install flyctl

# Linux
curl -L https://fly.io/install.sh | sh

# Windows
iwr https://fly.io/install.ps1 -useb | iex
```

### Step 2: Sign Up & Login

```bash
fly auth signup
fly auth login
```

### Step 3: Launch App

```bash
cd backend
fly launch
```

Follow the prompts:
- Choose app name
- Select region
- Don't set up Postgres (we're using Supabase)

### Step 4: Configure Secrets

```bash
fly secrets set \
  SECRET_KEY="your-secret-key" \
  DATABASE_URL="your-database-url" \
  REDIS_URL="your-redis-url" \
  RESEND_API_KEY="your-resend-key"
```

### Step 5: Deploy

```bash
fly deploy
```

Your API will be live at `https://your-app.fly.dev`

---

## Environment Variables

### Required Variables

```bash
# Core
SECRET_KEY=              # Generate: python -c "import secrets; print(secrets.token_urlsafe(32))"
DATABASE_URL=            # From Supabase
REDIS_URL=               # From Upstash
```

### Optional Variables

```bash
# Features
ENABLE_EMAIL_NOTIFICATIONS=True
ENABLE_WEBHOOKS=True
ENABLE_BACKGROUND_JOBS=True

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# Subscription Limits
FREE_TIER_LEADS_PER_MONTH=100
PRO_TIER_LEADS_PER_MONTH=1000
```

---

## Database Setup

### 1. Create Supabase Project

1. Go to [supabase.com](https://supabase.com)
2. Create new project
3. Wait for database to be ready

### 2. Run Migrations

```bash
# Set DATABASE_URL
export DATABASE_URL="postgresql://..."

# Run migrations
cd backend
alembic upgrade head
```

### 3. Create Storage Bucket

1. Go to **Storage** in Supabase dashboard
2. Create bucket named `exports`
3. Set as **Public bucket**

---

## Post-Deployment

### 1. Verify Health

```bash
curl https://your-api-url.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "database": "connected",
  "cache": "connected"
}
```

### 2. Test Authentication

```bash
# Register a user
curl -X POST https://your-api-url.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123!",
    "full_name": "Test User"
  }'
```

### 3. Test Stripe Webhooks

For local Stripe CLI testing, forward events to the real webhook handler:

```bash
stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe
```

The production webhook endpoint is `POST /api/v1/webhooks/stripe`.

### 4. Set Up Custom Domain (Optional)

#### Render:
1. Go to **Settings** → **Custom Domain**
2. Add your domain
3. Update DNS records

#### Railway:
1. **Settings** → **Domains**
2. Add domain
3. Update DNS

#### Fly.io:
```bash
fly certs add yourdomain.com
fly certs show yourdomain.com
```

---

## Monitoring

### 1. Sentry (Error Tracking)

```python
# Already configured in app/main.py
SENTRY_DSN=https://xxx@sentry.io/xxx
```

View errors at [sentry.io](https://sentry.io)

### 2. Uptime Monitoring

Use services like:
- [UptimeRobot](https://uptimerobot.com) (Free)
- [Better Uptime](https://betterstack.com/better-uptime)
- [Pingdom](https://www.pingdom.com)

### 3. Application Metrics

View metrics in platform dashboards:
- **Render**: Metrics tab
- **Railway**: Observability tab
- **Fly.io**: Metrics dashboard

---

## Troubleshooting

### Database Connection Issues

**Problem**: `Network is unreachable` or IPv6 errors

**Solution**: Use Supabase connection pooler:
```bash
# Change from direct connection:
db.xxx.supabase.co

# To connection pooler:
aws-0-region.pooler.supabase.com
```

### Worker Not Starting

**Problem**: Celery worker crashes

**Solution**: Check environment variables:
```bash
# Ensure these are set:
REDIS_URL
CELERY_BROKER_URL
CELERY_RESULT_BACKEND
```

### High Memory Usage

**Solution**: Reduce workers:
```bash
# Instead of --workers=4
uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers=2
```

### Slow API Response

**Solution**: Enable caching and optimize queries:
```python
# Increase cache TTL
REDIS_CACHE_TTL=7200  # 2 hours
```

---

## Production Checklist

Before going live:

- [ ] Set `DEBUG=False`
- [ ] Use strong `SECRET_KEY`
- [ ] Enable HTTPS only
- [ ] Set up error monitoring (Sentry)
- [ ] Configure backups (Supabase auto-backups)
- [ ] Add health checks
- [ ] Set up CI/CD pipeline
- [ ] Test all endpoints
- [ ] Run security scan
- [ ] Set up monitoring alerts
- [ ] Document API (OpenAPI/Swagger)
- [ ] Add rate limiting
- [ ] Configure CORS properly
- [ ] Set up log aggregation

---

## Support

Need help? Check these resources:

- 📚 [API Documentation](/docs)
- 💬 [GitHub Issues](https://github.com/yourusername/biotech-lead-generator/issues)
- 📧 Email: support@yourdomain.com

---

**🎉 Congratulations! Your Biotech Lead Generator API is now in production!**
## Post-Migration Steps (Run Once Per Environment)

After running `alembic upgrade head`, apply RLS policies in Supabase:

1. Go to **Supabase Dashboard → SQL Editor → New Query**
2. Paste the contents of `backend/alembic/rls_policies.sql`
3. Click **Run**
4. Verify under **Database → Tables** that each table shows the lock icon (🔒) indicating RLS is enabled
