"""Pydantic schemas for alert rules."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class AlertRuleCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    trigger: str = Field(..., pattern="^(high_value_lead|new_nih_grant|conference_match|score_increase)$")
    channel: str = Field("email", pattern="^(email|webhook|both)$")
    conditions: Dict[str, Any] = Field(default_factory=dict)
    throttle_seconds: int = Field(3600, ge=60, le=86400)


class AlertRuleUpdate(BaseModel):
    name: Optional[str] = None
    channel: Optional[str] = Field(None, pattern="^(email|webhook|both)$")
    conditions: Optional[Dict[str, Any]] = None
    throttle_seconds: Optional[int] = Field(None, ge=60, le=86400)
    is_active: Optional[bool] = None


class AlertRuleResponse(BaseModel):
    id: UUID
    name: str
    trigger: str
    channel: str
    is_active: bool
    conditions: Dict[str, Any]
    throttle_seconds: int
    last_triggered_at: Optional[datetime]
    trigger_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
