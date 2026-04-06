"""
Export Model - Track data exports and downloads
"""

import enum
import uuid

from sqlalchemy import Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class ExportFormat(str, enum.Enum):
    """
    Supported export formats
    """

    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"
    PDF = "pdf"


class ExportStatus(str, enum.Enum):
    """
    Export job status
    """

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class Export(Base):
    """
    Export model for tracking data exports

    Attributes:
        id: Unique export identifier
        user_id: User who created the export
        file_name: Generated file name
        file_url: URL to download file (S3/R2)
        file_size_bytes: Size of exported file
        format: Export format (csv, excel, json, pdf)
        status: Export status (pending, processing, completed, failed)
        records_count: Number of records exported
        filters: JSON object with filters applied
        columns: Array of columns included
        error_message: Error message if failed
        expires_at: When the export file will be deleted
        downloaded_at: When file was first downloaded
        created_at: When export was initiated
        completed_at: When export finished processing
    """

    __tablename__ = "exports"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Foreign Keys
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # File Information
    file_name = Column(String(255), nullable=False)
    file_url = Column(String(1000), nullable=True)  # S3/R2 URL
    file_size_bytes = Column(Integer, nullable=True)

    # Export Configuration
    format = Column(SQLEnum(ExportFormat), nullable=False, index=True)

    status = Column(
        SQLEnum(ExportStatus), default=ExportStatus.PENDING, nullable=False, index=True
    )

    # Data Information
    records_count = Column(Integer, default=0, nullable=False)

    filters = Column(JSONB, default=dict, nullable=False)
    # Filters used to select which records to export
    # Example: {"min_score": 70, "location": "Cambridge, MA"}

    columns = Column(JSONB, default=list, nullable=False)
    # Columns included in export
    # Example: ["name", "email", "company", "propensity_score"]

    # Error Handling
    error_message = Column(String(500), nullable=True)

    # Expiration (exports are temporary)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    # Files expire after 7 days by default

    # Download Tracking
    downloaded_at = Column(DateTime(timezone=True), nullable=True)
    download_count = Column(Integer, default=0, nullable=False)

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
    user = relationship("User", back_populates="exports")

    def __repr__(self):
        return f"<Export(id={self.id}, format={self.format}, status={self.status}, records={self.records_count})>"

    # Helper Methods
    def mark_as_processing(self):
        """
        Mark export as being processed
        """
        self.status = ExportStatus.PROCESSING

    def mark_as_completed(self, file_url: str, file_size: int):
        """
        Mark export as completed
        """
        self.status = ExportStatus.COMPLETED
        self.file_url = file_url
        self.file_size_bytes = file_size
        self.completed_at = func.now()

        # Set expiration (7 days from now)
        from datetime import datetime, timedelta, timezone

        self.expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    def mark_as_failed(self, error_message: str):
        """
        Mark export as failed
        """
        self.status = ExportStatus.FAILED
        self.error_message = error_message
        self.completed_at = func.now()

    def mark_as_downloaded(self):
        """
        Track download
        """
        from datetime import datetime, timezone

        if self.downloaded_at is None:
            self.downloaded_at = datetime.now(timezone.utc)

        self.download_count += 1

    def is_expired(self) -> bool:
        """
        Check if export has expired
        """
        if self.expires_at is None:
            return False

        from datetime import datetime, timezone

        return datetime.now(timezone.utc) > self.expires_at

    def is_downloadable(self) -> bool:
        """
        Check if export is ready to download
        """
        return (
            self.status == ExportStatus.COMPLETED
            and not self.is_expired()
            and self.file_url is not None
        )

    def get_file_size_mb(self) -> float:
        """
        Get file size in megabytes
        """
        if self.file_size_bytes is None:
            return 0.0

        return round(self.file_size_bytes / (1024 * 1024), 2)

    def to_dict(self) -> dict:
        """
        Convert export to dictionary
        """
        return {
            "id": str(self.id),
            "file_name": self.file_name,
            "file_url": self.file_url if self.is_downloadable() else None,
            "file_size_mb": self.get_file_size_mb(),
            "format": self.format.value,
            "status": self.status.value,
            "records_count": self.records_count,
            "download_count": self.download_count,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
        }
