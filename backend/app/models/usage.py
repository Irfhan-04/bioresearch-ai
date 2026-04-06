"""UsageEvent — append-only audit/analytics log."""

import enum
import uuid

from sqlalchemy import Column, DateTime, Enum as SQLEnum, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class UsageEventType(str, enum.Enum):
    LEAD_CREATED = "lead_created"
    LEAD_ENRICHED = "lead_enriched"
    SEARCH_EXECUTED = "search_executed"
    EXPORT_GENERATED = "export_generated"
    API_CALL = "api_call"
    PIPELINE_RUN = "pipeline_run"


class UsageEvent(Base):
    __tablename__ = "usage_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    team_id = Column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True
    )
    event_type = Column(SQLEnum(UsageEventType), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    event_metadata = Column("metadata", JSONB, nullable=True)
    occurred_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    user = relationship("User", back_populates="usage_events")
