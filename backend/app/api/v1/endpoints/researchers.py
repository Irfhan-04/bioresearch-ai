"""
Lead Management Endpoints - WITHOUT SCORING SERVICE
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import check_lead_quota, get_current_active_user, get_db
from app.models.lead import Lead
from app.models.team import TeamMembership
from app.models.usage import UsageEventType
from app.models.user import User
from app.schemas.base import (BulkDeleteRequest, BulkOperationResponse,
                              MessageResponse, PaginatedResponse,
                              SuccessResponse)
from app.schemas.lead import (LeadBulkCreate, LeadCreate, LeadDetail, LeadList,
                              LeadUpdate)
from app.services.tier_quota_service import TierQuotaService
from app.services.usage_service import UsageService
from app.utils.rate_limiter import leads_limiter

# COMMENTED OUT FOR NOW - Phase 2 feature
# from app.services.scoring_service import ScoringService


router = APIRouter()


def prepare_lead_for_serialization(lead: Lead) -> None:
    """Force eager loading of all Lead attributes."""
    _ = (
        lead.id,
        lead.user_id,
        lead.name,
        lead.title,
        lead.company,
        lead.location,
        lead.company_hq,
        lead.email,
        lead.phone,
        lead.linkedin_url,
        lead.twitter_url,
        lead.website,
        lead.propensity_score,
        lead.rank,
        lead.priority_tier,
        lead.recent_publication,
        lead.publication_year,
        lead.publication_title,
        lead.publication_count,
        lead.company_funding,
        lead.company_size,
        lead.uses_3d_models,
        lead.status,
        lead.notes,
        lead.last_contacted_at,
        lead.created_at,
        lead.updated_at,
    )
    _ = lead.data_sources or []
    _ = lead.enrichment_data or {}
    _ = lead.custom_fields or {}
    _ = lead.tags or []


@router.get("", response_model=PaginatedResponse)
async def list_leads(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    search: Optional[str] = Query(None),
    min_score: Optional[int] = Query(None, ge=0, le=100),
    max_score: Optional[int] = Query(None, ge=0, le=100),
    priority_tier: Optional[str] = Query(None, regex="^(HIGH|MEDIUM|LOW)$"),
    status: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    has_email: Optional[bool] = Query(None),
    has_publication: Optional[bool] = Query(None),
    request: Request = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's leads with pagination, filtering, and sorting"""

    await leads_limiter.check(request)

    query = select(Lead)

    team_ids_subq = (
        select(TeamMembership.team_id)
        .where(TeamMembership.user_id == current_user.id)
        .scalar_subquery()
    )

    query = query.where(
        or_(
            Lead.user_id == current_user.id,
            Lead.team_id.in_(team_ids_subq),
        )
    )

    if search:
        query = query.where(
            or_(
                Lead.name.ilike(f"%{search}%"),
                Lead.title.ilike(f"%{search}%"),
                Lead.company.ilike(f"%{search}%"),
            )
        )

    if min_score is not None:
        query = query.where(Lead.propensity_score >= min_score)

    if max_score is not None:
        query = query.where(Lead.propensity_score <= max_score)

    if priority_tier:
        query = query.where(Lead.priority_tier == priority_tier)

    if status:
        query = query.where(Lead.status == status)

    if location:
        query = query.where(Lead.location.ilike(f"%{location}%"))

    if has_email is not None:
        query = query.where(
            Lead.email.isnot(None) if has_email else Lead.email.is_(None)
        )

    if has_publication is not None:
        query = query.where(Lead.recent_publication == has_publication)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    sort_column = getattr(Lead, sort_by, Lead.created_at)
    query = query.order_by(
        sort_column.desc() if sort_order == "desc" else sort_column.asc()
    )
    query = query.offset((page - 1) * size).limit(size)

    result = await db.execute(query)
    leads = result.scalars().all()

    for lead in leads:
        prepare_lead_for_serialization(lead)

    lead_list = [LeadList.model_validate(lead, from_attributes=True) for lead in leads]

    return PaginatedResponse.create(items=lead_list, page=page, size=size, total=total)


