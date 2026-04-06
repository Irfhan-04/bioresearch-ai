"""Team, TeamMembership, and TeamInvitation SQLAlchemy models."""

import enum
import secrets
import uuid

from sqlalchemy import Column, DateTime, Enum as SQLEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class TeamRole(str, enum.Enum):
    OWNER  = "owner"    # Implicit — set on Team.owner_id; only one per team
    ADMIN  = "admin"    # Can invite, change roles, update team settings
    MEMBER = "member"   # Can view + create leads under team
    VIEWER = "viewer"   # Read-only access to team leads


class InviteStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"


class Team(Base):
    __tablename__ = "teams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(120), nullable=False)
    slug = Column(String(80), nullable=False, unique=True, index=True)
    owner_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    description = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    settings = Column(JSONB, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner = relationship("User", foreign_keys=[owner_id])
    memberships = relationship(
        "TeamMembership", back_populates="team", cascade="all, delete-orphan"
    )
    invitations = relationship(
        "TeamInvitation", back_populates="team", cascade="all, delete-orphan"
    )
    leads = relationship("Lead", back_populates="team")


class TeamMembership(Base):
    __tablename__ = "team_memberships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role = Column(SQLEnum(TeamRole), default=TeamRole.MEMBER, nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    team = relationship("Team", back_populates="memberships")
    user = relationship("User", back_populates="team_memberships")


class TeamInvitation(Base):
    __tablename__ = "team_invitations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    invited_by = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    email = Column(String(255), nullable=False, index=True)
    role = Column(SQLEnum(TeamRole), default=TeamRole.MEMBER, nullable=False)
    token = Column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        default=lambda: secrets.token_urlsafe(32),
    )
    status = Column(SQLEnum(InviteStatus), default=InviteStatus.PENDING, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    team = relationship("Team", back_populates="invitations")
    inviter = relationship("User", foreign_keys=[invited_by])
