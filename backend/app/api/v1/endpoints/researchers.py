"""Researcher Management Endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import check_researcher_quota, get_current_active_user, get_db
from app.models.researcher import Researcher
from app.models.team import TeamMembership
from app.models.user import User
from app.schemas.base import BulkDeleteRequest, BulkOperationResponse, MessageResponse, PaginatedResponse
from app.schemas.researcher import (
    ResearcherBulkCreate,
    ResearcherCreate,
    ResearcherDetail,
    ResearcherList,
    ResearcherUpdate,
)
from app.utils.rate_limiter import leads_limiter

router = APIRouter(tags=["Researchers"])


def prepare_researcher_for_serialization(researcher: Researcher) -> None:
    _ = (
        researcher.id,
        researcher.user_id,
        researcher.name,
        researcher.title,
        researcher.company,
        researcher.location,
        researcher.email,
        researcher.propensity_score,
        researcher.priority_tier,
        researcher.status,
        researcher.created_at,
        researcher.updated_at,
    )


@router.get("", response_model=PaginatedResponse)
async def list_researchers(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    search: Optional[str] = Query(None),
    request: Request = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await leads_limiter.check(request)

    team_ids_subq = (
        select(TeamMembership.team_id)
        .where(TeamMembership.user_id == current_user.id)
        .scalar_subquery()
    )

    query = select(Researcher).where(
        or_(Researcher.user_id == current_user.id, Researcher.team_id.in_(team_ids_subq))
    )

    if search:
        query = query.where(
            or_(
                Researcher.name.ilike(f"%{search}%"),
                Researcher.title.ilike(f"%{search}%"),
                Researcher.company.ilike(f"%{search}%"),
            )
        )

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    sort_column = getattr(Researcher, sort_by, Researcher.created_at)
    query = query.order_by(sort_column.desc() if sort_order == "desc" else sort_column.asc())
    query = query.offset((page - 1) * size).limit(size)

    researchers = (await db.execute(query)).scalars().all()
    for researcher in researchers:
        prepare_researcher_for_serialization(researcher)

    items = [ResearcherList.model_validate(r, from_attributes=True) for r in researchers]
    return PaginatedResponse.create(items=items, page=page, size=size, total=total)


@router.post("", response_model=ResearcherDetail, status_code=status.HTTP_201_CREATED)
async def create_researcher(
    researcher_data: ResearcherCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_researcher_quota),
):
    await leads_limiter.check(request)

    if researcher_data.email:
        existing = await db.execute(
            select(Researcher).where(
                and_(Researcher.user_id == current_user.id, Researcher.email == researcher_data.email)
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Researcher with this email already exists")

    researcher = Researcher(user_id=current_user.id, **researcher_data.model_dump())
    researcher.add_data_source("manual")
    db.add(researcher)
    await db.commit()
    await db.refresh(researcher)

    prepare_researcher_for_serialization(researcher)
    return ResearcherDetail.model_validate(researcher, from_attributes=True)


@router.get("/{researcher_id}", response_model=ResearcherDetail)
async def get_researcher(
    researcher_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    researcher = (
        await db.execute(
            select(Researcher).where(
                and_(Researcher.id == researcher_id, Researcher.user_id == current_user.id)
            )
        )
    ).scalar_one_or_none()
    if not researcher:
        raise HTTPException(status_code=404, detail="Researcher not found")

    prepare_researcher_for_serialization(researcher)
    return ResearcherDetail.model_validate(researcher, from_attributes=True)


@router.put("/{researcher_id}", response_model=ResearcherDetail)
async def update_researcher(
    researcher_id: UUID,
    researcher_updates: ResearcherUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    researcher = (
        await db.execute(
            select(Researcher).where(
                and_(Researcher.id == researcher_id, Researcher.user_id == current_user.id)
            )
        )
    ).scalar_one_or_none()
    if not researcher:
        raise HTTPException(status_code=404, detail="Researcher not found")

    for field, value in researcher_updates.model_dump(exclude_none=True).items():
        setattr(researcher, field, value)

    await db.commit()
    await db.refresh(researcher)
    return ResearcherDetail.model_validate(researcher, from_attributes=True)


@router.delete("/{researcher_id}", response_model=MessageResponse)
async def delete_researcher(
    researcher_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    researcher = (
        await db.execute(
            select(Researcher).where(
                and_(Researcher.id == researcher_id, Researcher.user_id == current_user.id)
            )
        )
    ).scalar_one_or_none()
    if not researcher:
        raise HTTPException(status_code=404, detail="Researcher not found")

    await db.delete(researcher)
    await db.commit()
    return MessageResponse(message="Researcher deleted successfully")


@router.post("/bulk/delete", response_model=BulkOperationResponse)
async def bulk_delete_researchers(
    request: BulkDeleteRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    success_count = 0
    errors = []

    for researcher_id in request.ids:
        researcher = (
            await db.execute(
                select(Researcher).where(
                    and_(Researcher.id == researcher_id, Researcher.user_id == current_user.id)
                )
            )
        ).scalar_one_or_none()
        if researcher:
            await db.delete(researcher)
            success_count += 1
        else:
            errors.append({"id": str(researcher_id), "error": "Not found"})

    await db.commit()
    return BulkOperationResponse(
        success_count=success_count,
        failure_count=len(errors),
        total=len(request.ids),
        errors=errors,
    )


@router.post("/bulk/create", response_model=BulkOperationResponse)
async def bulk_create_researchers(
    request: ResearcherBulkCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_researcher_quota),
):
    success_count = 0
    errors = []

    for idx, researcher_data in enumerate(request.leads):
        try:
            researcher = Researcher(user_id=current_user.id, **researcher_data.model_dump())
            researcher.add_data_source("bulk_import")
            db.add(researcher)
            success_count += 1
        except Exception as exc:
            errors.append({"row": idx + 1, "error": str(exc)})

    await db.commit()
    return BulkOperationResponse(
        success_count=success_count,
        failure_count=len(errors),
        total=len(request.leads),
        errors=errors,
    )
