"""
Search Schemas
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.base import TimestampSchema


class SearchCreate(BaseModel):
    """Create new search"""

    query: str = Field(..., min_length=1, description="Search query")
    search_type: str = Field(..., description="pubmed, linkedin, conference, etc.")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Applied filters")
    save_search: bool = Field(default=False, description="Save this search")
    saved_name: Optional[str] = Field(
        None, max_length=255, description="Name for saved search"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "drug-induced liver injury 3D models",
                "search_type": "pubmed",
                "filters": {"years": [2023, 2024]},
                "save_search": True,
                "saved_name": "DILI Research 2024",
            }
        }
    }


class SearchResponse(TimestampSchema):
    """Search response"""

    id: UUID
    query: str
    search_type: str
    filters: Dict[str, Any]
    results_count: int
    is_saved: bool
    saved_name: Optional[str] = None
    execution_time_ms: Optional[int] = None
