"""Pydantic schemas for CRM connections."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CrmConnectionCreate(BaseModel):
    """Payload for creating a CRM connection."""

    provider: str = Field(..., pattern="^(hubspot|pipedrive|salesforce|custom)$")
    name: str = Field(..., min_length=2, max_length=255)
    credentials: Dict[str, str]
    field_map: Dict[str, str] = Field(default_factory=dict)
    sync_direction: str = Field("push", pattern="^(push|pull|both)$")
    auto_sync: bool = False
    sync_filter: Optional[Dict[str, Any]] = None


class CrmConnectionUpdate(BaseModel):
    """Payload for updating a CRM connection."""

    name: Optional[str] = None
    credentials: Optional[Dict[str, str]] = None
    field_map: Optional[Dict[str, str]] = None
    sync_direction: Optional[str] = Field(None, pattern="^(push|pull|both)$")
    auto_sync: Optional[bool] = None
    sync_filter: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class CrmConnectionResponse(BaseModel):
    """Serialized CRM connection response."""

    id: UUID
    provider: str
    name: str
    is_active: bool
    sync_direction: str
    auto_sync: bool
    field_map: Dict[str, str]
    sync_filter: Optional[Dict[str, Any]]
    last_sync_at: Optional[datetime]
    last_sync_status: Optional[str]
    total_synced_leads: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class SyncRequest(BaseModel):
    """Sync request payload."""

    lead_ids: Optional[List[UUID]] = None
    dry_run: bool = False


class CrmSyncLogResponse(BaseModel):
    """Serialized CRM sync log response."""

    id: UUID
    started_at: datetime
    finished_at: Optional[datetime]
    status: str
    leads_pushed: int
    leads_updated: int
    leads_failed: int
    error_detail: Optional[str]

    model_config = ConfigDict(from_attributes=True)
