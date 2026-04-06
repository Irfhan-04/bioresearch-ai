"""TierQuotaService — per-user monthly subscription quota enforcement."""

from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import HTTPException
from sqlalchemy import func as sa_func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.usage import UsageEvent, UsageEventType
from app.models.user import User

QuotaMetric = Literal["leads", "searches", "exports", "api_calls"]

_METRIC_TO_EVENT = {
    "leads": UsageEventType.LEAD_CREATED,
    "searches": UsageEventType.SEARCH_EXECUTED,
    "exports": UsageEventType.EXPORT_GENERATED,
    "api_calls": UsageEventType.API_CALL,
}


class TierQuotaService:
    @staticmethod
    async def check_and_enforce(
        db: AsyncSession,
        user: User,
        metric: QuotaMetric,
        amount: int = 1,
    ) -> None:
        tier_limits = settings.TIER_LIMITS.get(
            user.subscription_tier, settings.TIER_LIMITS["free"]
        )
        limit = tier_limits[metric]
        if limit >= 999999:
            return

        today = date.today()
        period_start = date(today.year, today.month, 1)

        result = await db.execute(
            select(sa_func.coalesce(sa_func.sum(UsageEvent.quantity), 0)).where(
                UsageEvent.user_id == user.id,
                UsageEvent.event_type == _METRIC_TO_EVENT[metric],
                UsageEvent.occurred_at >= period_start,
            )
        )
        used = int(result.scalar() or 0)

        if used + amount > limit:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "quota_exceeded",
                    "metric": metric,
                    "limit": limit,
                    "used": used,
                    "tier": str(user.subscription_tier),
                    "upgrade": f"{settings.FRONTEND_URL}/billing",
                },
            )

    @staticmethod
    def get_tier_limits(tier: str) -> dict:
        return settings.TIER_LIMITS.get(tier, settings.TIER_LIMITS["free"])
