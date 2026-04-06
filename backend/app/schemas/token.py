"""
Token Schemas - JWT authentication tokens
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.base import BaseSchema


class Token(BaseModel):
    """
    JWT token response
    """

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Seconds until access token expires")

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 86400,
            }
        }
    }


class TokenData(BaseModel):
    """
    Data extracted from JWT token
    """

    user_id: Optional[UUID] = None
    email: Optional[str] = None
    exp: Optional[datetime] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "exp": "2024-12-31T23:59:59Z",
            }
        }
    }


class RefreshTokenRequest(BaseModel):
    """
    Request to refresh access token
    """

    refresh_token: str = Field(..., description="Refresh token")

    model_config = {
        "json_schema_extra": {
            "example": {"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}
        }
    }


class APIKeyCreate(BaseModel):
    """
    Create new API key
    """

    name: str = Field(
        ..., min_length=1, max_length=100, description="Key name/description"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and clean name"""
        return v.strip()

    model_config = {"json_schema_extra": {"example": {"name": "Production API Key"}}}


class APIKeyResponse(BaseSchema):
    """
    API key response (shown only once!)
    """

    id: UUID
    name: str
    key: str = Field(..., description="API key (shown only on creation!)")
    prefix: str = Field(..., description="Key prefix for identification")
    created_at: datetime

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Production API Key",
                "key": "btlg_abcdef123456...",
                "prefix": "btlg_abcd",
                "created_at": "2024-12-30T12:00:00Z",
            }
        }
    }


class APIKeyList(BaseSchema):
    """
    API key list item (without actual key)
    """

    id: UUID
    name: str
    prefix: str
    created_at: datetime
    last_used_at: Optional[datetime] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Production API Key",
                "prefix": "btlg_abcd",
                "created_at": "2024-12-30T12:00:00Z",
                "last_used_at": "2024-12-30T14:30:00Z",
            }
        }
    }


__all__ = [
    "Token",
    "TokenData",
    "RefreshTokenRequest",
    "APIKeyCreate",
    "APIKeyResponse",
    "APIKeyList",
]
