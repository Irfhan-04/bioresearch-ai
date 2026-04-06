"""
Model Unit Tests
Test model methods, properties, and relationships
"""

import pytest
from datetime import datetime, timedelta, timezone

from app.models.lead import Lead
from app.models.user import User, SubscriptionTier
from app.models.pipeline import Pipeline, PipelineStatus, PipelineSchedule
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
        assert user.subscription_tier == SubscriptionTier.FREE

    def test_get_monthly_lead_limit(self):
        """Test getting monthly lead limit"""
        free_user = User(email="free@example.com", password_hash="hash")
        assert free_user.get_monthly_lead_limit() == 100

        pro_user = User(
            email="pro@example.com",
            password_hash="hash",
            subscription_tier=SubscriptionTier.PRO,
        )
        assert pro_user.get_monthly_lead_limit() == 1000

    def test_has_reached_lead_limit(self):
        """Test checking lead limit"""
        user = User(email="test@example.com", password_hash="hash")
        user.usage_stats = {"leads_created_this_month": 50}

        assert not user.has_reached_lead_limit()

        user.usage_stats = {"leads_created_this_month": 100}
        assert user.has_reached_lead_limit()

    def test_increment_usage(self):
        """Test incrementing usage stats"""
        user = User(email="test@example.com", password_hash="hash")

        user.increment_usage("leads_created_this_month")
        assert user.usage_stats["leads_created_this_month"] == 1

        user.increment_usage("leads_created_this_month", 5)
        assert user.usage_stats["leads_created_this_month"] == 6

    def test_preferences(self):
        """Test user preferences"""
        user = User(email="test@example.com", password_hash="hash")

        user.set_preference("theme", "dark")
        assert user.get_preference("theme") == "dark"
        assert user.get_preference("nonexistent", "default") == "default"


@pytest.mark.unit
class TestLeadModel:
    """Test Lead model"""

    def test_lead_creation(self):
        """Test creating lead"""
        lead = Lead(
            user_id="user_id",
            name="Dr. Test",
            title="Scientist",
            company="Test Corp",
            status="NEW",
        )

        assert lead.name == "Dr. Test"
        assert lead.status == "NEW"

    def test_priority_tier_calculation(self):
        """Test priority tier calculation"""
        lead = Lead(user_id="user_id", name="Test", title="Scientist", status="NEW")

        lead.propensity_score = 95
        assert lead.get_priority_tier() == "HIGH"

        lead.propensity_score = 60
        assert lead.get_priority_tier() == "MEDIUM"

        lead.propensity_score = 30
        assert lead.get_priority_tier() == "LOW"

    def test_update_priority_tier(self):
        """Test updating priority tier"""
        lead = Lead(user_id="user_id", name="Test", title="Scientist", status="NEW")

        lead.propensity_score = 85
        lead.update_priority_tier()
        assert lead.priority_tier == "HIGH"

    def test_add_tag(self):
        """Test adding tags"""
        lead = Lead(user_id="user_id", name="Test", title="Scientist", status="NEW")

        lead.add_tag("high-priority")
        assert "high-priority" in lead.tags

        # Don't add duplicate
        lead.add_tag("high-priority")
        assert lead.tags.count("high-priority") == 1

    def test_data_source_management(self):
        """Test data source management"""
        lead = Lead(user_id="user_id", name="Test", title="Scientist", status="NEW")

        lead.add_data_source("pubmed")
        lead.add_data_source("linkedin")

        assert "pubmed" in lead.data_sources
        assert "linkedin" in lead.data_sources

    def test_enrichment_data(self):
        """Test enrichment data"""
        lead = Lead(user_id="user_id", name="Test", title="Scientist", status="NEW")

        lead.set_enrichment("email", {"email": "test@example.com", "confidence": 0.9})
        enrichment = lead.get_enrichment("email")

        assert enrichment["email"] == "test@example.com"

    def test_custom_fields(self):
        """Test custom fields"""
        lead = Lead(user_id="user_id", name="Test", title="Scientist", status="NEW")

        lead.set_custom_field("budget", "$50k")
        assert lead.get_custom_field("budget") == "$50k"


@pytest.mark.unit
class TestPipelineModel:
    """Test Pipeline model"""

    def test_pipeline_creation(self):
        """Test creating pipeline"""
        pipeline = Pipeline(
            user_id="user_id",
            name="Test Pipeline",
            schedule=PipelineSchedule.DAILY,
            config={"search_queries": []},
            status=PipelineStatus.ACTIVE,
        )

        assert pipeline.name == "Test Pipeline"
        assert pipeline.status == PipelineStatus.ACTIVE

    def test_calculate_next_run(self):
        """Test calculating next run time"""
        pipeline = Pipeline(
            user_id="user_id",
            name="Test",
            schedule=PipelineSchedule.DAILY,
            config={},
            status=PipelineStatus.ACTIVE,
        )

        next_run = pipeline.calculate_next_run()
        assert next_run is not None
        assert next_run > datetime.now(timezone.utc)

    def test_get_success_rate(self):
        """Test success rate calculation"""
        pipeline = Pipeline(
            user_id="user_id",
            name="Test",
            schedule=PipelineSchedule.MANUAL,
            config={},
            status=PipelineStatus.ACTIVE,
        )

        pipeline.run_count = 10
        pipeline.success_count = 8

        assert pipeline.get_success_rate() == 80.0

    def test_activate_pause_disable(self):
        """Test pipeline status changes"""
        pipeline = Pipeline(
            user_id="user_id",
            name="Test",
            schedule=PipelineSchedule.MANUAL,
            config={},
            status=PipelineStatus.PAUSED,
        )

        pipeline.activate()
        assert pipeline.status == PipelineStatus.ACTIVE

        pipeline.pause()
        assert pipeline.status == PipelineStatus.PAUSED

        pipeline.disable()
        assert pipeline.status == PipelineStatus.DISABLED


@pytest.mark.unit
class TestExportModel:
    """Test Export model"""

    def test_export_creation(self):
        """Test creating export"""
        export = Export(
            user_id="user_id",
            file_name="test.csv",
            format=ExportFormat.CSV,
            status=ExportStatus.PENDING,
        )

        assert export.file_name == "test.csv"
        assert export.status == ExportStatus.PENDING

    def test_is_downloadable(self):
        """Test is downloadable check"""
        export = Export(
            user_id="user_id",
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
            user_id="user_id",
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
            user_id="user_id",
            file_name="test.csv",
            format=ExportFormat.CSV,
            status=ExportStatus.COMPLETED,
        )

        export.file_size_bytes = 1024 * 1024 * 2  # 2MB
        assert export.get_file_size_mb() == 2.0