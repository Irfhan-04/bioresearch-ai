"""Usage analytics endpoints — per-user and admin reporting."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func as sa_func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user, get_db
from app.models.usage import UsageEvent, UsageEventType
from app.models.user import User

router = APIRouter()


# ============================================================================
# PER-USER ANALYTICS
# ============================================================================


@router.get("/me/daily", summary="Daily activity for the last N days")
async def get_daily_activity(
    days: int = Query(30, ge=1, le=90),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Daily breakdown of all event types for the last N days.
    Returns one row per (date, event_type) combination.
    """
    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(
            sa_func.date_trunc("day", UsageEvent.occurred_at).label("day"),
            UsageEvent.event_type,
            sa_func.sum(UsageEvent.quantity).label("count"),
        )
        .where(UsageEvent.user_id == current_user.id, UsageEvent.occurred_at >= since)
        .group_by("day", UsageEvent.event_type)
        .order_by("day")
    )
    return [
        {
            "date": str(row.day.date()),
            "event_type": row.event_type,
            "count": int(row.count),
        }
        for row in result
    ]


@router.get("/me/top-sources", summary="Top data sources used in lead creation")
async def get_top_sources(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Ranks data sources (pubmed, conference, funding…) by how many
    LEAD_CREATED events each generated this month.
    """
    result = await db.execute(
        select(
            UsageEvent.event_metadata["source"].astext.label("source"),
            sa_func.sum(UsageEvent.quantity).label("count"),
        )
        .where(
            UsageEvent.user_id == current_user.id,
            UsageEvent.event_type == UsageEventType.LEAD_CREATED,
        )
        .group_by("source")
        .order_by(sa_func.sum(UsageEvent.quantity).desc())
        .limit(10)
    )
    return [{"source": row.source or "unknown", "count": int(row.count)} for row in result]


@router.get("/me/exports", summary="Export frequency — last N days")
async def get_export_frequency(
    days: int = Query(30, ge=1, le=90),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    How often the user runs exports and how many records each export contains.

    Returns:
    - total_exports: count of export events in the period
    - total_records_exported: sum of quantity across all export events
    - daily: per-day export counts for charting
    """
    since = date.today() - timedelta(days=days)

    # Summary totals
    totals_result = await db.execute(
        select(
            sa_func.count(UsageEvent.id).label("total_exports"),
            sa_func.coalesce(sa_func.sum(UsageEvent.quantity), 0).label("total_records"),
        ).where(
            UsageEvent.user_id == current_user.id,
            UsageEvent.event_type == UsageEventType.EXPORT_GENERATED,
            UsageEvent.occurred_at >= since,
        )
    )
    totals = totals_result.first()

    # Daily breakdown
    daily_result = await db.execute(
        select(
            sa_func.date_trunc("day", UsageEvent.occurred_at).label("day"),
            sa_func.count(UsageEvent.id).label("exports"),
            sa_func.coalesce(sa_func.sum(UsageEvent.quantity), 0).label("records"),
        )
        .where(
            UsageEvent.user_id == current_user.id,
            UsageEvent.event_type == UsageEventType.EXPORT_GENERATED,
            UsageEvent.occurred_at >= since,
        )
        .group_by("day")
        .order_by("day")
    )

    return {
        "period_days":          days,
        "total_exports":        int(totals.total_exports or 0),
        "total_records_exported": int(totals.total_records or 0),
        "daily": [
            {
                "date":    str(row.day.date()),
                "exports": int(row.exports),
                "records": int(row.records),
            }
            for row in daily_result
        ],
    }


@router.get("/me/engagement", summary="User engagement summary — WAU and streaks")
async def get_engagement_summary(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Engagement metrics for the current user.

    Returns:
    - active_days_last_7:  days with ≥ 1 event in the last 7 days  (WAU proxy)
    - active_days_last_30: days with ≥ 1 event in the last 30 days (MAU proxy)
    - current_streak_days: consecutive days of activity ending today
    - longest_streak_days: longest consecutive activity streak in last 90 days
    - total_events_30d:    total event count in the last 30 days
    """
    today = date.today()

    # Days with any activity in last 7 and 30 days
    active_days_result = await db.execute(
        select(
            sa_func.date_trunc("day", UsageEvent.occurred_at).label("day"),
        )
        .where(
            UsageEvent.user_id == current_user.id,
            UsageEvent.occurred_at >= today - timedelta(days=90),
        )
        .group_by("day")
        .order_by("day")
    )
    active_day_dates = {row.day.date() for row in active_days_result}

    active_days_7 = sum(1 for d in active_day_dates if d >= today - timedelta(days=6))
    active_days_30 = sum(1 for d in active_day_dates if d >= today - timedelta(days=29))

    # Streak computation (consecutive days ending today)
    streak = 0
    cursor = today
    while cursor in active_day_dates:
        streak += 1
        cursor -= timedelta(days=1)

    longest = 0
    run = 0
    previous_day = None
    for activity_day in sorted(active_day_dates):
        if previous_day and activity_day == previous_day + timedelta(days=1):
            run += 1
        else:
            run = 1
        previous_day = activity_day
        longest = max(longest, run)

    # Total events last 30 days
    total_result = await db.execute(
        select(sa_func.coalesce(sa_func.sum(UsageEvent.quantity), 0)).where(
            UsageEvent.user_id == current_user.id,
            UsageEvent.occurred_at >= today - timedelta(days=30),
        )
    )
    total_events = int(total_result.scalar() or 0)

    return {
        "active_days_last_7":  active_days_7,
        "active_days_last_30": active_days_30,
        "current_streak_days": streak,
        "longest_streak_days": longest,
        "total_events_30d":    total_events,
    }


# ============================================================================
# ADMIN ANALYTICS
# ============================================================================


@router.get("/admin/overview", summary="[Admin] Platform-wide usage overview")
async def admin_overview(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """High-level platform dashboard: user counts, lead volumes, tier breakdown."""
    if not current_user.is_superuser:
        raise HTTPException(403)

    today       = date.today()
    month_start = date(today.year, today.month, 1)
    week_start  = today - timedelta(days=7)

    total_users = (await db.execute(select(sa_func.count(User.id)))).scalar()

    active_today = (
        await db.execute(
            select(sa_func.count(sa_func.distinct(UsageEvent.user_id))).where(
                UsageEvent.occurred_at >= today
            )
        )
    ).scalar()

    active_week = (
        await db.execute(
            select(sa_func.count(sa_func.distinct(UsageEvent.user_id))).where(
                UsageEvent.occurred_at >= week_start
            )
        )
    ).scalar()

    leads_month = (
        await db.execute(
            select(sa_func.sum(UsageEvent.quantity)).where(
                UsageEvent.event_type == UsageEventType.LEAD_CREATED,
                UsageEvent.occurred_at >= month_start,
            )
        )
    ).scalar() or 0

    tier_counts_result = await db.execute(
        select(User.subscription_tier, sa_func.count(User.id)).group_by(
            User.subscription_tier
        )
    )

    return {
        "total_users":    int(total_users or 0),
        "active_today":   int(active_today or 0),    # DAU
        "active_week":    int(active_week or 0),     # WAU
        "leads_month":    int(leads_month),
        "tier_breakdown": {str(row[0]): row[1] for row in tier_counts_result},
        "generated_at":   str(today),
    }


@router.get("/admin/detailed", summary="[Admin] Detailed breakdown of all event types")
async def admin_detailed_usage(
    days: int = Query(30, ge=1, le=90),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Full breakdown of every UsageEventType across the platform.

    Covers all 6 types:
      lead_created, lead_enriched, search_executed,
      export_generated, api_call, pipeline_run

    Returns per-event-type totals + daily series for charting.
    This endpoint satisfies the admin 'usage reports' requirement
    from the Phase 2.4 roadmap (Day 52-54).
    """
    if not current_user.is_superuser:
        raise HTTPException(403)

    since = date.today() - timedelta(days=days)

    # Platform-wide totals per event type
    totals_result = await db.execute(
        select(
            UsageEvent.event_type,
            sa_func.count(sa_func.distinct(UsageEvent.user_id)).label("unique_users"),
            sa_func.sum(UsageEvent.quantity).label("total_quantity"),
        )
        .where(UsageEvent.occurred_at >= since)
        .group_by(UsageEvent.event_type)
        .order_by(sa_func.sum(UsageEvent.quantity).desc())
    )

    event_totals = [
        {
            "event_type":   str(row.event_type),
            "unique_users": int(row.unique_users),
            "total":        int(row.total_quantity or 0),
        }
        for row in totals_result
    ]

    # Daily series — all event types grouped by day
    daily_result = await db.execute(
        select(
            sa_func.date_trunc("day", UsageEvent.occurred_at).label("day"),
            UsageEvent.event_type,
            sa_func.sum(UsageEvent.quantity).label("count"),
        )
        .where(UsageEvent.occurred_at >= since)
        .group_by("day", UsageEvent.event_type)
        .order_by("day")
    )

    daily_series = [
        {
            "date":       str(row.day.date()),
            "event_type": str(row.event_type),
            "count":      int(row.count),
        }
        for row in daily_result
    ]

    # Source breakdown — which data sources generated the most leads
    source_result = await db.execute(
        select(
            UsageEvent.event_metadata["source"].astext.label("source"),
            sa_func.sum(UsageEvent.quantity).label("count"),
        )
        .where(
            UsageEvent.event_type == UsageEventType.LEAD_CREATED,
            UsageEvent.occurred_at >= since,
        )
        .group_by("source")
        .order_by(sa_func.sum(UsageEvent.quantity).desc())
        .limit(10)
    )

    source_breakdown = [
        {"source": row.source or "unknown", "count": int(row.count)}
        for row in source_result
    ]

    return {
        "period_days":     days,
        "event_totals":    event_totals,
        "daily_series":    daily_series,
        "source_breakdown": source_breakdown,
        "generated_at":    str(date.today()),
    }


@router.get("/revenue/summary")
async def get_revenue_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Returns MRR and subscriber counts by tier.
    Admin only — other users get a 403.
    """
    from app.models.user import SubscriptionTier

    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin only")

    result = await db.execute(
        select(
            User.subscription_tier,
            sa_func.count(User.id).label("count"),
        )
        .where(User.stripe_subscription_status == "active")
        .group_by(User.subscription_tier)
    )
    tier_counts = {row.subscription_tier: row.count for row in result}

    pro_count = tier_counts.get(SubscriptionTier.PRO, 0)
    team_count = tier_counts.get(SubscriptionTier.TEAM, 0)
    enterprise_count = tier_counts.get(SubscriptionTier.ENTERPRISE, 0)
    mrr = (pro_count * 49) + (team_count * 199) + (enterprise_count * 2000)

    return {
        "mrr": mrr,
        "arr": mrr * 12,
        "subscribers": {
            "pro": pro_count,
            "team": team_count,
            "enterprise": enterprise_count,
            "total": pro_count + team_count + enterprise_count,
        },
    }
