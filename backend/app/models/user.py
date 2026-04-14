"""
User Model — Authentication and user management for BioResearch AI.
This model defines the structure of the user data, including authentication credentials, 
profile information, account status, API keys, usage tracking, and UI preferences.
"""

import uuid

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from app.core.database import Base


class User(Base):
    """
    User model for authentication and profile management.

    Attributes:
        id:            Unique user identifier (UUID)
        email:         User's email address (unique)
        password_hash: Hashed password — never store plain text
        full_name:     User's display name
        is_active:     Whether account is active
        is_verified:   Whether email is verified
        is_superuser:  Admin privileges
        api_keys:      JSON array of hashed API key records
        usage_stats:   JSON object tracking searches and enrichments (non-billing)
        preferences:   JSON object for UI preferences
        created_at:    Account creation timestamp
        updated_at:    Last update timestamp
        last_login_at: Last login timestamp
    """

    __tablename__ = "users"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Authentication
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    # Profile
    full_name = Column(String(255), nullable=True)

    # Account Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)

    # API Keys (stored as hashed values in JSON array)
    api_keys = Column(JSONB, default=list, nullable=False)
    # Example: [{"name": "prod-key", "hash": "xxx", "created_at": "2024-01-01"}]

    # Usage Tracking (non-billing — tracks searches and enrichments for display only)
    usage_stats = Column(JSONB, default=dict, nullable=False)
    # Example: {"researchers_created_this_month": 45, "searches_this_month": 12}

    # Daily search tracking for rate limiting
    # Resets at midnight UTC. Guest limits tracked by IP in Redis.
    daily_searches = Column(Integer, default=0, nullable=False,
        server_default="0",
        comment="Searches performed today by this registered user")
    daily_searches_reset_at = Column(
        DateTime(timezone=True),
        server_default=func.now(), nullable=False,
        comment="Last time daily_searches was reset to 0")

    # UI Preferences
    preferences = Column(JSONB, default=dict, nullable=False)
    # Example: {"theme": "dark", "default_export_format": "csv"}

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    researchers = relationship(
        "Researcher",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="Researcher.user_id",
    )
    searches = relationship(
        "Search", back_populates="user", cascade="all, delete-orphan"
    )
    exports = relationship(
        "Export", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"

    def increment_usage(self, metric: str, amount: int = 1) -> None:
        """Increment a non-billing usage metric (searches, enrichments)."""
        if not self.usage_stats:
            self.usage_stats = {}
        self.usage_stats[metric] = self.usage_stats.get(metric, 0) + amount

    def get_preference(self, key: str, default=None):
        """Get a UI preference value."""
        return self.preferences.get(key, default) if self.preferences else default

    def set_preference(self, key: str, value) -> None:
        """Set a UI preference value."""
        if not self.preferences:
            self.preferences = {}
        self.preferences[key] = value