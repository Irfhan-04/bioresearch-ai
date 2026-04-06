"""Collaboration API endpoints for Phase 2.6B."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user, get_db
from app.models.activity import ActivityType, LeadActivity
from app.models.lead import Lead
from app.models.team import TeamMembership
from app.models.user import User
from app.schemas.activity import (
    ActivityCreate,
    ActivityResponse,
    AssignRequest,
    StatusChangeRequest,
)
from app.schemas.base import MessageResponse

router = APIRouter()

_MENTION_RE = re.compile(
    r"@([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
    re.IGNORECASE,
)


async def _get_lead(lead_id: UUID, user: User, db: AsyncSession) -> Lead:
    """Return a lead the user owns or can access through a team membership."""

    result = await db.execute(
        select(Lead).where(Lead.id == lead_id, Lead.user_id == user.id)
    )
    lead = result.scalar_one_or_none()
    if not lead:
        team_result = await db.execute(
            select(Lead)
            .join(TeamMembership, TeamMembership.team_id == Lead.team_id)
            .where(Lead.id == lead_id, TeamMembership.user_id == user.id)
        )
        lead = team_result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


def _serialize_activity(activity: LeadActivity, author_name: Optional[str] = None) -> ActivityResponse:
    """Convert a LeadActivity model into an API response."""

    return ActivityResponse(
        id=activity.id,
        lead_id=activity.lead_id,
        user_id=activity.user_id,
        activity_type=(
            activity.activity_type.value
            if isinstance(activity.activity_type, ActivityType)
            else str(activity.activity_type)
        ),
        content=activity.content,
        mentioned_user_ids=activity.mentioned_user_ids,
        metadata=activity.activity_metadata,
        reminder_due_at=activity.reminder_due_at,
        reminder_done=activity.reminder_done,
        created_at=activity.created_at,
        author_name=author_name,
    )


@router.get("/leads/{lead_id}/activities", response_model=List[ActivityResponse])
async def get_activities(
    lead_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    activity_type: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the collaboration feed for a lead."""

    await _get_lead(lead_id, current_user, db)
    query = (
        select(LeadActivity)
        .where(LeadActivity.lead_id == lead_id)
        .order_by(LeadActivity.created_at.desc())
        .limit(limit)
    )
    if activity_type:
        query = query.where(LeadActivity.activity_type == ActivityType(activity_type))

    result = await db.execute(query)
    activities = result.scalars().all()

    serialized = []
    for activity in activities:
        author_name = None
        if activity.user_id:
            user_result = await db.execute(select(User).where(User.id == activity.user_id))
            author = user_result.scalar_one_or_none()
            if author:
                author_name = author.full_name or author.email
        serialized.append(_serialize_activity(activity, author_name=author_name))
    return serialized


