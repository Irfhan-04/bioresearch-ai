"""
Webhook Database Models
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class WebhookEventType(str, enum.Enum):
    """Types of webhook events"""

    PIPELINE_COMPLETED = "pipeline.completed"
    PIPELINE_FAILED = "pipeline.failed"
    LEAD_CREATED = "lead.created"
    LEAD_ENRICHED = "lead.enriched"
    LEAD_SCORED = "lead.scored"
    HIGH_VALUE_LEAD = "lead.high_value"
    EXPORT_READY = "export.ready"


class Webhook(Base):
    """
    Webhook endpoint configuration

    Allows users to receive real-time notifications about events
    """

    __tablename__ = "webhooks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Configuration
    name = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    secret_key = Column(String(100), nullable=False)  # For signature verification

    # Events to listen for
    events = Column(ARRAY(String), nullable=False, default=list)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Statistics
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    last_failure_at = Column(DateTime(timezone=True), nullable=True)
    success_count = Column(Integer, default=0, nullable=False)
    failure_count = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="webhooks")
    events_log = relationship(
        "WebhookEvent", back_populates="webhook", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Webhook {self.name} ({self.url})>"

    def get_success_rate(self) -> float:
        """Calculate webhook success rate"""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.0
        return (self.success_count / total) * 100


class WebhookEvent(Base):
    """
    Webhook event log

    Tracks all webhook deliveries for debugging and monitoring
    """

    __tablename__ = "webhook_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    webhook_id = Column(
        UUID(as_uuid=True),
        ForeignKey("webhooks.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Event details
    event_type = Column(SQLEnum(WebhookEventType), nullable=False)
    payload = Column(JSON, nullable=False)

    # Delivery details
    attempts = Column(Integer, default=0, nullable=False)
    delivered_at = Column(DateTime(timezone=True), nullable=True)

    # Response
    response_status_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)

    # Timestamp
    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    webhook = relationship("Webhook", back_populates="events_log")

    def __repr__(self):
        return f"<WebhookEvent {self.event_type} for {self.webhook_id}>"

    @property
    def is_successful(self) -> bool:
        """Check if event was delivered successfully"""
        return self.delivered_at is not None
