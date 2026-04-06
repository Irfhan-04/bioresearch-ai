"""Quota Manager — Phase 2.3 Step 5."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Optional

from app.core.cache import Cache
from app.core.config import settings

logger = logging.getLogger(__name__)

_HUNTER_MONTHLY_LIMIT = 25
_CLEARBIT_MONTHLY_LIMIT = 50


class QuotaManager:
    async def can_use_hunter(self, lead_score: int = 0) -> bool:
        if lead_score < settings.HUNTER_MIN_SCORE_FOR_API:
            return False
        if await self._is_exhausted("hunter"):
            return False
        return await self._get_used("hunter") < _HUNTER_MONTHLY_LIMIT

    async def record_hunter_use(self) -> int:
        return await self._increment("hunter")

    async def mark_hunter_exhausted(self) -> None:
        await self._mark_exhausted("hunter")

    async def get_hunter_status(self) -> dict:
        used = await self._get_used("hunter")
        return {
            "used": used,
            "limit": _HUNTER_MONTHLY_LIMIT,
            "remaining": max(0, _HUNTER_MONTHLY_LIMIT - used),
            "exhausted": await self._is_exhausted("hunter"),
            "min_score": settings.HUNTER_MIN_SCORE_FOR_API,
            "reset_date": _next_month_first(),
        }

    async def can_use_clearbit(self, lead_score: int = 0) -> bool:
        if lead_score < settings.CLEARBIT_MIN_SCORE_FOR_API:
            return False
        if await self._is_exhausted("clearbit"):
            return False
        return await self._get_used("clearbit") < _CLEARBIT_MONTHLY_LIMIT

    async def record_clearbit_use(self) -> int:
        return await self._increment("clearbit")

    async def mark_clearbit_exhausted(self) -> None:
        await self._mark_exhausted("clearbit")

    async def get_clearbit_status(self) -> dict:
        used = await self._get_used("clearbit")
        return {
            "used": used,
            "limit": _CLEARBIT_MONTHLY_LIMIT,
            "remaining": max(0, _CLEARBIT_MONTHLY_LIMIT - used),
            "exhausted": await self._is_exhausted("clearbit"),
            "min_score": settings.CLEARBIT_MIN_SCORE_FOR_API,
            "reset_date": _next_month_first(),
        }

    async def get_all_quota_status(self) -> dict:
        return {
            "hunter": await self.get_hunter_status(),
            "clearbit": await self.get_clearbit_status(),
            "month": _current_month_key(),
        }

    async def reset_all_quotas(self) -> None:
        """Delete current-month quota keys so usage starts at zero."""
        today = date.today()
        month_id = f"{today.year}-{today.month:02d}"

        hunter_key = f"quota:hunter:{month_id}"
        clearbit_key = f"quota:clearbit:{month_id}"
        exhaust_keys = [
            f"quota:hunter:exhausted:{month_id}",
            f"quota:clearbit:exhausted:{month_id}",
        ]

        await Cache.delete(hunter_key)
        await Cache.delete(clearbit_key)
        for key in exhaust_keys:
            await Cache.delete(key)

        logger.info("Quota counters reset for %s", month_id)

    @staticmethod
    def _counter_key(service: str) -> str:
        return f"quota:{service}:{_current_month_key()}"

    @staticmethod
    def _exhausted_key(service: str) -> str:
        return f"quota:{service}:exhausted:{_current_month_key()}"

    @staticmethod
    async def _get_used(service: str) -> int:
        value = await Cache.get(QuotaManager._counter_key(service))
        return int(value) if value is not None else 0

    @staticmethod
    async def _increment(service: str) -> int:
        key = QuotaManager._counter_key(service)
        new_val = await Cache.increment(key)
        await Cache.expire(key, _seconds_until_month_end())
        return new_val

    @staticmethod
    async def _is_exhausted(service: str) -> bool:
        return await Cache.exists(QuotaManager._exhausted_key(service))

    @staticmethod
    async def _mark_exhausted(service: str) -> None:
        await Cache.set(QuotaManager._exhausted_key(service), "1", ttl=_seconds_until_month_end())
        logger.warning("%s quota exhausted", service)


def _current_month_key() -> str:
    now = datetime.now(timezone.utc)
    return f"{now.year}-{now.month:02d}"


def _seconds_until_month_end() -> int:
    now = datetime.now(timezone.utc)
    year = now.year + (1 if now.month == 12 else 0)
    month = 1 if now.month == 12 else now.month + 1
    first_next = datetime(year, month, 1, tzinfo=timezone.utc)
    return max(int((first_next - now).total_seconds()), 3600)


def _next_month_first() -> str:
    now = datetime.now(timezone.utc)
    year = now.year + (1 if now.month == 12 else 0)
    month = 1 if now.month == 12 else now.month + 1
    return f"{year}-{month:02d}-01"


_quota_manager: Optional[QuotaManager] = None


def get_quota_manager() -> QuotaManager:
    global _quota_manager
    if _quota_manager is None:
        _quota_manager = QuotaManager()
    return _quota_manager


__all__ = ["QuotaManager", "get_quota_manager"]
