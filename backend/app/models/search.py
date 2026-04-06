"""
Search Model - Track user searches and history
"""

import uuid

from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer, String,
                        Text)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Search(Base):
    """
    Search model for tracking search history

    Attributes:
        id: Unique search identifier
        user_id: User who performed the search
        query: Search query text
        search_type: Type of search (pubmed, linkedin, conference, etc.)
        filters: JSON object with applied filters
        results_count: Number of results returned
        results_snapshot: JSON array with result IDs (for saved searches)
        is_saved: Whether user saved this search
        saved_name: Custom name for saved search
        created_at: When search was performed
    """

    __tablename__ = "searches"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Foreign Keys
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Search Information
    query = Column(Text, nullable=False)

    search_type = Column(String(50), nullable=False, index=True)
    # Types: pubmed, linkedin, conference, funding, google_scholar, custom

    # Filters applied to this search
    filters = Column(JSONB, default=dict, nullable=False)
    # Example: {
    #   "location": "Cambridge, MA",
    #   "min_score": 70,
    #   "publication_years": [2023, 2024],
    #   "funding_stages": ["Series A", "Series B"],
    #   "keywords": ["toxicology", "3D models"]
    # }

    # Results
    results_count = Column(Integer, default=0, nullable=False)

    results_snapshot = Column(JSONB, default=list, nullable=False)
    # Array of lead IDs that were returned
    # Example: ["uuid1", "uuid2", "uuid3"]

    # Saved Searches
    is_saved = Column(Boolean, default=False, nullable=False, index=True)
    saved_name = Column(String(255), nullable=True)

    # Execution metadata
    execution_time_ms = Column(Integer, nullable=True)  # How long search took

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="searches")

    def __repr__(self):
        return f"<Search(id={self.id}, type={self.search_type}, query={self.query[:50]}, results={self.results_count})>"

    # Helper Methods
    def get_filter(self, key: str, default=None):
        """
        Get a specific filter value
        """
        return self.filters.get(key, default)

    def set_filter(self, key: str, value):
        """
        Set a filter value
        """
        if not self.filters:
            self.filters = {}

        self.filters[key] = value

    def save_search(self, name: str):
        """
        Mark search as saved with a custom name
        """
        self.is_saved = True
        self.saved_name = name

    def to_dict(self) -> dict:
        """
        Convert search to dictionary
        """
        return {
            "id": str(self.id),
            "query": self.query,
            "search_type": self.search_type,
            "filters": self.filters,
            "results_count": self.results_count,
            "is_saved": self.is_saved,
            "saved_name": self.saved_name,
            "execution_time_ms": self.execution_time_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


from sqlalchemy import Boolean
