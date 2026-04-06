"""Team management endpoints — create, invite, and member management."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import List
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_active_user, get_db
from app.models.team import InviteStatus, Team, TeamInvitation, TeamMembership, TeamRole
from app.models.user import User
from app.schemas.base import MessageResponse
from app.schemas.team import (
    TransferOwnershipRequest,
    InviteCreate,
    InviteResponse,
    MemberResponse,
    RoleUpdate,
    TeamCreate,
    TeamResponse,
    TeamUpdate,
)
from app.services.email_service import EmailService

router = APIRouter()
_email_svc = EmailService()


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60]


async def _require_team_admin(team_id: UUID, current_user: User, db: AsyncSession) -> Team:
    team = (await db.execute(select(Team).where(Team.id == team_id))).scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    if team.owner_id == current_user.id:
        return team

    membership = (
        await db.execute(
            select(TeamMembership).where(
                TeamMembership.team_id == team_id,
                TeamMembership.user_id == current_user.id,
                TeamMembership.role.in_([TeamRole.ADMIN, TeamRole.OWNER]),
            )
        )
    ).scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=403, detail="Team admin access required")
    return team


@router.post("/", response_model=TeamResponse, status_code=201)
async def create_team(
    payload: TeamCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    slug = _slugify(payload.name)
    existing = (await db.execute(select(Team).where(Team.slug == slug))).scalar_one_or_none()
    if existing:
        slug = f"{slug}-{str(current_user.id).replace('-', '')[:6]}"

    team = Team(
        name=payload.name,
        slug=slug,
        owner_id=current_user.id,
        description=payload.description,
    )
    db.add(team)
    await db.flush()

    db.add(TeamMembership(team_id=team.id, user_id=current_user.id, role=TeamRole.OWNER))
    await db.commit()
    await db.refresh(team)

    return TeamResponse(
        **{
            k: getattr(team, k)
            for k in ("id", "name", "slug", "owner_id", "description", "avatar_url", "created_at")
        },
        member_count=1,
    )


@router.get("/", response_model=List[TeamResponse])
async def list_my_teams(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Team)
        .join(TeamMembership, TeamMembership.team_id == Team.id)
        .where(TeamMembership.user_id == current_user.id)
        .order_by(Team.created_at.desc())
    )
    teams = result.scalars().all()
    return [
        TeamResponse(
            **{
                k: getattr(team, k)
                for k in ("id", "name", "slug", "owner_id", "description", "avatar_url", "created_at")
            },
            member_count=len(team.memberships),
        )
        for team in teams
    ]


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    team = (await db.execute(select(Team).where(Team.id == team_id))).scalar_one_or_none()
    if not team:
        raise HTTPException(404, "Team not found")
    return TeamResponse(
        **{
            k: getattr(team, k)
            for k in ("id", "name", "slug", "owner_id", "description", "avatar_url", "created_at")
        },
        member_count=len(team.memberships),
    )


@router.put("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: UUID,
    payload: TeamUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    team = await _require_team_admin(team_id, current_user, db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(team, field, value)
    await db.commit()
    await db.refresh(team)
    return TeamResponse(
        **{
            k: getattr(team, k)
            for k in ("id", "name", "slug", "owner_id", "description", "avatar_url", "created_at")
        },
        member_count=len(team.memberships),
    )


@router.delete("/{team_id}", status_code=204)
async def delete_team(
    team_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    team = (await db.execute(select(Team).where(Team.id == team_id))).scalar_one_or_none()
    if not team:
        raise HTTPException(404, "Team not found")
    if team.owner_id != current_user.id:
        raise HTTPException(403, "Only the team owner can delete the team")
    await db.delete(team)
    await db.commit()


@router.get("/{team_id}/members", response_model=List[MemberResponse])
async def list_members(
    team_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_team_admin(team_id, current_user, db)
    result = await db.execute(
        select(TeamMembership, User)
        .join(User, User.id == TeamMembership.user_id)
        .where(TeamMembership.team_id == team_id)
    )
    return [
        MemberResponse(
            user_id=ms.user_id,
            email=user.email,
            full_name=user.full_name,
            role=ms.role.value,
            joined_at=ms.joined_at,
        )
        for ms, user in result
    ]


@router.patch("/{team_id}/members/{user_id}/role", response_model=MessageResponse)
async def update_member_role(
    team_id: UUID,
    user_id: UUID,
    payload: RoleUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_team_admin(team_id, current_user, db)
    membership = (
        await db.execute(
            select(TeamMembership).where(
                TeamMembership.team_id == team_id,
                TeamMembership.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if not membership:
        raise HTTPException(404, "Member not found")
    membership.role = TeamRole(payload.role)
    await db.commit()
    return {"message": f"Role updated to {payload.role}"}


@router.delete("/{team_id}/members/{user_id}", status_code=204)
async def remove_member(
    team_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_team_admin(team_id, current_user, db)
    await db.execute(
        delete(TeamMembership).where(
            TeamMembership.team_id == team_id,
            TeamMembership.user_id == user_id,
        )
    )
    await db.commit()


@router.post(
    "/{team_id}/transfer-ownership",
    response_model=MessageResponse,
    summary="Transfer team ownership",
    description=(
        "Transfer ownership to another team member. "
        "Only the current owner can perform this action. "
        "The previous owner's role becomes ADMIN."
    ),
)
async def transfer_ownership(
    team_id: UUID,
    payload: TransferOwnershipRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Transfer team ownership to another existing member.

    Rules:
    - Only the current owner (Team.owner_id) can call this.
    - The new owner must already be a member of the team.
    - The new owner's role is set to OWNER.
    - The previous owner's role is downgraded to ADMIN.
    - Team.owner_id is updated atomically.
    """
    # Fetch the team
    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(404, "Team not found")

    # Only the owner can transfer ownership
    if team.owner_id != current_user.id:
        raise HTTPException(403, "Only the team owner can transfer ownership")

    # Prevent transferring to yourself
    if payload.new_owner_user_id == current_user.id:
        raise HTTPException(400, "You are already the owner")

    # New owner must already be a member
    new_owner_membership_result = await db.execute(
        select(TeamMembership).where(
            TeamMembership.team_id == team_id,
            TeamMembership.user_id == payload.new_owner_user_id,
        )
    )
    new_owner_membership = new_owner_membership_result.scalar_one_or_none()
    if not new_owner_membership:
        raise HTTPException(400, "New owner must already be a member of this team")

    # Downgrade current owner's membership role to ADMIN
    current_owner_membership_result = await db.execute(
        select(TeamMembership).where(
            TeamMembership.team_id == team_id,
            TeamMembership.user_id == current_user.id,
        )
    )
    current_owner_membership = current_owner_membership_result.scalar_one_or_none()
    if current_owner_membership:
        current_owner_membership.role = TeamRole.ADMIN

    # Promote new owner
    new_owner_membership.role = TeamRole.OWNER

    # Update the canonical owner_id on the Team record
    team.owner_id = payload.new_owner_user_id

    await db.commit()

    return MessageResponse(
        message=f"Ownership transferred successfully to user {payload.new_owner_user_id}"
    )


