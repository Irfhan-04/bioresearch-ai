"""
Researcher Model - The core entity representing potential customers
"""

import uuid

from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey, Integer,
                        String, Text)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Researcher(Base):
    """
    Researcher model representing potential customers

    Attributes:
        id: Unique researcher identifier
        user_id: Owner of this researcher (foreign key to users)
        name: Full name of the researcher
        title: Job title
        company: Company name
        location: Personal location (could be remote)
        company_hq: Company headquarters location
        email: Contact email
        phone: Contact phone number
        linkedin_url: LinkedIn profile URL
        twitter_url: Twitter/X profile URL
        website: Personal or company website

        relevance_score: Calculated score (0-100)
        rank: Relative ranking among all researchers
        relevance_tier: HIGH, MEDIUM, or LOW

        recent_publication: Whether they published recently
        publication_year: Most recent publication year
        publication_title: Title of most recent publication
        publication_count: Total number of publications

        company_funding: Funding stage (Seed, Series A, etc.)
        company_size: Company size category
        uses_3d_models: Whether they use 3D in-vitro models

        data_sources: JSON array of where data came from
        enrichment_data: JSON object with enrichment results
        custom_fields: JSON object for user-defined fields

        tags: Array of user-defined tags
        notes: Internal notes
        status: Researcher status (NEW, CONTACTED, QUALIFIED, etc.)

        last_contacted_at: When researcher was last contacted
        created_at: When researcher was added
        updated_at: Last update timestamp
    """

    __tablename__ = "researchers"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Foreign Keys
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    team_id = Column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    assigned_to = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Basic Information
    name = Column(String(255), nullable=False, index=True)
    title = Column(String(255), nullable=True, index=True)
    company = Column(String(255), nullable=True, index=True)

    # Location
    location = Column(String(255), nullable=True)
    company_hq = Column(String(255), nullable=True)

    # Contact Information
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    twitter_url = Column(String(500), nullable=True)
    website = Column(String(500), nullable=True)

    # Scoring
    relevance_score = Column(Integer, nullable=True, index=True)
    rank = Column(Integer, nullable=True, index=True)
    relevance_tier = Column(String(20), nullable=True)  # HIGH, MEDIUM, LOW



    # AI / ML Intelligence fields
    abstract_text = Column(Text, nullable=True, comment="Raw PubMed abstract for embedding")
    abstract_embedding_id = Column(String(255), nullable=True, comment="ChromaDB document ID")
    abstract_relevance_score = Column(Float, nullable=True, comment="Cosine sim vs default biotech query")
    research_area = Column(String(100), nullable=True, comment="Classifier output")
    domain_coverage_score = Column(Float, nullable=True, comment="Domain keyword coverage — ML feature 11")
    relevance_confidence = Column(Float, nullable=True, comment="Model probability for predicted tier")
    shap_contributions = Column(JSONB, nullable=True, comment="Top 5 SHAP explanations")
    intelligence = Column(JSONB, nullable=True, comment="LLM research intelligence output")
    intelligence_generated_at = Column(DateTime(timezone=True), nullable=True)
    contact_confidence = Column(Float, nullable=True, comment="Contact discovery confidence")

    # Publication Information
    recent_publication = Column(Boolean, default=False)
    publication_year = Column(Integer, nullable=True)
    publication_title = Column(Text, nullable=True)
    publication_count = Column(Integer, default=0)

    # Company Information
    company_funding = Column(String(50), nullable=True)  # Seed, Series A, B, C, Public
    company_size = Column(String(50), nullable=True)  # 1-10, 11-50, 51-200, etc.
    uses_3d_models = Column(Boolean, default=False)

    # Data Sources & Enrichment
    data_sources = Column(JSONB, default=list, nullable=False)
    # Example: ["pubmed", "linkedin", "hunter.io"]

    enrichment_data = Column(JSONB, default=dict, nullable=False)
    # Example: {
    #   "email_verified": true,
    #   "company_data": {...},
    #   "social_profiles": {...},
    #   "funding_history": [...]
    # }

    # Custom Fields (user-defined)
    custom_fields = Column(JSONB, default=dict, nullable=False)
    # Example: {
    #   "budget": "$50k",
    #   "interest_level": "high",
    #   "decision_maker": true
    # }

    # Organization
    tags = Column(JSONB, default=list, nullable=False)
    # Example: ["high-priority", "conference-speaker", "published-author"]

    notes = Column(Text, nullable=True)

    status = Column(String(50), default="NEW", nullable=False, index=True)
    # Status values: NEW, CONTACTED, QUALIFIED, PROPOSAL, NEGOTIATION, WON, LOST

    # Timestamps
    last_contacted_at = Column(DateTime(timezone=True), nullable=True)
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
    user = relationship("User", back_populates="researchers")
    team = relationship("Team", back_populates="researchers")
    assignee = relationship("User", foreign_keys=[assigned_to])

    # Indexes for common queries
    __table_args__ = (
        # Composite index for filtering by user and score
        # Index('ix_researchers_user_score', 'user_id', 'relevance_score'),
        # Composite index for filtering by user and status
        # Index('ix_researchers_user_status', 'user_id', 'status'),
    )

    def __repr__(self):
        return f"<Researcher(id={self.id}, name={self.name}, company={self.company}, score={self.relevance_score})>"

    # Helper Methods
    def get_relevance_tier(self) -> str:
        """
        Get priority tier based on relevance score
        """
        if self.relevance_score is None:
            return "UNSCORED"

        if self.relevance_score >= 70:
            return "HIGH"
        elif self.relevance_score >= 50:
            return "MEDIUM"
        else:
            return "LOW"

    def update_relevance_tier(self):
        """
        Update the relevance_tier field based on current score
        """
        self.relevance_tier = self.get_relevance_tier()

    def add_tag(self, tag: str):
        """
        Add a tag to the researcher
        """
        if not self.tags:
            self.tags = []

        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str):
        """
        Remove a tag from the researcher
        """
        if self.tags and tag in self.tags:
            self.tags.remove(tag)

    def has_tag(self, tag: str) -> bool:
        """
        Check if researcher has a specific tag
        """
        return tag in (self.tags or [])

    def add_data_source(self, source: str):
        """
        Add a data source to the researcher
        """
        if not self.data_sources:
            self.data_sources = []

        if source not in self.data_sources:
            self.data_sources.append(source)

    def get_enrichment(self, enrichment_type: str):
        """
        Get a specific enrichment result
        """
        return self.enrichment_data.get(enrichment_type)

    def set_enrichment(self, enrichment_type: str, data: dict):
        """
        Store enrichment data
        """
        if not self.enrichment_data:
            self.enrichment_data = {}

        self.enrichment_data[enrichment_type] = data

    def get_custom_field(self, field_name: str, default=None):
        """
        Get a custom field value
        """
        return self.custom_fields.get(field_name, default)

    def set_custom_field(self, field_name: str, value):
        """
        Set a custom field value
        """
        if not self.custom_fields:
            self.custom_fields = {}

        self.custom_fields[field_name] = value

    def to_dict(self) -> dict:
        """
        Convert researcher to dictionary (useful for exports)
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "company_hq": self.company_hq,
            "email": self.email,
            "phone": self.phone,
            "linkedin_url": self.linkedin_url,
            "relevance_score": self.relevance_score,
            "rank": self.rank,
            "relevance_tier": self.relevance_tier,
            "recent_publication": self.recent_publication,
            "publication_title": self.publication_title,
            "publication_year": self.publication_year,
            "company_funding": self.company_funding,
            "uses_3d_models": self.uses_3d_models,
            "tags": self.tags,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
