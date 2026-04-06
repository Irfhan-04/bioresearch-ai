"""API v1 router registration — Phase 2.6 (16 routers)."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    alerts,
    analytics,
    auth,
    dashboard,
    billing,
    collaboration,
    crm,
    enrichment,
    export,
    leads,
    pipelines,
    reports,
    scoring,
    search,
    stripe_webhooks,
    teams,
    users,
    webhooks,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(leads.router, prefix="/leads", tags=["Leads"])
api_router.include_router(search.router, prefix="/search", tags=["Search"])
api_router.include_router(export.router, prefix="/export", tags=["Export"])
api_router.include_router(enrichment.router, prefix="/enrich", tags=["Enrichment"])
api_router.include_router(pipelines.router, prefix="/pipelines", tags=["Pipelines"])
api_router.include_router(billing.router, prefix="/billing", tags=["Billing"])
api_router.include_router(stripe_webhooks.router, prefix="/webhooks", tags=["Webhooks - Stripe"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
api_router.include_router(teams.router, prefix="/teams", tags=["Teams"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
api_router.include_router(scoring.router, prefix="/scoring", tags=["Scoring"])
api_router.include_router(crm.router, prefix="/crm", tags=["CRM"])
api_router.include_router(collaboration.router, prefix="/collaboration", tags=["Collaboration"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
