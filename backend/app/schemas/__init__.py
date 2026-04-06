"""
Schemas package initialization
Import all schemas for easy access
"""

# Base schemas
from app.schemas.base import (BaseSchema, BulkDeleteRequest,
                              BulkOperationResponse, DateRangeFilter,
                              ErrorResponse, HealthCheckResponse,
                              MessageResponse, PaginatedResponse,
                              PaginationMeta, PaginationParams, SortParams,
                              SuccessResponse, TimestampSchema, UUIDSchema)
# Export schemas
from app.schemas.export import ExportCreate, ExportResponse
# Lead schemas
from app.schemas.lead import (LeadBase, LeadBulkCreate, LeadCreate, LeadDetail,
                              LeadFilters, LeadList, LeadQuery,
                              LeadScoreUpdate, LeadUpdate)
# Pipeline schemas
from app.schemas.pipeline import (PipelineCreate, PipelineResponse,
                                  PipelineRunRequest, PipelineUpdate)
# Search schemas
from app.schemas.search import SearchCreate, SearchResponse
# Team schemas
from app.schemas.team import (
    InviteCreate,
    InviteResponse,
    MemberResponse,
    RoleUpdate,
    TeamCreate,
    TeamResponse,
    TeamUpdate,
)
from app.schemas.usage import AdminUserSummary, UsageEventOut, UsageSummary
# Token schemas
from app.schemas.token import (APIKeyCreate, APIKeyList, APIKeyResponse,
                               RefreshTokenRequest, Token, TokenData)
# User schemas
from app.schemas.user import (DeleteAccountRequest, PasswordChange, PasswordReset,
                              PasswordResetRequest, UserBase, UserLogin,
                              UserPreferences, UserProfile, UserPublic,
                              UserRegister, UserUpdate, UserUsageStats)

# Export all
__all__ = [
    # Base
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
    "BulkOperationResponse",
    "BulkDeleteRequest",
    "HealthCheckResponse",
    "TeamCreate",
    "TeamUpdate",
    "TeamResponse",
    "MemberResponse",
    "RoleUpdate",
    "InviteCreate",
    "InviteResponse",
    "UsageEventOut",
    "UsageSummary",
    "AdminUserSummary",
    # Token
    "Token",
    "TokenData",
    "RefreshTokenRequest",
    "APIKeyCreate",
    "APIKeyResponse",
    "APIKeyList",
    # User
    "UserRegister",
    "UserLogin",
    "UserBase",
    "UserProfile",
    "UserPublic",
    "UserUpdate",
    "DeleteAccountRequest",
    "PasswordChange",
    "PasswordResetRequest",
    "PasswordReset",
    "UserPreferences",
    "UserUsageStats",
    # Lead
    "LeadCreate",
    "LeadUpdate",
    "LeadBase",
    "LeadDetail",
    "LeadList",
    "LeadFilters",
    "LeadQuery",
    "LeadBulkCreate",
    "LeadScoreUpdate",
    # Search
    "SearchCreate",
    "SearchResponse",
    # Export
    "ExportCreate",
    "ExportResponse",
    # Pipeline
    "PipelineCreate",
    "PipelineUpdate",
    "PipelineResponse",
    "PipelineRunRequest",
]
