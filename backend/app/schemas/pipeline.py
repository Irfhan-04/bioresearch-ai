"""
Pipeline Schemas
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.pipeline import PipelineSchedule, PipelineStatus
from app.schemas.base import TimestampSchema


class PipelineCreate(BaseModel):
    """Create new pipeline"""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    schedule: PipelineSchedule = Field(default=PipelineSchedule.MANUAL)
    cron_expression: Optional[str] = Field(None, max_length=100)
    config: Dict[str, Any] = Field(..., description="Pipeline configuration")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Daily PubMed Scan",
                "description": "Search PubMed for DILI research daily",
                "schedule": "daily",
                "config": {
                    "data_sources": ["pubmed"],
                    "search_queries": [
                        {"source": "pubmed", "query": "drug-induced liver injury"}
                    ],
                    "filters": {"min_score": 70},
                    "enrichment": {"find_email": True},
                },
            }
        }
    }


class PipelineUpdate(BaseModel):
    """Update pipeline"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    schedule: Optional[PipelineSchedule] = None
    cron_expression: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    status: Optional[PipelineStatus] = None


class PipelineResponse(TimestampSchema):
    """Pipeline response"""

    id: UUID
    name: str
    description: Optional[str] = None
    schedule: PipelineSchedule
    cron_expression: Optional[str] = None
    status: PipelineStatus
    last_run_at: Optional[datetime] = None
    last_run_status: Optional[str] = None
    last_run_results: Dict[str, Any]
    next_run_at: Optional[datetime] = None
    run_count: int
    success_count: int
    error_count: int
    total_leads_generated: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Daily PubMed Scan",
                "schedule": "daily",
                "status": "active",
                "last_run_at": "2024-12-30T09:00:00Z",
                "last_run_status": "success",
                "last_run_results": {
                    "leads_found": 45,
                    "leads_created": 38,
                    "leads_updated": 7,
                },
                "next_run_at": "2024-12-31T09:00:00Z",
                "run_count": 30,
                "success_count": 28,
                "error_count": 2,
                "total_leads_generated": 856,
                "created_at": "2024-12-01T00:00:00Z",
                "updated_at": "2024-12-30T09:00:00Z",
            }
        }
    }


class PipelineRunRequest(BaseModel):
    """Manually trigger pipeline run"""

    override_config: Optional[Dict[str, Any]] = Field(
        None, description="Temporary config override"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "override_config": {
                    "search_queries": [
                        {"source": "pubmed", "query": "hepatotoxicity 2024"}
                    ]
                }
            }
        }
    }
