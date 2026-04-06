"""
Export Schemas
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.export import ExportFormat, ExportStatus
from app.schemas.base import TimestampSchema


class ExportCreate(BaseModel):
    """Create export request"""

    format: ExportFormat = Field(..., description="Export format")
    filters: Dict[str, Any] = Field(
        default_factory=dict, description="Filters to apply"
    )
    columns: List[str] = Field(
        default_factory=list, description="Columns to include (empty = all)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "format": "excel",
                "filters": {"min_score": 70},
                "columns": ["name", "email", "company", "propensity_score"],
            }
        }
    }


class ExportResponse(TimestampSchema):
    """Export response"""

    id: UUID
    file_name: str
    file_url: Optional[str] = None
    file_size_mb: float = 0.0
    format: ExportFormat
    status: ExportStatus
    records_count: int
    download_count: int
    expires_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "file_name": "leads_export_20241230.xlsx",
                "file_url": "https://r2.cloudflare.com/...",
                "file_size_mb": 2.5,
                "format": "excel",
                "status": "completed",
                "records_count": 200,
                "download_count": 3,
                "expires_at": "2025-01-06T12:00:00Z",
                "created_at": "2024-12-30T12:00:00Z",
                "completed_at": "2024-12-30T12:02:00Z",
            }
        }
    }
