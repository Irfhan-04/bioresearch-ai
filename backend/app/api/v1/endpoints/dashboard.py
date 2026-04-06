"""Dashboard stats endpoint used by the frontend dashboard page."""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func as sa_func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user, get_db
from app.models.lead import Lead
from app.models.team import TeamMembership
from app.models.user import User

router = APIRouter()


@router.get("/stats", summary="Get dashboard summary statistics")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the lead metrics shown on the main dashboard page."""
    team_ids_subq = (
        select(TeamMembership.team_id)
        .where(TeamMembership.user_id == current_user.id)
        .scalar_subquery()
    )

    accessible_leads = or_(
        Lead.user_id == current_user.id,
        Lead.team_id.in_(team_ids_subq),
    )

    today = date.today()
    month_start = date(today.year, today.month, 1)
    if today.month == 12:
        next_month_start = date(today.year + 1, 1, 1)
    else:
        next_month_start = date(today.year, today.month + 1, 1)

    total_leads = await db.scalar(
        select(sa_func.count(Lead.id)).where(accessible_leads)
    )

    high_priority_leads = await db.scalar(
        select(sa_func.count(Lead.id)).where(
            accessible_leads,
            Lead.propensity_score >= 70,
        )
    )

    leads_this_month = await db.scalar(
        select(sa_func.count(Lead.id)).where(
            accessible_leads,
            Lead.created_at >= month_start,
            Lead.created_at < next_month_start,
        )
    )

    average_score = await db.scalar(
        select(sa_func.avg(Lead.propensity_score)).where(
            accessible_leads,
            Lead.propensity_score.isnot(None),
        )
    )

    return {
        "total_leads": int(total_leads or 0),
        "high_priority_leads": int(high_priority_leads or 0),
        "leads_this_month": int(leads_this_month or 0),
        "average_score": (
            round(float(average_score), 1) if average_score is not None else 0.0
        ),
    }