@router.post("", response_model=LeadDetail, status_code=status.HTTP_201_CREATED)
async def create_lead(
    lead_data: LeadCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_lead_quota),
):
    """Create new lead"""

    await leads_limiter.check(request)

    if lead_data.email:
        existing = await db.execute(
            select(Lead).where(
                and_(Lead.user_id == current_user.id, Lead.email == lead_data.email)
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lead with this email already exists",
            )

    await TierQuotaService.check_and_enforce(db, current_user, "leads")

    lead = Lead(user_id=current_user.id, **lead_data.model_dump())

    # SCORING DISABLED - Phase 2 feature
    # scoring_service = ScoringService()
    # lead.propensity_score = scoring_service.calculate_score(lead)
    # lead.update_priority_tier()

    lead.add_data_source("manual")

    db.add(lead)
    await UsageService.record(
        db=db,
        user_id=current_user.id,
        event_type=UsageEventType.LEAD_CREATED,
        metadata={"source": lead.data_sources},
    )
    await db.commit()
    await db.refresh(lead)

    lead_id = lead.id

    await update_lead_ranks(current_user.id, db)

    current_user.increment_usage("leads_created_this_month")
    await db.commit()

    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one()

    prepare_lead_for_serialization(lead)

    return LeadDetail.model_validate(lead, from_attributes=True)


@router.get("/{lead_id}", response_model=LeadDetail)
async def get_lead(
    lead_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get lead details"""

    result = await db.execute(
        select(Lead).where(and_(Lead.id == lead_id, Lead.user_id == current_user.id))
    )
    lead = result.scalar_one_or_none()

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found"
        )

    prepare_lead_for_serialization(lead)

    return LeadDetail.model_validate(lead, from_attributes=True)


@router.put("/{lead_id}", response_model=LeadDetail)
async def update_lead(
    lead_id: UUID,
    lead_updates: LeadUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update lead"""

    result = await db.execute(
        select(Lead).where(and_(Lead.id == lead_id, Lead.user_id == current_user.id))
    )
    lead = result.scalar_one_or_none()

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found"
        )

    for field, value in lead_updates.model_dump(exclude_none=True).items():
        setattr(lead, field, value)

    await db.commit()
    await db.refresh(lead)

    prepare_lead_for_serialization(lead)

    return LeadDetail.model_validate(lead, from_attributes=True)


@router.delete("/{lead_id}", response_model=MessageResponse)
async def delete_lead(
    lead_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete lead"""

    result = await db.execute(
        select(Lead).where(and_(Lead.id == lead_id, Lead.user_id == current_user.id))
    )
    lead = result.scalar_one_or_none()

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found"
        )

    await db.delete(lead)
    await db.commit()
    await update_lead_ranks(current_user.id, db)

    return MessageResponse(message="Lead deleted successfully")


@router.post("/bulk/delete", response_model=BulkOperationResponse)
async def bulk_delete_leads(
    request: BulkDeleteRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Bulk delete leads"""

    success_count = 0
    errors = []

    for lead_id in request.ids:
        try:
            result = await db.execute(
                select(Lead).where(
                    and_(Lead.id == lead_id, Lead.user_id == current_user.id)
                )
            )
            lead = result.scalar_one_or_none()

            if lead:
                await db.delete(lead)
                success_count += 1
            else:
                errors.append({"id": str(lead_id), "error": "Not found"})
        except Exception as e:
            errors.append({"id": str(lead_id), "error": str(e)})

    await db.commit()
    await update_lead_ranks(current_user.id, db)

    return BulkOperationResponse(
        success_count=success_count,
        failure_count=len(errors),
        total=len(request.ids),
        errors=errors,
    )


@router.post("/bulk/create", response_model=BulkOperationResponse)
async def bulk_create_leads(
    request: LeadBulkCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_lead_quota),
):
    """Bulk create leads"""

    success_count = 0
    errors = []
    # SCORING DISABLED - Phase 2 feature
    # scoring_service = ScoringService() if request.calculate_scores else None

    for idx, lead_data in enumerate(request.leads):
        try:
            if request.skip_duplicates and lead_data.email:
                existing = await db.execute(
                    select(Lead).where(
                        and_(
                            Lead.user_id == current_user.id,
                            Lead.email == lead_data.email,
                        )
                    )
                )
                if existing.scalar_one_or_none():
                    errors.append({"row": idx + 1, "error": "Duplicate"})
                    continue

            await TierQuotaService.check_and_enforce(db, current_user, "leads")

            lead = Lead(user_id=current_user.id, **lead_data.model_dump())

            # SCORING DISABLED
            # if scoring_service:
            #     lead.propensity_score = scoring_service.calculate_score(lead)
            #     lead.update_priority_tier()

            lead.add_data_source("bulk_import")
            db.add(lead)
            success_count += 1

        except Exception as e:
            errors.append({"row": idx + 1, "error": str(e)})

    await db.commit()

    if success_count > 0:
        await update_lead_ranks(current_user.id, db)
        current_user.increment_usage("leads_created_this_month", success_count)
        await db.commit()

    return BulkOperationResponse(
        success_count=success_count,
        failure_count=len(errors),
        total=len(request.leads),
        errors=errors,
    )


# SCORING ENDPOINTS - DISABLED FOR PHASE 2
# Uncomment these when implementing scoring service

# @router.post("/{lead_id}/score", response_model=LeadDetail)
# async def recalculate_score(...):
#     """Recalculate lead score"""
#     pass

# @router.post("/bulk/recalculate-scores", response_model=SuccessResponse)
# async def recalculate_all_scores(...):
#     """Recalculate all lead scores"""
#     pass


async def update_lead_ranks(user_id: UUID, db: AsyncSession):
    """Update ranks based on score"""
    result = await db.execute(
        select(Lead)
        .where(Lead.user_id == user_id)
        .order_by(Lead.propensity_score.desc())
    )
    for rank, lead in enumerate(result.scalars().all(), start=1):
        lead.rank = rank
    await db.commit()
