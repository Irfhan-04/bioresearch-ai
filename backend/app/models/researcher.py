"""
Researcher Model — Core entity for BioResearch AI.

Represents a biotech researcher discovered from PubMed, NIH funding records,
or conference databases. Stores identity, contact discovery metadata, ML
relevance scoring (Component 1), semantic embedding metadata (Component 2),
LLM intelligence output (Component 3), and SHAP feature contributions (Component 4).
"""

import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Researcher(Base):
    """
    Researcher model representing a biotech scientist discovered via PubMed,
    NIH funding records, or conference data.

    Attributes:
        id: Unique researcher identifier
        user_id: Owner of this researcher record (foreign key to users)
        name: Full name of the researcher
        title: Academic/professional title (Professor, PI, Research Scientist, etc.)
        company: Institution or organisation name
        location: Researcher location
        company_hq: Institution headquarters location

        email: Contact email (discovered by contact_service)
        phone: Contact phone number
        linkedin_url: LinkedIn profile URL
        twitter_url: Twitter/X profile URL
        website: Personal or institutional website

        relevance_score: ML-predicted relevance score (0–100) from RandomForest
        rank: Relative ranking among all researchers
        relevance_tier: HIGH, MEDIUM, or LOW (predicted class from ML model)
        relevance_confidence: Model probability for predicted tier
        shap_contributions: Top 5 SHAP feature contributions (drives ScoreExplanationCard)

        abstract_text: Raw PubMed abstract — source for embedding_service
        abstract_embedding_id: ChromaDB document ID for this researcher
        abstract_relevance_score: Cosine sim vs default biotech query, stored at
            enrichment time. Used as ML feature 12 (abstract semantic relevance).
            NOT the per-query semantic score computed at search time.
        research_area: Output of research_area_classifier.py
        domain_coverage_score: Domain keyword coverage across title + abstract (ML feature 11)

        intelligence: Structured JSON from intelligence_service (Gemini 2.0 Flash)
        intelligence_generated_at: Timestamp for Redis cache invalidation

        contact_confidence: Confidence of contact discovery (0–1)

        recent_publication: Whether published in last 2 years
        publication_year: Most recent publication year
        publication_title: Title of most recent publication
        publication_count: Total number of publications

        data_sources: JSON array of data source identifiers
        enrichment_data: JSON object with enrichment results
        custom_fields: JSON object for user-defined fields
        tags: Array of user-defined tags
        notes: Internal notes
        status: Profile status (NEW, REVIEWING, NOTED, CONTACTED, ARCHIVED)

        created_at: When researcher was added
        updated_at: Last update timestamp
    """

    __tablename__ = "researchers"

    # ── Primary key ───────────────────────────────────────────────────────────
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # ── Foreign keys ─────────────────────────────────────────────────────────
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assigned_to = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── Identity ──────────────────────────────────────────────────────────────
    name = Column(String(255), nullable=False, index=True)
    title = Column(String(255), nullable=True, index=True)
    company = Column(String(255), nullable=True, index=True)
    location = Column(String(255), nullable=True)
    company_hq = Column(String(255), nullable=True)

    # ── Contact ───────────────────────────────────────────────────────────────
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    twitter_url = Column(String(500), nullable=True)
    website = Column(String(500), nullable=True)

    # ── ML Relevance Scoring — Components 1 + 4 ───────────────────────────────
    relevance_score = Column(
        Integer,
        nullable=True,
        index=True,
        comment="0–100 score from RandomForest classifier",
    )
    rank = Column(Integer, nullable=True, index=True)
    relevance_tier = Column(
        String(20),
        nullable=True,
        comment="HIGH / MEDIUM / LOW — predicted class from ML model",
    )
    relevance_confidence = Column(
        Float, nullable=True, comment="Model probability for predicted tier"
    )
    shap_contributions = Column(
        JSONB,
        nullable=True,
        comment="Top 5 SHAP feature contributions — drives ScoreExplanationCard UI",
    )

    # ── Semantic Embeddings — Component 2 ─────────────────────────────────────
    abstract_text = Column(
        Text,
        nullable=True,
        comment="Raw PubMed abstract — source for embedding_service",
    )
    abstract_embedding_id = Column(
        String(255), nullable=True, comment="ChromaDB document ID for this researcher"
    )
    abstract_relevance_score = Column(
        Float,
        nullable=True,
        comment=(
            "Cosine similarity vs default biotech query, stored at enrichment time. "
            "Used as ML feature 12. NOT the per-query semantic score."
        ),
    )

    # ── Research Area Classifier — Component 2 dependency ─────────────────────
    research_area = Column(
        String(100),
        nullable=True,
        comment=(
            "Output of research_area_classifier.py: "
            "toxicology / drug_safety / drug_discovery / "
            "preclinical / organoids / in_vitro / biomarkers / general_biotech"
        ),
    )
    domain_coverage_score = Column(
        Float,
        nullable=True,
        comment="Domain keyword coverage across title + abstract — ML feature 11",
    )

    # ── LLM Intelligence — Component 3 (Gemini 2.0 Flash) ────────────────────
    intelligence = Column(
        JSONB,
        nullable=True,
        comment=(
            "Structured JSON from intelligence_service: "
            "research_summary, domain_significance, research_connections, "
            "key_topics, research_area_tags, activity_level, data_gaps"
        ),
    )
    intelligence_generated_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp for Redis cache invalidation",
    )

    # ── Contact discovery ─────────────────────────────────────────────────────
    contact_confidence = Column(
        Float, nullable=True, comment="Confidence of contact discovery (0–1)"
    )

    # ── Publication metadata (PubMed) ─────────────────────────────────────────
    recent_publication = Column(Boolean, default=False)
    publication_year = Column(Integer, nullable=True)
    publication_title = Column(Text, nullable=True)
    publication_count = Column(Integer, default=0)

    # ── Institution ───────────────────────────────────────────────────────────
    company_funding = Column(String(50), nullable=True)
    company_size = Column(String(50), nullable=True)
    uses_3d_models = Column(Boolean, default=False)

    # ── Enrichment metadata ───────────────────────────────────────────────────
    data_sources = Column(
        JSONB,
        default=list,
        nullable=False,
        comment='Array of source identifiers e.g. ["pubmed", "hunter.io"]',
    )
    enrichment_data = Column(JSONB, default=dict, nullable=False)
    custom_fields = Column(JSONB, default=dict, nullable=False)
    tags = Column(JSONB, default=list, nullable=False)
    notes = Column(Text, nullable=True)
    status = Column(
        String(50),
        default="NEW",
        nullable=False,
        index=True,
        comment="NEW / REVIEWING / NOTED / CONTACTED / ARCHIVED",
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
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

    # ── Relationships ─────────────────────────────────────────────────────────
    user = relationship("User", back_populates="researchers", foreign_keys=[user_id])
    assignee = relationship("User", foreign_keys=[assigned_to])

    __table_args__ = ()

    def __repr__(self):
        return f"<Researcher(id={self.id}, name={self.name}, score={self.relevance_score})>"

    # ── Helper methods ────────────────────────────────────────────────────────

    def get_relevance_tier(self) -> str:
        """Return relevance tier based on current score."""
        if self.relevance_score is None:
            return "UNSCORED"
        if self.relevance_score >= 70:
            return "HIGH"
        elif self.relevance_score >= 50:
            return "MEDIUM"
        return "LOW"

    def update_relevance_tier(self):
        """Sync relevance_tier column with current score."""
        self.relevance_tier = self.get_relevance_tier()

    def add_tag(self, tag: str):
        if not self.tags:
            self.tags = []
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str):
        if self.tags and tag in self.tags:
            self.tags.remove(tag)

    def has_tag(self, tag: str) -> bool:
        return tag in (self.tags or [])

    def add_data_source(self, source: str):
        if not self.data_sources:
            self.data_sources = []
        if source not in self.data_sources:
            self.data_sources.append(source)

    def get_enrichment(self, enrichment_type: str):
        return self.enrichment_data.get(enrichment_type)

    def set_enrichment(self, enrichment_type: str, data: dict):
        if not self.enrichment_data:
            self.enrichment_data = {}
        self.enrichment_data[enrichment_type] = data

    def set_custom_field(self, key: str, value):
        """Set a user-defined custom field on the researcher."""
        if not self.custom_fields:
            self.custom_fields = {}
        self.custom_fields[key] = value

    def get_custom_field(self, key: str, default=None):
        """Get a user-defined custom field value or `default` if missing."""
        if not self.custom_fields:
            return default
        return self.custom_fields.get(key, default)

    def to_dict(self) -> dict:
        """Convert researcher to dict (used for CSV exports)."""
        return {
            "id": str(self.id),
            "name": self.name,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "email": self.email,
            "linkedin_url": self.linkedin_url,
            "relevance_score": self.relevance_score,
            "relevance_tier": self.relevance_tier,
            "research_area": self.research_area,
            "recent_publication": self.recent_publication,
            "publication_title": self.publication_title,
            "publication_year": self.publication_year,
            "publication_count": self.publication_count,
            "tags": self.tags,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
