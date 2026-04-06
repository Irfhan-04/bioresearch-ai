"""
Base Schemas - Common patterns and base classes
"""

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    """
    Base schema with common configuration
    """

    model_config = ConfigDict(
        from_attributes=True,  # Allow creation from ORM models
        validate_assignment=True,  # Validate on assignment
        str_strip_whitespace=True,  # Strip whitespace from strings
        json_schema_extra={"example": {}},
    )


class TimestampSchema(BaseSchema):
    """
    Schema with timestamp fields
    """

    created_at: datetime
    updated_at: datetime


class UUIDSchema(BaseSchema):
    """
    Schema with UUID primary key
    """

    id: UUID


# ============================================================================
# RESPONSE WRAPPERS
# ============================================================================


class SuccessResponse(BaseModel):
    """
    Standard success response wrapper
    """

    success: bool = True
    message: str
    data: Optional[Any] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "data": {"id": "123"},
            }
        }
    )


class ErrorResponse(BaseModel):
    """
    Standard error response wrapper
    """

    success: bool = False
    message: str
    error_code: Optional[str] = None
    details: Optional[Any] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": False,
                "message": "Validation error",
                "error_code": "VALIDATION_ERROR",
                "details": {"email": ["Invalid email format"]},
            }
        }
    )


class MessageResponse(BaseModel):
    """
    Simple message response
    """

    message: str

    model_config = ConfigDict(
        json_schema_extra={"example": {"message": "Lead deleted successfully"}}
    )


# ============================================================================
# PAGINATION
# ============================================================================


class PaginationParams(BaseModel):
    """
    Pagination query parameters
    """

    page: int = Field(default=1, ge=1, description="Page number (starts at 1)")
    size: int = Field(default=50, ge=1, le=100, description="Items per page (max 100)")

    def get_offset(self) -> int:
        """Calculate offset for database query"""
        return (self.page - 1) * self.size

    model_config = ConfigDict(json_schema_extra={"example": {"page": 1, "size": 50}})


class PaginationMeta(BaseModel):
    """
    Pagination metadata
    """

    page: int
    size: int
    total: int
    pages: int

    model_config = ConfigDict(
        json_schema_extra={"example": {"page": 1, "size": 50, "total": 250, "pages": 5}}
    )


class PaginatedResponse(BaseModel):
    """
    Generic paginated response
    """

    items: List[Any]
    pagination: PaginationMeta

    @classmethod
    def create(cls, items: List[Any], page: int, size: int, total: int):
        """
        Helper to create paginated response
        """
        import math

        pages = math.ceil(total / size) if size > 0 else 0

        return cls(
            items=items,
            pagination=PaginationMeta(page=page, size=size, total=total, pages=pages),
        )


# ============================================================================
# SORTING & FILTERING
# ============================================================================


class SortParams(BaseModel):
    """
    Sorting parameters
    """

    sort_by: str = Field(default="created_at", description="Field to sort by")
    sort_order: str = Field(
        default="desc", pattern="^(asc|desc)$", description="Sort order"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"sort_by": "propensity_score", "sort_order": "desc"}
        }
    )


class DateRangeFilter(BaseModel):
    """
    Date range filter
    """

    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-12-31T23:59:59Z",
            }
        }
    )


# ============================================================================
# COMMON FIELD VALIDATORS
# ============================================================================

import re

from pydantic import EmailStr, field_validator


class EmailMixin(BaseModel):
    """
    Mixin for email validation
    """

    email: EmailStr

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        """Convert email to lowercase"""
        return v.lower()


class URLMixin(BaseModel):
    """
    Mixin for URL validation
    """

    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format"""
        if not v:
            return v

        # Basic URL validation
        url_pattern = re.compile(
            r"^https?://"  # http:// or https://
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
            r"localhost|"  # localhost...
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
            r"(?::\d+)?"  # optional port
            r"(?:/?|[/?]\S+)$",
            re.IGNORECASE,
        )

        if not url_pattern.match(v):
            raise ValueError("Invalid URL format")

        return v


# ============================================================================
# BULK OPERATIONS
# ============================================================================


class BulkOperationResponse(BaseModel):
    """
    Response for bulk operations
    """

    success_count: int = 0
    failure_count: int = 0
    total: int = 0
    errors: List[dict] = []

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success_count": 45,
                "failure_count": 5,
                "total": 50,
                "errors": [
                    {"row": 3, "error": "Invalid email format"},
                    {"row": 7, "error": "Duplicate entry"},
                ],
            }
        }
    )


class BulkDeleteRequest(BaseModel):
    """
    Request to delete multiple items
    """

    ids: List[UUID] = Field(..., min_length=1, max_length=100)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ids": [
                    "123e4567-e89b-12d3-a456-426614174000",
                    "123e4567-e89b-12d3-a456-426614174001",
                ]
            }
        }
    )


# ============================================================================
# HEALTH CHECK
# ============================================================================


class HealthCheckResponse(BaseModel):
    """
    Health check response
    """

    status: str = "healthy"
    version: str
    database: str
    cache: str
    timestamp: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "version": "2.0.0",
                "database": "connected",
                "cache": "connected",
                "timestamp": "2024-12-30T12:00:00Z",
            }
        }
    )


# Export all
__all__ = [
    "BaseSchema",
    "TimestampSchema",
    "UUIDSchema",
    "SuccessResponse",
    "ErrorResponse",
    "MessageResponse",
    "PaginationParams",
    "PaginationMeta",
    "PaginatedResponse",
    "SortParams",
    "DateRangeFilter",
    "EmailMixin",
    "URLMixin",
    "BulkOperationResponse",
    "BulkDeleteRequest",
    "HealthCheckResponse",
]
