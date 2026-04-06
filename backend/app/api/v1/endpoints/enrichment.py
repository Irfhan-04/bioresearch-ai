"""
Enrichment API Endpoints
Enrich lead data with external APIs
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user, get_db
from app.models.lead import Lead
from app.models.usage import UsageEventType
from app.models.user import User
from app.schemas.base import BulkOperationResponse, MessageResponse
from app.services.enrichment_service import get_enrichment_service
from app.services.quota_manager import get_quota_manager
from app.services.usage_service import UsageService
from app.utils.rate_limiter import enrich_limiter

router = APIRouter()


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================


class EnrichLeadRequest(BaseModel):
    """Request to enrich a lead"""

    services: Optional[List[str]] = Field(
        None,
        description="Services to use (email, company, linkedin). None = all available",
    )

    model_config = {
        "json_schema_extra": {"example": {"services": ["email", "company"]}}
    }


class EnrichBatchRequest(BaseModel):
    """Request to enrich multiple leads"""

    lead_ids: List[UUID] = Field(..., min_length=1, max_length=100)
    services: Optional[List[str]] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "lead_ids": [
                    "123e4567-e89b-12d3-a456-426614174000",
                    "123e4567-e89b-12d3-a456-426614174001",
                ],
                "services": ["email", "linkedin"],
            }
        }
    }


# ============================================================================
# ENRICH MULTIPLE LEADS - MUST COME BEFORE SINGLE LEAD ROUTE
# ============================================================================


@router.post(
    "/leads/batch",  # This must come BEFORE /leads/{lead_id}
    response_model=BulkOperationResponse,
    summary="Enrich multiple leads",
    description="Enrich multiple leads in batch",
)
async def enrich_leads_batch(
    request: EnrichBatchRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Enrich multiple leads

    **Process:**
    - Processes up to 100 leads at once
    - Runs in background to avoid timeout
    - Uses caching to optimize API costs
    - Updates leads as enrichment completes

    **Best practices:**
    - Start with small batches (10-20 leads)
    - Check costs if using paid APIs
    - Monitor results in lead details
    """
    service = get_enrichment_service()

    # Validate lead limit
    if len(request.lead_ids) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 leads per batch",
        )

    try:
        # Execute batch enrichment
        results = await service.enrich_leads_batch(
            lead_ids=request.lead_ids,
            user=current_user,
            db=db,
            services=request.services,
        )

        successful_ids = [
            row["lead_id"] for row in results["results"] if row["status"] == "success"
        ]
        if successful_ids:
            await UsageService.record(
                db=db,
                user_id=current_user.id,
                event_type=UsageEventType.LEAD_ENRICHED,
                quantity=len(successful_ids),
                metadata={"source": "batch", "lead_count": len(successful_ids)},
            )
            await db.commit()

        return BulkOperationResponse(
            success_count=results["successful"],
            failure_count=results["failed"],
            total=results["total"],
            errors=[
                {"id": r["lead_id"], "error": r.get("error", "Unknown error")}
                for r in results["results"]
                if r["status"] != "success"
            ],
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch enrichment failed: {str(e)}",
        )


# ============================================================================
# ENRICH SINGLE LEAD - MUST COME AFTER BATCH ROUTE
# ============================================================================


