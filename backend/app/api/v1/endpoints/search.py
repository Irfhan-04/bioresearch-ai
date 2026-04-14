"""
Search API Endpoints
Execute searches, manage search history, view results
"""

import logging
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import check_search_quota, get_current_active_user, get_db, get_optional_user
from app.models.search import Search
from app.models.user import User
from app.schemas.base import (MessageResponse, PaginatedResponse,
                              SuccessResponse)
from app.schemas.search import SearchCreate, SearchResponse
from app.services.data_quality_service import get_data_quality_service
from app.services.data_source_manager import get_data_source_manager
from app.services.search_service import get_search_service
from app.utils.rate_limiter import search_limiter

router = APIRouter()
logger = logging.getLogger(__name__)


# ============================================================================
# EXECUTE SEARCH
# ============================================================================


@router.post(
    "",
    response_model=dict,
    summary="Execute search",
    description="Semantic + hybrid search. Guest: 3/day. Registered (free): 20/day.",
)
async def execute_search(
    search_data: SearchCreate,
    request: Request,
    quota: dict = Depends(check_search_quota),          # enforces daily limit
    current_user: Optional[User] = Depends(get_optional_user),  # None for guests
    db: AsyncSession = Depends(get_db),
):
    """
    Execute a semantic + hybrid search for researchers.

    Hybrid ranking formula:
        hybrid_score = 0.6 × semantic_similarity + 0.4 × (relevance_score / 100)
    """
    await search_limiter.check(request)

    from app.models.researcher import Researcher as ResearcherModel
    from app.services.embedding_service import get_embedding_service

    service = get_search_service()
    embedding_svc = get_embedding_service()
    query = search_data.query
    research_area_filter = (search_data.filters or {}).get("research_area")

    try:
        pubmed_results = await service.execute_search(
            query=query,
            search_type=search_data.search_type,
            user=current_user,
            db=db,
            filters=search_data.filters,
            save_search=search_data.save_search,
            saved_name=search_data.saved_name,
            create_leads=True,  # Always create researchers for now
            max_results=50,
        )

        semantic_hits = await embedding_svc.semantic_search(
            query=query,
            n_results=50,
            research_area_filter=research_area_filter,
        )

        if not semantic_hits:
            return {
                **pubmed_results,
                "quota": quota,
                "semantic_search_available": False,
                "message": (
                    f"Found {pubmed_results['results_count']} results. "
                    "Semantic search will be available after researchers are enriched."
                ),
            }

        semantic_ids = [hit[0] for hit in semantic_hits]
        semantic_scores = {hit[0]: hit[1] for hit in semantic_hits}

        result = await db.execute(
            select(ResearcherModel).where(
                ResearcherModel.id.in_(semantic_ids),
                ResearcherModel.user_id == current_user.id,
            )
        )
        researchers = result.scalars().all()

        ranked_researchers = []
        for researcher in researchers:
            researcher_id = str(researcher.id)
            semantic_sim = semantic_scores.get(researcher_id, 0.0)
            relevance_score = (researcher.relevance_score or 0) / 100.0
            hybrid_score = 0.6 * semantic_sim + 0.4 * relevance_score

            ranked_researchers.append(
                {
                    "id": researcher_id,
                    "name": researcher.name,
                    "title": researcher.title,
                    "company": researcher.company,
                    "location": researcher.location,
                    "relevance_score": researcher.relevance_score,
                    "relevance_tier": researcher.relevance_tier,
                    "research_area": researcher.research_area,
                    "semantic_similarity": round(semantic_sim, 4),
                    "hybrid_score": round(hybrid_score, 4),
                    "shap_contributions": researcher.shap_contributions,
                    "recent_publication": researcher.recent_publication,
                    "publication_count": researcher.publication_count,
                    "email": researcher.email,
                }
            )

        ranked_researchers.sort(key=lambda item: item["hybrid_score"], reverse=True)

        return {
            "search_id": pubmed_results.get("search_id"),
            "query": query,
            "results_count": len(ranked_researchers),
            "researchers_created": pubmed_results.get("researchers_created", 0),
            "quota": quota,
            "semantic_search_available": True,
            "researchers": ranked_researchers,
            "message": (
                f"Semantic + hybrid search complete. "
                f"Returned {len(ranked_researchers)} ranked results."
            ),
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Search failed")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get(
    "/semantic",
    response_model=dict,
    summary="Direct semantic search",
    description="Search existing indexed researchers by semantic similarity",
)
async def semantic_search(
    query: str = Query(..., min_length=2, description="Natural language search query"),
    research_area: Optional[str] = Query(None, description="Filter by research area"),
    n_results: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Semantic-only search over the ChromaDB index."""
    from app.models.researcher import Researcher as ResearcherModel
    from app.services.embedding_service import get_embedding_service

    embedding_svc = get_embedding_service()
    semantic_hits = await embedding_svc.semantic_search(
        query=query,
        n_results=n_results,
        research_area_filter=research_area,
    )

    if not semantic_hits:
        return {
            "query": query,
            "results_count": 0,
            "researchers": [],
            "message": "No indexed researchers found. Run enrichment to build the semantic index.",
        }

    semantic_ids = [hit[0] for hit in semantic_hits]
    semantic_scores = {hit[0]: hit[1] for hit in semantic_hits}

    result = await db.execute(
        select(ResearcherModel).where(
            ResearcherModel.id.in_(semantic_ids),
            ResearcherModel.user_id == current_user.id,
        )
    )
    researchers = result.scalars().all()

    ranked = []
    for researcher in researchers:
        researcher_id = str(researcher.id)
        semantic_sim = semantic_scores.get(researcher_id, 0.0)
        relevance_score = (researcher.relevance_score or 0) / 100.0
        hybrid_score = 0.6 * semantic_sim + 0.4 * relevance_score

        ranked.append(
            {
                "id": researcher_id,
                "name": researcher.name,
                "title": researcher.title,
                "company": researcher.company,
                "research_area": researcher.research_area,
                "relevance_score": researcher.relevance_score,
                "relevance_tier": researcher.relevance_tier,
                "semantic_similarity": round(semantic_sim, 4),
                "hybrid_score": round(hybrid_score, 4),
                "abstract_relevance_score": researcher.abstract_relevance_score,
                "shap_contributions": researcher.shap_contributions,
            }
        )

    ranked.sort(key=lambda item: item["hybrid_score"], reverse=True)

    return {
        "query": query,
        "results_count": len(ranked),
        "researchers": ranked,
    }


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
    - Created researchers
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
    create_leads: bool = Query(True, description="Create new researchers"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Re-run a search

    Useful for:
    - Finding new publications
    - Refreshing researcher data
    - Periodic searches (before scheduled refresh jobs)

    Creates a new search record with fresh results.
    """
    service = get_search_service()

    try:
        results = await service.rerun_search(
            search_id=str(search_id),
            user=current_user,
            db=db,
            create_leads=create_leads,
        )

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

    Note: This does NOT delete the researchers created by the search,
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
    description="Returns quality statistics for researchers in the database",
)
async def get_data_quality_metrics(
    limit: int = Query(
        500,
        ge=10,
        le=2000,
        description="Max researchers to sample for quality check",
    ),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get quality health metrics for the current user's researchers."""
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
            "status": "no_researchers",
            "total_sampled": 0,
            "message": "No researchers found. Run a search first.",
        }

    quality_svc = get_data_quality_service()

    passed = 0
    issue_tally: Dict[str, int] = {}
    field_missing: Dict[str, int] = {}
    completeness_sum = 0.0

    for researcher in researchers:
        qr = quality_svc.check_existing_researcher(researcher)
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
