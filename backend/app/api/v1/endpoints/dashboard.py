"""Dashboard stats endpoint used by the frontend dashboard page."""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func as sa_func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user, get_db
from app.models.researcher import Researcher
from app.models.user import User

router = APIRouter()


@router.get("/stats", summary="Get dashboard summary statistics")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the researcher metrics shown on the main dashboard page."""
    accessible_researchers = Researcher.user_id == current_user.id

    today = date.today()
    month_start = date(today.year, today.month, 1)
    if today.month == 12:
        next_month_start = date(today.year + 1, 1, 1)
    else:
        next_month_start = date(today.year, today.month + 1, 1)

    total_researchers = await db.scalar(
        select(sa_func.count(Researcher.id)).where(accessible_researchers)
    )

    high_relevance_researchers = await db.scalar(
        select(sa_func.count(Researcher.id)).where(
            accessible_researchers,
            Researcher.propensity_score >= 70,
        )
    )

    researchers_this_month = await db.scalar(
        select(sa_func.count(Researcher.id)).where(
            accessible_researchers,
            Researcher.created_at >= month_start,
            Researcher.created_at < next_month_start,
        )
    )

    average_score = await db.scalar(
        select(sa_func.avg(Researcher.propensity_score)).where(
            accessible_researchers,
            Researcher.propensity_score.isnot(None),
        )
    )

    return {
        "total_researchers": int(total_researchers or 0),
        "high_relevance_researchers": int(high_relevance_researchers or 0),
        "researchers_this_month": int(researchers_this_month or 0),
        "average_score": (
            round(float(average_score), 1) if average_score is not None else 0.0
        ),
    }
