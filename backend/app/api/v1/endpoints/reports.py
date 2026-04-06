"""Advanced analytics and report endpoints for Phase 2.6B."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import case, func as sa_func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user, get_db
from app.models.lead import Lead
from app.models.user import User

router = APIRouter()

_FUNNEL_STAGES = [
    "NEW",
    "CONTACTED",
    "QUALIFIED",
    "PROPOSAL",
    "NEGOTIATION",
    "WON",
    "LOST",
]
_TIER_MULT = {"HIGH": 3.0, "MEDIUM": 1.5, "LOW": 0.5}


@router.get("/funnel", summary="Lead status funnel")
async def get_funnel(
    days: int = Query(90, ge=7, le=365),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Return a lead-status funnel for the requested time window."""

    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(Lead.status, sa_func.count(Lead.id).label("cnt"))
        .where(Lead.user_id == current_user.id, Lead.created_at >= since)
        .group_by(Lead.status)
    )
    raw_counts = {row.status: int(row.cnt) for row in result}
    stages = [
        {"stage": stage, "count": raw_counts.get(stage, 0), "pct_of_top": 0.0}
        for stage in _FUNNEL_STAGES
    ]
    top_count = stages[0]["count"] or 1
    for stage in stages:
        stage["pct_of_top"] = round(stage["count"] / top_count * 100, 1)

    return {"period_days": days, "stages": stages, "total": sum(raw_counts.values())}


@router.get("/conversion", summary="Stage-to-stage conversion rates")
async def get_conversion_rates(
    days: int = Query(90, ge=7, le=365),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Return stage-to-stage conversion rates across the funnel."""

    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(Lead.status, sa_func.count(Lead.id).label("cnt"))
        .where(Lead.user_id == current_user.id, Lead.created_at >= since)
        .group_by(Lead.status)
    )
    counts = {row.status: int(row.cnt) for row in result}
    transitions = []
    for index in range(len(_FUNNEL_STAGES) - 2):
        from_stage = _FUNNEL_STAGES[index]
        to_stage = _FUNNEL_STAGES[index + 1]
        from_count = counts.get(from_stage, 0)
        to_count = counts.get(to_stage, 0)
        transitions.append(
            {
                "from": from_stage,
                "to": to_stage,
                "from_count": from_count,
                "to_count": to_count,
                "rate_pct": round(to_count / from_count * 100, 1) if from_count else 0.0,
            }
        )

    won = counts.get("WON", 0)
    total = counts.get("NEW", 0) or 1
    return {
        "period_days": days,
        "transitions": transitions,
        "overall_win_rate": round(won / total * 100, 1),
    }


@router.get("/roi", summary="Pipeline ROI estimate")
async def get_roi_estimate(
    avg_deal_value: float = Query(50_000.0, ge=0),
    win_rate_pct: float = Query(15.0, ge=0, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Estimate ROI based on lead tiers and a configurable win rate."""

    result = await db.execute(
        select(Lead.priority_tier, sa_func.count(Lead.id).label("cnt"))
        .where(Lead.user_id == current_user.id)
        .group_by(Lead.priority_tier)
    )
    tier_counts = {row.priority_tier: int(row.cnt) for row in result}
    win_rate = win_rate_pct / 100.0
    breakdown = []
    total_pipeline_value = 0.0

    for tier, multiplier in _TIER_MULT.items():
        lead_count = tier_counts.get(tier, 0)
        expected_value = lead_count * avg_deal_value * multiplier * win_rate
        total_pipeline_value += expected_value
        breakdown.append(
            {
                "tier": tier,
                "lead_count": lead_count,
                "multiplier": multiplier,
                "expected_value": round(expected_value, 2),
            }
        )

    return {
        "avg_deal_value": avg_deal_value,
        "win_rate_pct": win_rate_pct,
        "total_pipeline_value": round(total_pipeline_value, 2),
        "tier_breakdown": breakdown,
        "total_leads": sum(tier_counts.values()),
    }


@router.get("/cohort", summary="Weekly cohort analysis")
async def get_cohort_analysis(
    weeks: int = Query(8, ge=2, le=26),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Return a weekly cohort activation view for recent leads."""

    today = date.today()
    cohorts = []
    for week_offset in range(weeks):
        week_start = today - timedelta(weeks=week_offset + 1)
        week_end = today - timedelta(weeks=week_offset)

        total = int(
            (
                await db.execute(
                    select(sa_func.count(Lead.id)).where(
                        Lead.user_id == current_user.id,
                        Lead.created_at >= week_start,
                        Lead.created_at < week_end,
                    )
                )
            ).scalar()
            or 0
        )
        activated = int(
            (
                await db.execute(
                    select(sa_func.count(Lead.id)).where(
                        Lead.user_id == current_user.id,
                        Lead.created_at >= week_start,
                        Lead.created_at < week_end,
                        Lead.status.in_(
                            ["CONTACTED", "QUALIFIED", "PROPOSAL", "NEGOTIATION", "WON"]
                        ),
                    )
                )
            ).scalar()
            or 0
        )
        cohorts.append(
            {
                "cohort_week": str(week_start),
                "total_leads": total,
                "activated": activated,
                "activation_rate": round(activated / total * 100, 1) if total else 0.0,
            }
        )

    cohorts.reverse()
    return {"weeks": weeks, "cohorts": cohorts}


class CustomReportRequest(BaseModel):
    """Custom report builder request payload."""

    metric: str = Field(
        ...,
        pattern=(
            "^(lead_count|avg_score|high_value_count|contacted_count|won_count|"
            "enriched_count)$"
        ),
    )
    group_by: str = Field("week", pattern="^(day|week|month)$")
    days: int = Field(30, ge=7, le=180)
    filters: Optional[Dict[str, Any]] = None


@router.post("/custom", summary="Custom report builder")
async def custom_report(
    request: CustomReportRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Build a grouped custom report for the selected metric."""

    since = date.today() - timedelta(days=request.days)
    period_col = sa_func.date_trunc(request.group_by, Lead.created_at).label("period")

    metric_map = {
        "lead_count": sa_func.count(Lead.id),
        "avg_score": sa_func.round(sa_func.avg(Lead.propensity_score), 1),
        "high_value_count": sa_func.sum(
            case((Lead.propensity_score >= 70, 1), else_=0)
        ),
        "contacted_count": sa_func.sum(
            case(
                (
                    Lead.status.in_(
                        ["CONTACTED", "QUALIFIED", "PROPOSAL", "NEGOTIATION", "WON"]
                    ),
                    1,
                ),
                else_=0,
            )
        ),
        "won_count": sa_func.sum(case((Lead.status == "WON", 1), else_=0)),
        "enriched_count": sa_func.sum(case((Lead.email.isnot(None), 1), else_=0)),
    }

    query = (
        select(period_col, metric_map[request.metric].label("value"))
        .where(Lead.user_id == current_user.id, Lead.created_at >= since)
        .group_by(period_col)
        .order_by(period_col)
    )
    if request.filters:
        if minimum_score := request.filters.get("min_score"):
            query = query.where(Lead.propensity_score >= minimum_score)
        if status_filter := request.filters.get("status"):
            query = query.where(Lead.status == status_filter)

    result = await db.execute(query)
    return {
        "metric": request.metric,
        "group_by": request.group_by,
        "days": request.days,
        "data": [
            {"period": str(row.period.date()), "value": float(row.value or 0)}
            for row in result
        ],
    }