@router.post(
    "/leads/{lead_id}/activities",
    response_model=ActivityResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_activity(
    lead_id: UUID,
    payload: ActivityCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a note, comment, or reminder to a lead."""

    await _get_lead(lead_id, current_user, db)
    if payload.activity_type == "reminder" and not payload.reminder_due_at:
        raise HTTPException(status_code=400, detail="reminder_due_at is required for reminders")

    mentions = [UUID(match) for match in _MENTION_RE.findall(payload.content or "")]
    activity = LeadActivity(
        lead_id=lead_id,
        user_id=current_user.id,
        activity_type=ActivityType(payload.activity_type),
        content=payload.content,
        mentioned_user_ids=mentions or None,
        activity_metadata=payload.metadata,
        reminder_due_at=payload.reminder_due_at,
    )
    db.add(activity)
    await db.commit()
    await db.refresh(activity)
    return _serialize_activity(activity, author_name=current_user.full_name or current_user.email)


@router.post("/leads/{lead_id}/assign", response_model=MessageResponse)
async def assign_lead(
    lead_id: UUID,
    payload: AssignRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Assign or unassign a lead and record the activity."""

    lead = await _get_lead(lead_id, current_user, db)
    old_assignee = lead.assigned_to
    lead.assigned_to = payload.assignee_user_id

    assignee_name = None
    if payload.assignee_user_id:
        assignee_result = await db.execute(
            select(User).where(User.id == payload.assignee_user_id)
        )
        assignee = assignee_result.scalar_one_or_none()
        assignee_name = (
            assignee.full_name or assignee.email if assignee else str(payload.assignee_user_id)
        )

    db.add(
        LeadActivity(
            lead_id=lead_id,
            user_id=current_user.id,
            activity_type=ActivityType.ASSIGNMENT,
            content=f"Assigned to {assignee_name}" if assignee_name else "Unassigned",
            activity_metadata={
                "from": str(old_assignee) if old_assignee else None,
                "to": str(payload.assignee_user_id) if payload.assignee_user_id else None,
            },
        )
    )
    db.add(lead)
    await db.commit()
    return MessageResponse(
        message=f"Lead assigned to {assignee_name}" if assignee_name else "Lead unassigned"
    )


@router.post("/leads/{lead_id}/status", response_model=MessageResponse)
async def change_status(
    lead_id: UUID,
    payload: StatusChangeRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Change a lead status and append a collaboration activity."""

    lead = await _get_lead(lead_id, current_user, db)
    old_status = lead.status
    lead.status = payload.new_status
    if payload.new_status == "CONTACTED" and not lead.last_contacted_at:
        lead.last_contacted_at = datetime.now(timezone.utc)

    db.add(
        LeadActivity(
            lead_id=lead_id,
            user_id=current_user.id,
            activity_type=ActivityType.STATUS_CHANGE,
            content=f"Status changed from {old_status} to {payload.new_status}",
            activity_metadata={"from": old_status, "to": payload.new_status},
        )
    )
    db.add(lead)
    await db.commit()
    return MessageResponse(message=f"Status updated to {payload.new_status}")


@router.get("/reminders", response_model=List[ActivityResponse])
async def list_reminders(
    due_within_days: int = Query(7, ge=1, le=90),
    include_done: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List upcoming reminders visible to the current user."""

    now = datetime.now(timezone.utc)
    deadline = now + timedelta(days=due_within_days)
    membership_team_ids = (
        select(TeamMembership.team_id)
        .where(TeamMembership.user_id == current_user.id)
        .scalar_subquery()
    )
    query = (
        select(LeadActivity)
        .join(Lead, Lead.id == LeadActivity.lead_id)
        .where(
            or_(Lead.user_id == current_user.id, Lead.team_id.in_(membership_team_ids)),
            LeadActivity.activity_type == ActivityType.REMINDER,
            LeadActivity.reminder_due_at <= deadline,
            LeadActivity.reminder_due_at >= now,
        )
        .order_by(LeadActivity.reminder_due_at)
    )
    if not include_done:
        query = query.where(LeadActivity.reminder_done.is_(False))

    result = await db.execute(query)
    activities = result.scalars().all()
    return [_serialize_activity(activity) for activity in activities]


@router.post("/reminders/{activity_id}/done", response_model=MessageResponse)
async def complete_reminder(
    activity_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a reminder complete if it belongs to a visible lead."""

    membership_team_ids = (
        select(TeamMembership.team_id)
        .where(TeamMembership.user_id == current_user.id)
        .scalar_subquery()
    )
    result = await db.execute(
        select(LeadActivity)
        .join(Lead, Lead.id == LeadActivity.lead_id)
        .where(
            LeadActivity.id == activity_id,
            LeadActivity.activity_type == ActivityType.REMINDER,
            or_(Lead.user_id == current_user.id, Lead.team_id.in_(membership_team_ids)),
        )
    )
    activity = result.scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=404, detail="Reminder not found")

    activity.reminder_done = True
    db.add(activity)
    await db.commit()
    return MessageResponse(message="Reminder marked as complete")
