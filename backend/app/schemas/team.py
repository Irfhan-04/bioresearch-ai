"""Pydantic schemas for Team, Membership, and Invitation."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class TeamCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


class TeamUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    settings: Optional[dict] = None


class TeamResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    owner_id: UUID
    description: Optional[str]
    avatar_url: Optional[str]
    member_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class MemberResponse(BaseModel):
    user_id: UUID
    email: str
    full_name: Optional[str]
    role: str           # "owner" | "admin" | "member" | "viewer"
    joined_at: datetime

    class Config:
        from_attributes = True


class RoleUpdate(BaseModel):
    # "owner" excluded — use the dedicated transfer-ownership endpoint
    role: str = Field(..., pattern="^(admin|member|viewer)$")


class InviteCreate(BaseModel):
    email: EmailStr
    role: str = Field("member", pattern="^(admin|member|viewer)$")


class InviteResponse(BaseModel):
    id: UUID
    team_id: UUID
    email: str
    role: str
    token: str
    status: str
    expires_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class TransferOwnershipRequest(BaseModel):
    """Body for POST /teams/{id}/transfer-ownership."""
    new_owner_user_id: UUID