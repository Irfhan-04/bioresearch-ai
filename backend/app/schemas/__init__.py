"""Schemas package initialization."""

# Base schemas
from app.schemas.base import (
    BaseSchema,
    BulkDeleteRequest,
    BulkOperationResponse,
    DateRangeFilter,
    ErrorResponse,
    HealthCheckResponse,
    MessageResponse,
    PaginatedResponse,
    PaginationMeta,
    PaginationParams,
    SortParams,
    SuccessResponse,
    TimestampSchema,
    UUIDSchema,
)

# Token schemas
from app.schemas.token import (
    APIKeyCreate,
    APIKeyList,
    APIKeyResponse,
    RefreshTokenRequest,
    Token,
    TokenData,
)

# User schemas
from app.schemas.user import (
    DeleteAccountRequest,
    PasswordChange,
    PasswordReset,
    PasswordResetRequest,
    UserBase,
    UserLogin,
    UserPreferences,
    UserProfile,
    UserPublic,
    UserRegister,
    UserUpdate,
    UserUsageStats,
)

# Researcher schemas (renamed → Researcher on Day 3)
from app.schemas.researcher import (
    ResearcherBase,
    ResearcherBulkCreate,
    ResearcherCreate,
    ResearcherDetail,
    ResearcherFilters,
    ResearcherList,
    ResearcherQuery,
    ResearcherScoreUpdate,
    ResearcherUpdate,
)

# Search schemas
from app.schemas.search import SearchCreate, SearchResponse

# Export schemas
from app.schemas.export import ExportCreate, ExportResponse