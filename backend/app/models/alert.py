"""AlertRule model for smart alerts."""

import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class AlertTrigger(str, enum.Enum):
    HIGH_VALUE_LEAD = "high_value_lead"
    NEW_NIH_GRANT = "new_nih_grant"
    CONFERENCE_MATCH = "conference_match"
    SCORE_INCREASE = "score_increase"


class AlertChannel(str, enum.Enum):
    EMAIL = "email"
    WEBHOOK = "webhook"
    BOTH = "both"


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    trigger = Column(SQLEnum(AlertTrigger), nullable=False)
    channel = Column(SQLEnum(AlertChannel), default=AlertChannel.EMAIL, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    conditions = Column(JSONB, nullable=False, default=dict)
    throttle_seconds = Column(Integer, default=3600, nullable=False)
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    trigger_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User")

    def is_throttled(self) -> bool:
        if not self.last_triggered_at:
            return False
        from datetime import datetime, timezone

        elapsed = (datetime.now(timezone.utc) - self.last_triggered_at).total_seconds()
        return elapsed < self.throttle_seconds
