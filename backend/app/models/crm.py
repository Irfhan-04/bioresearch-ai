"""CRM connection and sync log models."""

import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class CrmProvider(str, enum.Enum):
    """Supported CRM providers."""

    HUBSPOT = "hubspot"
    PIPEDRIVE = "pipedrive"
    SALESFORCE = "salesforce"
    CUSTOM = "custom"


class SyncDirection(str, enum.Enum):
    """Supported sync directions."""

    PUSH = "push"
    PULL = "pull"
    BOTH = "both"


class CrmConnection(Base):
    """Stores a user's CRM integration with encrypted credentials."""

    __tablename__ = "crm_connections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider = Column(SQLEnum(CrmProvider), nullable=False)
    name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    credentials_encrypted = Column(Text, nullable=False)
    field_map = Column(JSONB, nullable=False, default=dict)
    sync_direction = Column(
        SQLEnum(SyncDirection), default=SyncDirection.PUSH, nullable=False
    )
    auto_sync = Column(Boolean, default=False, nullable=False)
    sync_filter = Column(JSONB, nullable=True)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    last_sync_status = Column(String(50), nullable=True)
    total_synced_leads = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User")
    sync_logs = relationship(
        "CrmSyncLog", back_populates="connection", cascade="all, delete-orphan"
    )


class CrmSyncLog(Base):
    """Immutable audit record for each CRM sync operation."""

    __tablename__ = "crm_sync_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("crm_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), nullable=False)
    leads_pushed = Column(Integer, default=0)
    leads_updated = Column(Integer, default=0)
    leads_failed = Column(Integer, default=0)
    error_detail = Column(Text, nullable=True)

    connection = relationship("CrmConnection", back_populates="sync_logs")
