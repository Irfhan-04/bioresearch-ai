"""API v1 router registration — BioResearch AI (8 routers)."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    dashboard,
    enrichment,
    export,
    researchers,
    scoring,
    search,
    users,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(researchers.router, prefix="/researchers", tags=["Researchers"])
api_router.include_router(search.router, prefix="/search", tags=["Search"])
api_router.include_router(enrichment.router, prefix="/enrich", tags=["Enrichment"])
api_router.include_router(scoring.router, prefix="/scoring", tags=["Scoring"])
api_router.include_router(export.router, prefix="/export", tags=["Export"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
