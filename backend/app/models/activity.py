"""LeadActivity append-only collaboration log."""

import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class ActivityType(str, enum.Enum):
    """Supported collaboration activity types."""

    NOTE = "note"
    COMMENT = "comment"
    ASSIGNMENT = "assignment"
    STATUS_CHANGE = "status_change"
    REMINDER = "reminder"
    MENTION = "mention"
    ENRICHMENT = "enrichment"
    SCORE_CHANGE = "score_change"


class LeadActivity(Base):
    """Append-only collaboration activity log for a lead."""

    __tablename__ = "lead_activities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(
        UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    activity_type = Column(SQLEnum(ActivityType), nullable=False, index=True)
    content = Column(Text, nullable=True)
    mentioned_user_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True)
    activity_metadata = Column("metadata", JSONB, nullable=True)
    reminder_due_at = Column(DateTime(timezone=True), nullable=True, index=True)
    reminder_done = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    lead = relationship("Lead")
    author = relationship("User", foreign_keys=[user_id])
