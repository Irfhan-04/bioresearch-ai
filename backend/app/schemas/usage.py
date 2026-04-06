from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel


class UsageEventOut(BaseModel):
    id: UUID
    event_type: str
    quantity: int
    metadata: Optional[Dict[str, Any]]
    occurred_at: datetime

    class Config:
        from_attributes = True


class UsageSummary(BaseModel):
    period_start: str
    period_end: str
    leads_created: int = 0
    leads_enriched: int = 0
    searches_run: int = 0
    exports_made: int = 0
    api_calls_total: int = 0
    pipeline_runs: int = 0
    tier: str
    leads_limit: int
    leads_remaining: int
    quota_pct_used: float


class AdminUserSummary(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str]
    tier: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    leads_30d: int = 0
    last_login_at: Optional[datetime]

    class Config:
        from_attributes = True
