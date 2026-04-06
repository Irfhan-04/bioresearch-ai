"""
Search API Endpoints
Execute searches, manage search history, view results
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user, get_db
from app.models.search import Search
from app.models.user import User
from app.schemas.base import (MessageResponse, PaginatedResponse,
                              SuccessResponse)
from app.schemas.search import SearchCreate, SearchResponse
from app.services.data_quality_service import get_data_quality_service
from app.services.data_source_manager import get_data_source_manager
from app.services.tier_quota_service import TierQuotaService
from app.services.usage_service import UsageService
from app.models.usage import UsageEventType
from app.services.search_service import get_search_service
from app.utils.rate_limiter import search_limiter

router = APIRouter()


# ============================================================================
# EXECUTE SEARCH
# ============================================================================


@router.post(
    "",
    response_model=dict,
    summary="Execute search",
    description="Search for researchers across data sources",
)
async def execute_search(
    search_data: SearchCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Execute a search for researchers

    **Supported search types:**
    - `pubmed`: Search PubMed for researchers
    - `linkedin`: Search LinkedIn (coming soon)
    - `conference`: Search conference attendees (coming soon)

    **Example queries:**
    - "drug-induced liver injury 3D models"
    - "hepatotoxicity organoids"
    - "DILI prediction in vitro"

    **Returns:**
    - `search_id`: ID of search record
    - `results_count`: Number of results found
    - `researchers_created`: Number of leads created
    - `execution_time_ms`: Time taken in milliseconds
    - `lead_ids`: IDs of created leads (if create_leads=true)
    """
    await search_limiter.check(request)

    service = get_search_service()

    try:
        await TierQuotaService.check_and_enforce(db, current_user, "searches")
        results = await service.execute_search(
            query=search_data.query,
            search_type=search_data.search_type,
            user=current_user,
            db=db,
            filters=search_data.filters,
            save_search=search_data.save_search,
            saved_name=search_data.saved_name,
            create_leads=True,  # Always create researchers for now
            max_results=50,
        )

        await UsageService.record(
            db=db,
            user_id=current_user.id,
            event_type=UsageEventType.SEARCH_EXECUTED,
            quantity=1,
            metadata={"search_type": search_data.search_type, "query": search_data.query},
        )
        await db.commit()

        return {
            **results,
            "message": f"Search completed. Found {results['results_count']} results, created {results['researchers_created']} leads.",
        }

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        )


# ============================================================================
# SEARCH HISTORY
# ============================================================================


