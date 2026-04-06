"""UsageService — centralized helper to record usage events."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usage import UsageEvent, UsageEventType

logger = logging.getLogger(__name__)


class UsageService:
    @staticmethod
    async def record(
        db: AsyncSession,
        user_id: UUID,
        event_type: UsageEventType,
        quantity: int = 1,
        team_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        try:
            db.add(
                UsageEvent(
                    user_id=user_id,
                    team_id=team_id,
                    event_type=event_type,
                    quantity=quantity,
                    event_metadata=metadata or {},
                )
            )
        except Exception as exc:
            logger.warning("UsageService.record failed: %s", exc)