@router.post(
    "/leads/{lead_id}",
    response_model=dict,
    summary="Enrich lead",
    description="Enrich a single lead with external data",
)
async def enrich_lead(
    lead_id: UUID,
    request: EnrichLeadRequest,
    http_request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Enrich a single lead

    **Available services:**
    - `email`: Find email address (Hunter.io)
    - `company`: Company data (Clearbit/Crunchbase)
    - `linkedin`: LinkedIn profile (free: Google CSE → DuckDuckGo → pattern)

    **Process:**
    1. Validates lead exists and belongs to user
    2. Checks which fields need enrichment
    3. Calls external APIs concurrently
    4. Updates lead with new data
    5. Caches results to reduce API costs

    **Returns:**
    - Enriched fields
    - Confidence scores
    - Data sources
    - Any errors
    """
    await enrich_limiter.check(http_request)

    service = get_enrichment_service()

    # Get lead
    result = await db.execute(
        select(Lead).where(and_(Lead.id == lead_id, Lead.user_id == current_user.id))
    )
    lead = result.scalar_one_or_none()

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found"
        )

    try:
        # Enrich lead
        enrichment_result = await service.enrich_lead(
            lead=lead, db=db, services=request.services
        )

        enriched_count = len(enrichment_result["enrichments"])
        if enriched_count > 0:
            await UsageService.record(
                db=db,
                user_id=current_user.id,
                event_type=UsageEventType.LEAD_ENRICHED,
                quantity=enriched_count,
                metadata={
                    "lead_id": str(lead.id),
                    "services": list(enrichment_result["enrichments"].keys()),
                },
            )
            await db.commit()

        # Extract pubmed-specific summary fields for the top-level response
        pubmed_data = enrichment_result["enrichments"].get("pubmed", {})
        score_boost = pubmed_data.get("score_boost", 0)
        tags_applied = pubmed_data.get("tags_applied", [])

        return {
            "lead_id": str(lead.id),
            "lead_name": lead.name,
            "enrichments": enrichment_result["enrichments"],
            "errors": enrichment_result["errors"],
            "success": len(enrichment_result["enrichments"]) > 0,
            "score_boost": score_boost,
            "tags_applied": tags_applied,
            "message": (
                f"Enriched {len(enrichment_result['enrichments'])} field(s)"
                + (f", score +{score_boost}" if score_boost else "")
            ),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Enrichment failed: {str(e)}",
        )


# ============================================================================
# GET ENRICHMENT STATUS
# ============================================================================


@router.get(
    "/leads/{lead_id}/status",
    response_model=dict,
    summary="Get enrichment status",
    description="Check which fields are enriched for a lead",
)
async def get_enrichment_status(
    lead_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get enrichment status

    Shows:
    - Which fields are enriched
    - Which fields are missing
    - Enrichment sources
    - Completion percentage
    - Last enrichment date
    """
    service = get_enrichment_service()

    # Get lead
    result = await db.execute(
        select(Lead).where(and_(Lead.id == lead_id, Lead.user_id == current_user.id))
    )
    lead = result.scalar_one_or_none()

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found"
        )

    status = await service.get_enrichment_status(lead)

    return status


# ============================================================================
# AVAILABLE SERVICES
# ============================================================================


@router.get(
    "/services",
    response_model=dict,
    summary="Get available services",
    description="List all available enrichment services",
)
async def get_available_services():
    """
    Get available enrichment services

    Shows:
    - Service name
    - Description
    - Status (configured/not configured)
    - Cost (free/paid)
    - Rate limits
    """
    quota_manager = get_quota_manager()
    hunter_status = await quota_manager.get_hunter_status()
    clearbit_status = await quota_manager.get_clearbit_status()

    services = {
        "email": {
            "name": "Email Finder",
            "description": (
                "Four-layer email discovery: "
                "NIH grant record → academic institution pattern → "
                "Hunter.io domain search → pattern fallback"
            ),
            "layers": {
                "nih_grant": "free — 0 API calls (from Step 4 enrichment)",
                "academic_pattern": "free — 0 API calls (institution type aware)",
                "hunter_domain": f"free {hunter_status['remaining']}/{hunter_status['limit']} remaining this month (score ≥ 70 only)",
                "pattern_fallback": "free — always available",
            },
            "cost": "Free",
            "fields_enriched": ["email"],
            "confidence_range": "0.40–0.98",
        },
        "company": {
            "name": "Company Enricher",
            "description": "Three-layer company enrichment: NIH data → Clearbit API → structural fallback",
            "layers": {
                "nih_data": "free — from NIH grant record (academic leads)",
                "clearbit": f"free {clearbit_status['remaining']}/{clearbit_status['limit']} remaining this month (score ≥ 50, pharma/unknown only)",
                "structural_mock": "always available fallback",
            },
            "cost": "Free",
            "fields_enriched": ["company_funding", "company_size", "company_hq"],
        },
        "linkedin": {
            "name": "LinkedIn Profile Finder",
            "description": "Google CSE + DuckDuckGo + pattern generation",
            "cost": "Free",
            "fields_enriched": ["linkedin_url"],
        },
        "pubmed": {
            "name": "PubMed Enrichment",
            "description": "Citation profile, h-index, publication velocity",
            "cost": "Free (NCBI Entrez API)",
            "fields_enriched": [
                "publication_count",
                "enrichment_data.pubmed.total_citations",
                "enrichment_data.pubmed.h_index_approx",
            ],
        },
    }

    return {
        "services": services,
        "quota_status": await quota_manager.get_all_quota_status(),
    }


@router.get(
    "/quota",
    response_model=dict,
    summary="Get API quota status",
    description="Check monthly quota usage for Hunter.io and Clearbit",
)
async def get_quota_status(
    current_user: User = Depends(get_current_active_user),
):
    """
    Get current month's API quota usage.

    Shows:
    - Hunter.io: used/remaining (25/month, score ≥ 70 leads only)
    - Clearbit: used/remaining (50/month, pharma leads score ≥ 50 only)
    - Reset date: first of next month
    """
    quota_manager = get_quota_manager()
    return await quota_manager.get_all_quota_status()