@router.get(
    "/history",
    response_model=PaginatedResponse,
    summary="Get search history",
    description="Get user's search history with pagination",
)
async def get_search_history(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Items per page"),
    saved_only: bool = Query(False, description="Show only saved searches"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get search history

    Returns paginated list of previous searches with:
    - Query text
    - Search type
    - Results count
    - Execution time
    - Whether saved
    - Timestamp
    """
    service = get_search_service()

    searches, total = await service.get_search_history(
        user=current_user, db=db, page=page, size=size, saved_only=saved_only
    )

    # Convert to response schema
    search_responses = [
        SearchResponse.model_validate(search, from_attributes=True)
        for search in searches
    ]

    return PaginatedResponse.create(
        items=search_responses, page=page, size=size, total=total
    )


# ============================================================================
# GET SPECIFIC SEARCH
# ============================================================================


@router.get(
    "/{search_id}",
    response_model=SearchResponse,
    summary="Get search details",
    description="Get detailed information about a specific search",
)
async def get_search(
    search_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get search details

    Returns complete information about a search including:
    - Query and filters
    - Results count
    - Created leads
    - Execution time
    """
    from sqlalchemy import and_

    result = await db.execute(
        select(Search).where(
            and_(Search.id == search_id, Search.user_id == current_user.id)
        )
    )
    search = result.scalar_one_or_none()

    if not search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Search not found"
        )

    return SearchResponse.model_validate(search, from_attributes=True)


# ============================================================================
# SAVE SEARCH
# ============================================================================


@router.post(
    "/{search_id}/save",
    response_model=SearchResponse,
    summary="Save search",
    description="Save a search for later reference",
)
async def save_search(
    search_id: UUID,
    saved_name: str = Query(
        ..., min_length=1, max_length=255, description="Name for saved search"
    ),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Save a search

    Saved searches can be:
    - Re-run with same parameters
    - Easily found in search history
    - Used as templates for new searches
    """
    service = get_search_service()

    try:
        await TierQuotaService.check_and_enforce(db, current_user, "searches")
        search = await service.save_search(
            search_id=str(search_id), name=saved_name, user=current_user, db=db
        )

        return SearchResponse.model_validate(search, from_attributes=True)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ============================================================================
# RERUN SEARCH
# ============================================================================


@router.post(
    "/{search_id}/rerun",
    response_model=dict,
    summary="Re-run search",
    description="Re-execute a previous search with same parameters",
)
async def rerun_search(
    search_id: UUID,
    create_leads: bool = Query(True, description="Create new leads"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Re-run a search

    Useful for:
    - Finding new publications
    - Refreshing lead data
    - Periodic searches (before pipelines)

    Creates a new search record with fresh results.
    """
    service = get_search_service()

    try:
        await TierQuotaService.check_and_enforce(db, current_user, "searches")
        results = await service.rerun_search(
            search_id=str(search_id),
            user=current_user,
            db=db,
            create_leads=create_leads,
        )

        await UsageService.record(
            db=db,
            user_id=current_user.id,
            event_type=UsageEventType.SEARCH_EXECUTED,
            quantity=1,
            metadata={"search_type": search_data.search_type, "query": search_data.query},
        )
        await db.commit()

        return {
            **results,
            "message": f"Search re-run completed. Found {results['results_count']} results.",
        }

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ============================================================================
# DELETE SEARCH
# ============================================================================


@router.delete(
    "/{search_id}",
    response_model=MessageResponse,
    summary="Delete search",
    description="Delete a search from history",
)
async def delete_search(
    search_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a search from history

    Note: This does NOT delete the leads created by the search,
    only the search record itself.
    """
    from sqlalchemy import and_

    result = await db.execute(
        select(Search).where(
            and_(Search.id == search_id, Search.user_id == current_user.id)
        )
    )
    search = result.scalar_one_or_none()

    if not search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Search not found"
        )

    await db.delete(search)
    await db.commit()

    return MessageResponse(message="Search deleted successfully")


# ============================================================================
# DATA SOURCE STATUS
# ============================================================================


@router.get(
    "/status/sources",
    response_model=dict,
    summary="Get data source status",
    description="Check status and availability of all data sources",
)
async def get_data_source_status():
    """
    Get data source status

    Shows which data sources are:
    - Available
    - Configured correctly
    - Ready to use

    Useful for troubleshooting search issues.
    """
    manager = get_data_source_manager()

    status = await manager.get_source_status()

    return {"status": "healthy", "timestamp": "2024-12-30T12:00:00Z", **status}


# ============================================================================
# DATA QUALITY METRICS
# ============================================================================


@router.get(
    "/status/quality",
    response_model=dict,
    summary="Get data quality metrics",
    description="Returns quality statistics for leads in the database",
)
async def get_data_quality_metrics(
    limit: int = Query(
        500,
        ge=10,
        le=2000,
        description="Max leads to sample for quality check",
    ),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get quality health metrics for the current user's leads."""
    from app.models.researcher import Researcher

    result = await db.execute(
        select(Researcher)
        .where(Researcher.user_id == current_user.id)
        .order_by(Researcher.created_at.desc())
        .limit(limit)
    )
    researchers = result.scalars().all()

    if not researchers:
        return {
            "status": "no_leads",
            "total_sampled": 0,
            "message": "No leads found. Run a search first.",
        }

    quality_svc = get_data_quality_service()

    passed = 0
    issue_tally: Dict[str, int] = {}
    field_missing: Dict[str, int] = {}
    completeness_sum = 0.0

    for researcher in researchers:
        qr = quality_svc.check_existing_lead(researcher)
        completeness_sum += qr.completeness

        if qr.passes:
            passed += 1

        for issue in qr.issues:
            category = issue.split(":")[0]
            issue_tally[category] = issue_tally.get(category, 0) + 1

        for field_name, present in qr.field_scores.items():
            if not present:
                field_missing[field_name] = field_missing.get(field_name, 0) + 1

    total = len(researchers)
    avg_completeness = completeness_sum / total
    top_issues = sorted(issue_tally.items(), key=lambda item: item[1], reverse=True)
    top_missing = sorted(field_missing.items(), key=lambda item: item[1], reverse=True)

    return {
        "status": "healthy" if (passed / total) > 0.8 else "degraded",
        "total_sampled": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 3),
        "avg_completeness": round(avg_completeness, 3),
        "top_issues": dict(top_issues[:5]),
        "missing_fields": dict(top_missing[:5]),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
