"""
Pipeline Model - Automated data collection workflows
"""

import enum
import uuid

from sqlalchemy import Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class PipelineStatus(str, enum.Enum):
    """
    Pipeline status
    """

    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    RUNNING = "running"  # Currently executing
    ERROR = "error"


class PipelineSchedule(str, enum.Enum):
    """
    Pipeline schedule options
    """

    MANUAL = "manual"  # Run manually only
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"  # Custom cron expression


class Pipeline(Base):
    """
    Pipeline model for automated lead generation workflows

    Attributes:
        id: Unique pipeline identifier
        user_id: User who owns this pipeline
        name: Pipeline name
        description: Pipeline description
        schedule: Schedule type (manual, daily, weekly, monthly)
        cron_expression: Custom cron expression if schedule is "custom"
        config: JSON object with pipeline configuration
        status: Pipeline status (active, paused, disabled, running, error)
        last_run_at: When pipeline last ran
        last_run_status: Status of last run (success, partial, failed)
        last_run_results: JSON with results from last run
        next_run_at: When pipeline will run next
        run_count: Total number of times pipeline has run
        success_count: Number of successful runs
        error_count: Number of failed runs
        created_at: When pipeline was created
        updated_at: Last update timestamp
    """

    __tablename__ = "pipelines"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Foreign Keys
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Basic Information
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Scheduling
    schedule = Column(
        SQLEnum(PipelineSchedule),
        default=PipelineSchedule.MANUAL,
        nullable=False,
        index=True,
    )

    cron_expression = Column(String(100), nullable=True)
    # For custom schedules: "0 9 * * 1" (Every Monday at 9 AM)

    # Configuration
    config = Column(JSONB, nullable=False)
    # Example config:
    # {
    #   "data_sources": ["pubmed", "linkedin"],
    #   "search_queries": [
    #     {"source": "pubmed", "query": "drug-induced liver injury"},
    #     {"source": "linkedin", "title": "Director of Toxicology"}
    #   ],
    #   "filters": {
    #     "min_score": 70,
    #     "locations": ["Cambridge, MA", "Boston, MA"]
    #   },
    #   "enrichment": {
    #     "find_email": true,
    #     "get_company_data": true
    #   },
    #   "notifications": {
    #     "email_on_completion": true,
    #     "email_on_error": true,
    #     "webhook_url": "https://..."
    #   }
    # }

    # Status
    status = Column(
        SQLEnum(PipelineStatus),
        default=PipelineStatus.ACTIVE,
        nullable=False,
        index=True,
    )

    # Execution History
    last_run_at = Column(DateTime(timezone=True), nullable=True, index=True)

    last_run_status = Column(String(50), nullable=True)
    # Values: success, partial, failed

    last_run_results = Column(JSONB, default=dict, nullable=False)
    # Example:
    # {
    #   "leads_found": 45,
    #   "leads_created": 38,
    #   "leads_updated": 7,
    #   "leads_skipped": 0,
    #   "errors": [],
    #   "execution_time_seconds": 124,
    #   "data_sources_used": ["pubmed", "linkedin"]
    # }

    next_run_at = Column(DateTime(timezone=True), nullable=True, index=True)

    # Statistics
    run_count = Column(Integer, default=0, nullable=False)
    success_count = Column(Integer, default=0, nullable=False)
    error_count = Column(Integer, default=0, nullable=False)
    total_leads_generated = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="pipelines")

    def __repr__(self):
        return f"<Pipeline(id={self.id}, name={self.name}, schedule={self.schedule}, status={self.status})>"

    # Helper Methods
    def get_config(self, key: str, default=None):
        """
        Get a configuration value
        """
        return self.config.get(key, default)

    def set_config(self, key: str, value):
        """
        Set a configuration value
        """
        if not self.config:
            self.config = {}

        self.config[key] = value

    def activate(self):
        """
        Activate the pipeline
        """
        self.status = PipelineStatus.ACTIVE

    def pause(self):
        """
        Pause the pipeline
        """
        self.status = PipelineStatus.PAUSED

    def disable(self):
        """
        Disable the pipeline
        """
        self.status = PipelineStatus.DISABLED

    def mark_running(self):
        """
        Mark pipeline as currently running
        """
        self.status = PipelineStatus.RUNNING

    def mark_run_complete(self, success: bool, results: dict, next_run_at=None):
        """
        Mark a pipeline run as complete

        Args:
            success: Whether run was successful
            results: Results dictionary
            next_run_at: When to run next (optional)
        """
        from datetime import datetime, timezone

        self.last_run_at = datetime.now(timezone.utc)
        self.last_run_status = "success" if success else "failed"
        self.last_run_results = results

        # Initialize counters if None
        if self.run_count is None:
            self.run_count = 0
        if self.success_count is None:
            self.success_count = 0
        if self.error_count is None:
            self.error_count = 0
        if self.total_leads_generated is None:
            self.total_leads_generated = 0

        self.run_count += 1

        if success:
            self.success_count += 1
            self.status = PipelineStatus.ACTIVE

            # Update total leads generated
            leads_created = results.get("leads_created", 0)
            leads_updated = results.get("leads_updated", 0)
            self.total_leads_generated += leads_created + leads_updated
        else:
            self.error_count += 1
            self.status = PipelineStatus.ERROR

        if next_run_at:
            self.next_run_at = next_run_at

    def calculate_next_run(self):
        """
        Calculate when pipeline should run next based on schedule
        """
        from datetime import datetime, timedelta, timezone

        if self.schedule == PipelineSchedule.MANUAL:
            return None

        now = datetime.now(timezone.utc)

        if self.schedule == PipelineSchedule.DAILY:
            return now + timedelta(days=1)
        elif self.schedule == PipelineSchedule.WEEKLY:
            return now + timedelta(weeks=1)
        elif self.schedule == PipelineSchedule.MONTHLY:
            return now + timedelta(days=30)
        elif self.schedule == PipelineSchedule.CUSTOM and self.cron_expression:
            # Would need a cron parser library here
            # For now, default to 24 hours
            return now + timedelta(days=1)

        return None

    def should_run_now(self) -> bool:
        """
        Check if pipeline should run now
        """
        if self.status != PipelineStatus.ACTIVE:
            return False

        if self.schedule == PipelineSchedule.MANUAL:
            return False

        if self.next_run_at is None:
            return True

        from datetime import datetime, timezone

        return datetime.now(timezone.utc) >= self.next_run_at

    def get_success_rate(self) -> float:
        """
        Get success rate as percentage
        """
        if self.run_count == 0:
            return 0.0

        return round((self.success_count / self.run_count) * 100, 2)

    def to_dict(self) -> dict:
        """
        Convert pipeline to dictionary
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "schedule": self.schedule.value,
            "status": self.status.value,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "last_run_status": self.last_run_status,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "run_count": self.run_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": self.get_success_rate(),
            "total_leads_generated": self.total_leads_generated,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
