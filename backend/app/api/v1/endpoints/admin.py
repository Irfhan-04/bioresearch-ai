"""Admin-only endpoints for user management, flags, tickets, and health."""

from __future__ import annotations

from datetime import date, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func as sa_func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import Cache
from app.core.deps import get_current_active_user, get_db
from app.models.admin import FeatureFlag, SupportTicket, TicketPriority, TicketStatus
from app.models.usage import UsageEvent, UsageEventType
from app.models.user import User
from app.schemas.base import MessageResponse
from app.schemas.usage import AdminUserSummary

router = APIRouter()


def _require_superuser(user: User):
    if not user.is_superuser:
        raise HTTPException(403, "Superuser access required")


@router.get("/users", response_model=List[AdminUserSummary], summary="List all users")
async def list_users(
    skip: int = 0,
    limit: int = Query(50, le=200),
    tier: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    _require_superuser(current_user)

    query = select(User)
    if tier:
        query = query.where(User.subscription_tier == tier)
    if search:
        query = query.where(User.email.ilike(f"%{search}%"))
    query = query.offset(skip).limit(limit).order_by(User.created_at.desc())

    users = (await db.execute(query)).scalars().all()
    since_30d = date.today() - timedelta(days=30)
    summaries = []
    for user in users:
        leads_30d_result = await db.execute(
            select(sa_func.coalesce(sa_func.sum(UsageEvent.quantity), 0)).where(
                UsageEvent.user_id == user.id,
                UsageEvent.event_type == UsageEventType.LEAD_CREATED,
                UsageEvent.occurred_at >= since_30d,
            )
        )
        summaries.append(
            AdminUserSummary(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                tier=str(user.subscription_tier),
                is_active=user.is_active,
                is_superuser=user.is_superuser,
                created_at=user.created_at,
                leads_30d=int(leads_30d_result.scalar() or 0),
                last_login_at=user.last_login_at,
            )
        )
    return summaries


@router.patch("/users/{user_id}/status", response_model=MessageResponse)
async def toggle_user_status(
    user_id: UUID,
    active: bool,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    _require_superuser(current_user)
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    user.is_active = active
    await db.commit()
    return {"message": f"User {'activated' if active else 'deactivated'}"}


@router.get("/flags", summary="List all feature flags")
async def list_flags(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    _require_superuser(current_user)
    result = await db.execute(select(FeatureFlag).order_by(FeatureFlag.key))
    return result.scalars().all()


@router.put("/flags/{key}", summary="Create or update a feature flag")
async def upsert_flag(
    key: str,
    enabled: bool,
    description: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    _require_superuser(current_user)
    flag = (await db.execute(select(FeatureFlag).where(FeatureFlag.key == key))).scalar_one_or_none()

    if flag:
        flag.enabled = enabled
        flag.updated_by = current_user.id
        if description:
            flag.description = description
    else:
        db.add(
            FeatureFlag(
                key=key,
                enabled=enabled,
                description=description,
                updated_by=current_user.id,
            )
        )

    await db.commit()
    await Cache.delete(f"feature_flag:{key}")
    return {"key": key, "enabled": enabled}


async def is_flag_enabled(key: str, db: AsyncSession) -> bool:
    cached = await Cache.get(f"feature_flag:{key}")
    if cached is not None:
        return cached == "1"

    flag = (await db.execute(select(FeatureFlag).where(FeatureFlag.key == key))).scalar_one_or_none()
    enabled = flag.enabled if flag else False
    await Cache.set(f"feature_flag:{key}", "1" if enabled else "0", ttl=300)
    return enabled


@router.get("/tickets", summary="[Admin] List support tickets")
async def list_tickets(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    _require_superuser(current_user)
    query = select(SupportTicket)
    if status:
        query = query.where(SupportTicket.status == TicketStatus(status))
    if priority:
        query = query.where(SupportTicket.priority == TicketPriority(priority))
    query = query.order_by(SupportTicket.created_at.desc()).offset(skip).limit(limit)
    return (await db.execute(query)).scalars().all()


@router.patch("/tickets/{ticket_id}", summary="[Admin] Update ticket status/notes")
async def update_ticket(
    ticket_id: UUID,
    status: Optional[str] = None,
    admin_notes: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    _require_superuser(current_user)
    ticket = (
        await db.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
    ).scalar_one_or_none()
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    if status:
        ticket.status = TicketStatus(status)
    if admin_notes:
        ticket.admin_notes = admin_notes
    await db.commit()
    return ticket


@router.get("/health/system", summary="[Admin] System health overview")
async def system_health(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    _require_superuser(current_user)

    try:
        await db.execute(select(sa_func.now()))
        db_ok = True
    except Exception:
        db_ok = False

    try:
        await Cache.set("health:ping", "1", ttl=5)
        redis_ok = True
    except Exception:
        redis_ok = False

    return {
        "database": "ok" if db_ok else "error",
        "redis": "ok" if redis_ok else "error",
        "api": "ok",
        "checked_at": str(date.today()),
    }


@router.post("/tickets", status_code=201, summary="Submit a support ticket")
async def create_ticket(
    subject: str,
    body: str,
    priority: str = "medium",
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    ticket = SupportTicket(
        user_id=current_user.id,
        subject=subject,
        body=body,
        priority=TicketPriority(priority),
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    return ticket
