"""
Model Unit Tests
Test model methods, properties, and relationships
"""

import pytest
from datetime import datetime, timedelta, timezone

# FIX: Lead does not exist — the entity is called Researcher.
from app.models.researcher import Researcher
from app.models.user import User
# FIX: Pipeline / PipelineStatus / PipelineSchedule do not exist in this codebase.
#      The TestPipelineModel class has been removed entirely.
from app.models.export import Export, ExportStatus, ExportFormat


@pytest.mark.unit
class TestUserModel:
    """Test User model"""

    def test_user_creation(self):
        """Test creating user"""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
            full_name="Test User",
        )

        assert user.email == "test@example.com"


    def test_increment_usage(self):
        """Test incrementing usage stats"""
        user = User(email="test@example.com", password_hash="hash")

        user.increment_usage("searches_this_month")
        assert user.usage_stats["searches_this_month"] == 1

        user.increment_usage("searches_this_month", 5)
        assert user.usage_stats["searches_this_month"] == 6

    def test_preferences(self):
        """Test user preferences"""
        user = User(email="test@example.com", password_hash="hash")

        user.set_preference("theme", "dark")
        assert user.get_preference("theme") == "dark"
        assert user.get_preference("nonexistent", "default") == "default"


@pytest.mark.unit
class TestResearcherModel:
    """Test Researcher model (replaces the old TestLeadModel)"""

    def test_researcher_creation(self):
        """Test creating researcher"""
        researcher = Researcher(
            user_id="00000000-0000-0000-0000-000000000001",
            name="Dr. Test",
            title="Scientist",
            company="Test Corp",
            status="NEW",
        )

        assert researcher.name == "Dr. Test"
        assert researcher.status == "NEW"

    def test_relevance_tier_calculation(self):
        """Test relevance tier calculation.
        Thresholds: HIGH >= 70, MEDIUM >= 50, LOW < 50
        """
        researcher = Researcher(
            user_id="00000000-0000-0000-0000-000000000001",
            name="Test",
            title="Scientist",
            status="NEW",
        )

        researcher.relevance_score = 95
        assert researcher.get_relevance_tier() == "HIGH"

        researcher.relevance_score = 60
        assert researcher.get_relevance_tier() == "MEDIUM"

        researcher.relevance_score = 30
        assert researcher.get_relevance_tier() == "LOW"

    def test_update_relevance_tier(self):
        """Test updating relevance_tier field from current score"""
        researcher = Researcher(
            user_id="00000000-0000-0000-0000-000000000001",
            name="Test",
            title="Scientist",
            status="NEW",
        )

        researcher.relevance_score = 85
        researcher.update_relevance_tier()
        assert researcher.relevance_tier == "HIGH"

    def test_add_tag(self):
        """Test adding tags"""
        researcher = Researcher(
            user_id="00000000-0000-0000-0000-000000000001",
            name="Test",
            title="Scientist",
            status="NEW",
        )
        researcher.tags = []

        researcher.add_tag("high-priority")
        assert "high-priority" in researcher.tags

        # Duplicate should not be added
        researcher.add_tag("high-priority")
        assert researcher.tags.count("high-priority") == 1

    def test_data_source_management(self):
        """Test data source management"""
        researcher = Researcher(
            user_id="00000000-0000-0000-0000-000000000001",
            name="Test",
            title="Scientist",
            status="NEW",
        )
        researcher.data_sources = []

        researcher.add_data_source("pubmed")
        researcher.add_data_source("linkedin")

        assert "pubmed" in researcher.data_sources
        assert "linkedin" in researcher.data_sources

    def test_enrichment_data(self):
        """Test enrichment data get/set"""
        researcher = Researcher(
            user_id="00000000-0000-0000-0000-000000000001",
            name="Test",
            title="Scientist",
            status="NEW",
        )
        researcher.enrichment_data = {}

        researcher.set_enrichment("email", {"email": "test@example.com", "confidence": 0.9})
        enrichment = researcher.get_enrichment("email")

        assert enrichment["email"] == "test@example.com"

    def test_custom_fields(self):
        """Test custom fields get/set"""
        researcher = Researcher(
            user_id="00000000-0000-0000-0000-000000000001",
            name="Test",
            title="Scientist",
            status="NEW",
        )
        researcher.custom_fields = {}

        researcher.set_custom_field("budget", "$50k")
        assert researcher.get_custom_field("budget") == "$50k"


# NOTE: TestPipelineModel removed — Pipeline / PipelineStatus / PipelineSchedule
# do not exist in this codebase. Add these tests once the Pipeline model is
# implemented (planned for a later phase).


@pytest.mark.unit
class TestExportModel:
    """Test Export model"""

    def test_export_creation(self):
        """Test creating export"""
        export = Export(
            user_id="00000000-0000-0000-0000-000000000001",
            file_name="test.csv",
            format=ExportFormat.CSV,
            status=ExportStatus.PENDING,
        )

        assert export.file_name == "test.csv"
        assert export.status == ExportStatus.PENDING

    def test_is_downloadable(self):
        """Test is_downloadable check"""
        export = Export(
            user_id="00000000-0000-0000-0000-000000000001",
            file_name="test.csv",
            format=ExportFormat.CSV,
            status=ExportStatus.COMPLETED,
        )

        export.file_url = "https://example.com/file.csv"
        export.expires_at = datetime.now(timezone.utc) + timedelta(days=1)

        assert export.is_downloadable() is True

    def test_is_expired(self):
        """Test expiration check"""
        export = Export(
            user_id="00000000-0000-0000-0000-000000000001",
            file_name="test.csv",
            format=ExportFormat.CSV,
            status=ExportStatus.COMPLETED,
        )

        export.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        assert export.is_expired() is True

        export.expires_at = datetime.now(timezone.utc) + timedelta(days=1)
        assert export.is_expired() is False

    def test_get_file_size_mb(self):
        """Test file size calculation"""
        export = Export(
            user_id="00000000-0000-0000-0000-000000000001",
            file_name="test.csv",
            format=ExportFormat.CSV,
            status=ExportStatus.COMPLETED,
        )

        export.file_size_bytes = 1024 * 1024 * 2  # 2 MB
        assert export.get_file_size_mb() == 2.0