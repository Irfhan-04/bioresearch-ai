"""Pydantic schemas for collaboration activities."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ActivityCreate(BaseModel):
    """Payload for creating a note, comment, or reminder."""

    activity_type: str = Field(..., pattern="^(note|comment|reminder)$")
    content: Optional[str] = Field(None, max_length=5000)
    reminder_due_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class AssignRequest(BaseModel):
    """Payload for assigning or unassigning a lead."""

    assignee_user_id: Optional[UUID]


class StatusChangeRequest(BaseModel):
    """Payload for changing a lead's lifecycle status."""

    new_status: str = Field(
        ...,
        pattern="^(NEW|CONTACTED|QUALIFIED|PROPOSAL|NEGOTIATION|WON|LOST)$",
    )


class ActivityResponse(BaseModel):
    """Serialized collaboration activity."""

    id: UUID
    lead_id: UUID
    user_id: Optional[UUID]
    activity_type: str
    content: Optional[str]
    mentioned_user_ids: Optional[List[UUID]]
    metadata: Optional[Dict[str, Any]]
    reminder_due_at: Optional[datetime]
    reminder_done: bool
    created_at: datetime
    author_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
