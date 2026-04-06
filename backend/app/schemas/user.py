"""
User Schemas - User registration, authentication, and profile management
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import SubscriptionTier
from app.schemas.base import BaseSchema, TimestampSchema, UUIDSchema

# ============================================================================
# REGISTRATION & AUTHENTICATION
# ============================================================================


class UserRegister(BaseModel):
    """
    User registration request
    """

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(
        ..., min_length=8, max_length=100, description="Password (min 8 chars)"
    )
    full_name: str = Field(..., min_length=2, max_length=255, description="Full name")

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        """Convert email to lowercase"""
        return v.lower().strip()

    @field_validator("full_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and clean name"""
        return v.strip()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")

        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")

        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")

        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")

        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in v):
            raise ValueError("Password must contain at least one special character")

        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123!",
                "full_name": "John Doe",
            }
        }
    }


class UserLogin(BaseModel):
    """
    User login request
    """

    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="User password")

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.lower().strip()

    model_config = {
        "json_schema_extra": {
            "example": {"email": "user@example.com", "password": "SecurePass123!"}
        }
    }


# ============================================================================
# USER RESPONSES
# ============================================================================


class UserBase(BaseSchema):
    """
    Base user fields (public information)
    """

    id: UUID
    email: EmailStr
    full_name: str
    subscription_tier: SubscriptionTier
    is_active: bool
    is_verified: bool

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "full_name": "John Doe",
                "subscription_tier": "free",
                "is_active": True,
                "is_verified": True,
            }
        }
    }


class UserProfile(UserBase, TimestampSchema):
    """
    Full user profile (includes timestamps and preferences)
    """

    last_login_at: Optional[datetime] = None
    usage_stats: Dict[str, Any] = {}
    preferences: Dict[str, Any] = {}

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "full_name": "John Doe",
                "subscription_tier": "pro",
                "is_active": True,
                "is_verified": True,
                "last_login_at": "2024-12-30T12:00:00Z",
                "usage_stats": {
                    "leads_created_this_month": 45,
                    "searches_this_month": 12,
                },
                "preferences": {"theme": "dark", "email_notifications": True},
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-12-30T12:00:00Z",
            }
        }
    }


class UserPublic(BaseSchema):
    """
    Public user information (minimal, for sharing)
    """

    id: UUID
    full_name: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "full_name": "John Doe",
            }
        }
    }


# ============================================================================
# USER UPDATES
# ============================================================================


class UserUpdate(BaseModel):
    """
    Update user profile
    """

    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None

    @field_validator("full_name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return v.strip()
        return v

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return v.lower().strip()
        return v

    model_config = {
        "json_schema_extra": {
            "example": {"full_name": "Jane Doe", "email": "jane@example.com"}
        }
    }


class PasswordChange(BaseModel):
    """
    Change password request
    """

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(
        ..., min_length=8, max_length=100, description="New password"
    )

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")

        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")

        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")

        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")

        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "current_password": "OldPass123!",
                "new_password": "NewPass456@",
            }
        }
    }


class PasswordResetRequest(BaseModel):
    """
    Request password reset
    """

    email: EmailStr = Field(..., description="Email address")

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.lower().strip()

    model_config = {"json_schema_extra": {"example": {"email": "user@example.com"}}}


class PasswordReset(BaseModel):
    """
    Reset password with token
    """

    token: str = Field(..., description="Reset token from email")
    new_password: str = Field(
        ..., min_length=8, max_length=100, description="New password"
    )

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")

        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")

        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")

        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")

        return v

    model_config = {
        "json_schema_extra": {
            "example": {"token": "abc123xyz789...", "new_password": "NewSecurePass123!"}
        }
    }


# ============================================================================
# USER PREFERENCES
# ============================================================================


class UserPreferences(BaseModel):
    """
    User preferences update
    """

    theme: Optional[str] = Field(None, pattern="^(light|dark|auto)$")
    email_notifications: Optional[bool] = None
    default_export_format: Optional[str] = Field(None, pattern="^(csv|excel|json|pdf)$")
    scoring_weights: Optional[Dict[str, int]] = None

    @field_validator("scoring_weights")
    @classmethod
    def validate_weights(cls, v: Optional[Dict[str, int]]) -> Optional[Dict[str, int]]:
        """Validate scoring weights sum to 100"""
        if v is not None:
            total = sum(v.values())
            if total != 100:
                raise ValueError(f"Scoring weights must sum to 100, got {total}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "theme": "dark",
                "email_notifications": True,
                "default_export_format": "csv",
                "scoring_weights": {
                    "role_fit": 30,
                    "publication": 40,
                    "funding": 20,
                    "location": 10,
                },
            }
        }
    }


# ============================================================================
# USAGE STATISTICS
# ============================================================================


class UserUsageStats(BaseSchema):
    """
    User usage statistics
    """

    leads_created_this_month: int
    leads_limit_per_month: int
    searches_this_month: int
    exports_this_month: int
    api_calls_today: int
    subscription_tier: SubscriptionTier
    usage_percentage: float = Field(..., description="Percentage of monthly limit used")

    model_config = {
        "json_schema_extra": {
            "example": {
                "leads_created_this_month": 45,
                "leads_limit_per_month": 100,
                "searches_this_month": 12,
                "exports_this_month": 5,
                "api_calls_today": 150,
                "subscription_tier": "free",
                "usage_percentage": 45.0,
            }
        }
    }


class DeleteAccountRequest(BaseModel):
    """Requires current password to confirm account deletion."""

    password: str = Field(
        ...,
        min_length=1,
        description="Current password for confirmation",
    )

# Export all
__all__ = [
    "UserRegister",
    "UserLogin",
    "UserBase",
    "UserProfile",
    "UserPublic",
    "UserUpdate",
    "DeleteAccountRequest",   # ← keep only once
    "PasswordChange",
    "PasswordResetRequest",
    "PasswordReset",
    "UserPreferences",
    "UserUsageStats",
]