@router.post("/{team_id}/invitations", response_model=InviteResponse, status_code=201)
async def invite_member(
    team_id: UUID,
    payload: InviteCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    team = await _require_team_admin(team_id, current_user, db)
    invite = TeamInvitation(
        team_id=team_id,
        invited_by=current_user.id,
        email=payload.email,
        role=TeamRole(payload.role),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)

    invite_url = f"{settings.FRONTEND_URL}/teams/invite/{invite.token}"
    background_tasks.add_task(
        _email_svc.send_team_invitation,
        to_email=payload.email,
        team_name=team.name,
        inviter=current_user.full_name or current_user.email,
        invite_url=invite_url,
    )
    return invite


@router.get("/invitations/accept/{token}", response_model=MessageResponse)
async def accept_invitation(
    token: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    invite = (
        await db.execute(select(TeamInvitation).where(TeamInvitation.token == token))
    ).scalar_one_or_none()

    if not invite:
        raise HTTPException(404, "Invitation not found")
    if invite.status != InviteStatus.PENDING:
        raise HTTPException(400, f"Invitation is {invite.status.value}")
    if invite.expires_at < datetime.now(timezone.utc):
        invite.status = InviteStatus.EXPIRED
        await db.commit()
        raise HTTPException(400, "Invitation has expired")
    if invite.email != current_user.email:
        raise HTTPException(403, "This invitation was sent to a different email address")

    db.add(TeamMembership(team_id=invite.team_id, user_id=current_user.id, role=invite.role))
    invite.status = InviteStatus.ACCEPTED
    await db.commit()
    return {"message": "You have joined the team successfully"}
