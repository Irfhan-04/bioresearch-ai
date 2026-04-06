"""
Lead Schemas - Lead creation, updates, and responses
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator

from app.schemas.base import (BaseSchema, PaginationParams, SortParams,
                              TimestampSchema)

# ============================================================================
# LEAD CREATION & UPDATES
# ============================================================================


class ResearcherCreate(BaseModel):
    """
    Create new lead
    """

    name: str = Field(..., min_length=2, max_length=255, description="Full name")
    title: Optional[str] = Field(None, max_length=255, description="Job title")
    company: Optional[str] = Field(None, max_length=255, description="Company name")
    location: Optional[str] = Field(
        None, max_length=255, description="Personal location"
    )
    company_hq: Optional[str] = Field(
        None, max_length=255, description="Company HQ location"
    )

    email: Optional[EmailStr] = Field(None, description="Contact email")
    phone: Optional[str] = Field(None, max_length=50, description="Phone number")
    linkedin_url: Optional[str] = Field(
        None, max_length=500, description="LinkedIn profile URL"
    )
    twitter_url: Optional[str] = Field(
        None, max_length=500, description="Twitter/X profile"
    )
    website: Optional[str] = Field(None, max_length=500, description="Website")

    recent_publication: bool = Field(
        default=False, description="Has recent publication"
    )
    publication_year: Optional[int] = Field(
        None, ge=1950, le=2100, description="Publication year"
    )
    publication_title: Optional[str] = Field(None, description="Publication title")
    publication_count: int = Field(default=0, ge=0, description="Total publications")

    company_funding: Optional[str] = Field(
        None, max_length=50, description="Funding stage"
    )
    company_size: Optional[str] = Field(None, max_length=50, description="Company size")
    uses_3d_models: bool = Field(default=False, description="Uses 3D in-vitro models")

    tags: List[str] = Field(default_factory=list, description="Custom tags")
    notes: Optional[str] = Field(None, description="Internal notes")
    custom_fields: Dict[str, Any] = Field(
        default_factory=dict, description="Custom fields"
    )

    @field_validator("name", "title", "company")
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return v.strip()
        return v

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return v.lower().strip()
        return v

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """Clean and validate tags"""
        # Remove empty tags, strip whitespace, limit to 20 tags
        cleaned = [tag.strip().lower() for tag in v if tag.strip()]
        return cleaned[:20]

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Dr. Sarah Mitchell",
                "title": "Director of Toxicology",
                "company": "Moderna Therapeutics",
                "location": "Cambridge, MA",
                "company_hq": "Cambridge, MA",
                "email": "sarah.mitchell@modernatx.com",
                "linkedin_url": "https://linkedin.com/in/sarahmitchell",
                "recent_publication": True,
                "publication_year": 2024,
                "publication_title": "Novel 3D hepatic models for DILI assessment",
                "company_funding": "Public",
                "uses_3d_models": True,
                "tags": ["high-priority", "conference-speaker"],
            }
        }
    }


class ResearcherUpdate(BaseModel):
    """
    Update existing lead
    """

    name: Optional[str] = Field(None, min_length=2, max_length=255)
    title: Optional[str] = Field(None, max_length=255)
    company: Optional[str] = Field(None, max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    company_hq: Optional[str] = Field(None, max_length=255)

    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    linkedin_url: Optional[str] = Field(None, max_length=500)
    twitter_url: Optional[str] = Field(None, max_length=500)
    website: Optional[str] = Field(None, max_length=500)

    recent_publication: Optional[bool] = None
    publication_year: Optional[int] = Field(None, ge=1950, le=2100)
    publication_title: Optional[str] = None
    publication_count: Optional[int] = Field(None, ge=0)

    company_funding: Optional[str] = Field(None, max_length=50)
    company_size: Optional[str] = Field(None, max_length=50)
    uses_3d_models: Optional[bool] = None

    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    status: Optional[str] = Field(None, max_length=50)
    custom_fields: Optional[Dict[str, Any]] = None

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return v.lower().strip()
        return v

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            cleaned = [tag.strip().lower() for tag in v if tag.strip()]
            return cleaned[:20]
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "Senior Director of Toxicology",
                "email": "sarah.mitchell@newemail.com",
                "tags": ["high-priority", "conference-speaker", "published-author"],
            }
        }
    }


# ============================================================================
# LEAD RESPONSES
# ============================================================================


class ResearcherBase(BaseSchema):
    """
    Base lead information
    """

    id: UUID
    name: str
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    email: Optional[str] = None
    relevance_score: Optional[int] = None
    rank: Optional[int] = None
    relevance_tier: Optional[str] = None
    status: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Dr. Sarah Mitchell",
                "title": "Director of Toxicology",
                "company": "Moderna Therapeutics",
                "location": "Cambridge, MA",
                "email": "sarah.mitchell@modernatx.com",
                "relevance_score": 95,
                "rank": 1,
                "relevance_tier": "HIGH",
                "status": "NEW",
            }
        }
    }


class ResearcherDetail(TimestampSchema):
    """
    Detailed lead information
    """

    id: UUID
    name: str
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    email: Optional[str] = None
    relevance_score: Optional[int] = None
    rank: Optional[int] = None
    relevance_tier: Optional[str] = None
    status: str

    company_hq: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    twitter_url: Optional[str] = None
    website: Optional[str] = None

    recent_publication: bool
    publication_year: Optional[int] = None
    publication_title: Optional[str] = None
    publication_count: int

    company_funding: Optional[str] = None
    company_size: Optional[str] = None
    uses_3d_models: bool

    data_sources: List[str] = []
    enrichment_data: Dict[str, Any] = {}
    custom_fields: Dict[str, Any] = {}

    tags: List[str] = []
    notes: Optional[str] = None

    last_contacted_at: Optional[datetime] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Dr. Sarah Mitchell",
                "title": "Director of Toxicology",
                "company": "Moderna Therapeutics",
                "location": "Cambridge, MA",
                "company_hq": "Cambridge, MA",
                "email": "sarah.mitchell@modernatx.com",
                "phone": "+1-555-0123",
                "linkedin_url": "https://linkedin.com/in/sarahmitchell",
                "relevance_score": 95,
                "rank": 1,
                "relevance_tier": "HIGH",
                "status": "NEW",
                "recent_publication": True,
                "publication_year": 2024,
                "publication_title": "Novel 3D hepatic models for DILI assessment",
                "publication_count": 15,
                "company_funding": "Public",
                "uses_3d_models": True,
                "data_sources": ["pubmed", "linkedin"],
                "tags": ["high-priority", "conference-speaker"],
                "created_at": "2024-12-01T00:00:00Z",
                "updated_at": "2024-12-30T12:00:00Z",
            }
        }
    }


class ResearcherList(BaseModel):
    """
    Simplified lead for list view
    """

    id: UUID
    name: str
    title: Optional[str] = None
    company: Optional[str] = None
    email: Optional[str] = None
    relevance_score: Optional[int] = None
    relevance_tier: Optional[str] = None
    tags: List[str] = []
    created_at: datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Dr. Sarah Mitchell",
                "title": "Director of Toxicology",
                "company": "Moderna Therapeutics",
                "email": "sarah.mitchell@modernatx.com",
                "relevance_score": 95,
                "relevance_tier": "HIGH",
                "tags": ["high-priority"],
                "created_at": "2024-12-01T00:00:00Z",
            }
        },
    }


# ============================================================================
# LEAD FILTERING & SEARCH
# ============================================================================


class ResearcherFilters(BaseModel):
    """
    Lead filtering parameters
    """

    search: Optional[str] = Field(None, description="Search in name, title, company")
    min_score: Optional[int] = Field(
        None, ge=0, le=100, description="Minimum propensity score"
    )
    max_score: Optional[int] = Field(
        None, ge=0, le=100, description="Maximum propensity score"
    )
    relevance_tier: Optional[str] = Field(None, pattern="^(HIGH|MEDIUM|LOW)$")
    status: Optional[str] = None

    location: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None

    has_email: Optional[bool] = None
    has_linkedin: Optional[bool] = None
    has_publication: Optional[bool] = None
    uses_3d_models: Optional[bool] = None

    tags: Optional[List[str]] = None
    funding_stages: Optional[List[str]] = None

    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "search": "director toxicology",
                "min_score": 70,
                "relevance_tier": "HIGH",
                "location": "Cambridge",
                "has_email": True,
                "tags": ["high-priority", "conference-speaker"],
            }
        }
    }


class ResearcherQuery(PaginationParams, SortParams):
    """
    Combined lead query parameters
    """

    filters: ResearcherFilters = Field(default_factory=ResearcherFilters)

    model_config = {
        "json_schema_extra": {
            "example": {
                "page": 1,
                "size": 50,
                "sort_by": "relevance_score",
                "sort_order": "desc",
                "filters": {"min_score": 70, "location": "Cambridge"},
            }
        }
    }


# ============================================================================
# BULK OPERATIONS
# ============================================================================


class ResearcherBulkCreate(BaseModel):
    """
    Bulk create leads
    """

    leads: List[ResearcherCreate] = Field(..., min_length=1, max_length=100)
    skip_duplicates: bool = Field(default=True, description="Skip duplicate emails")
    calculate_scores: bool = Field(
        default=True, description="Calculate propensity scores"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "leads": [
                    {
                        "name": "Dr. Sarah Mitchell",
                        "title": "Director of Toxicology",
                        "company": "Moderna",
                        "email": "sarah@modernatx.com",
                    }
                ],
                "skip_duplicates": True,
                "calculate_scores": True,
            }
        }
    }


class ResearcherScoreUpdate(BaseModel):
    """
    Update lead score
    """

    relevance_score: int = Field(..., ge=0, le=100, description="New propensity score")
    recalculate: bool = Field(default=False, description="Recalculate using algorithm")

    model_config = {
        "json_schema_extra": {"example": {"relevance_score": 95, "recalculate": False}}
    }


# Export all
__all__ = [
    "ResearcherCreate",
    "ResearcherUpdate",
    "ResearcherBase",
    "ResearcherDetail",
    "ResearcherList",
    "ResearcherFilters",
    "ResearcherQuery",
    "ResearcherBulkCreate",
    "ResearcherScoreUpdate",
]
