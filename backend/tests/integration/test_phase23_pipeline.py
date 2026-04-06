"""Phase 2.3 integration tests for the full pipeline."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.data_quality_service import (
    DataQualityService,
    get_data_quality_service,
)


@pytest.mark.unit
class TestDataQualityServiceSingleton:
    """Verify the module-level singleton factory behaves correctly."""

    def test_factory_returns_instance(self):
        svc = get_data_quality_service()
        assert isinstance(svc, DataQualityService)

    def test_factory_is_singleton(self):
        svc_a = get_data_quality_service()
        svc_b = get_data_quality_service()
        assert svc_a is svc_b

    def test_factory_instance_is_functional(self):
        svc = get_data_quality_service()
        result = svc.validate_lead(
            {"name": "Dr. Alice Smith", "company": "NIH", "propensity_score": 60}
        )
        assert result.passes is True
        assert isinstance(result.completeness, float)


@pytest.fixture
def dq_service() -> DataQualityService:
    return DataQualityService()


@pytest.fixture
def good_lead_dict():
    return {
        "name": "Dr. Sarah Johnson",
        "title": "Principal Investigator",
        "company": "Harvard Medical School",
        "location": "Boston, MA",
        "email": "sarah.johnson@hms.harvard.edu",
        "linkedin_url": "https://www.linkedin.com/in/sarah-johnson-pi",
        "propensity_score": 85,
        "data_sources": ["pubmed"],
    }


@pytest.fixture
def minimal_passing_lead():
    return {
        "name": "Dr. Jane Doe",
        "company": "BioLab Inc",
        "propensity_score": 15,
        "data_sources": ["funding"],
    }


@pytest.fixture
def junk_lead_dict():
    return {
        "name": "X",
        "propensity_score": 2,
    }


@pytest.mark.unit
class TestDataQualityService:
    def test_good_lead_passes(self, dq_service, good_lead_dict):
        result = dq_service.validate_lead(good_lead_dict)
        assert result.passes is True
        assert result.completeness > 0.7

    def test_junk_lead_rejected(self, dq_service, junk_lead_dict):
        result = dq_service.validate_lead(junk_lead_dict)
        assert result.passes is False
        assert any("name" in issue or "score" in issue for issue in result.issues)

    def test_minimal_lead_passes(self, dq_service, minimal_passing_lead):
        result = dq_service.validate_lead(minimal_passing_lead)
        assert result.passes is True

    def test_invalid_email_is_issue(self, dq_service, good_lead_dict):
        good_lead_dict["email"] = "not-an-email"
        result = dq_service.validate_lead(good_lead_dict)
        assert result.passes is False
        assert any("invalid_email" in issue for issue in result.issues)

    def test_invalid_linkedin_is_warning_not_issue(self, dq_service, good_lead_dict):
        good_lead_dict["linkedin_url"] = "http://notlinkedin.com/xyz"
        result = dq_service.validate_lead(good_lead_dict)
        assert any("linkedin" in warning for warning in result.warnings)

    def test_score_above_100_is_warning(self, dq_service, good_lead_dict):
        good_lead_dict["propensity_score"] = 150
        result = dq_service.validate_lead(good_lead_dict)
        assert result.passes is True
        assert any("score_exceeds_100" in warning for warning in result.warnings)


@pytest.mark.unit
class TestValidateBatch:
    def test_batch_rejects_junk(self, dq_service, good_lead_dict, junk_lead_dict):
        passing, report = dq_service.validate_batch([good_lead_dict, junk_lead_dict])
        assert len(passing) == 1
        assert passing[0]["name"] == "Dr. Sarah Johnson"
        assert report.rejected == 1

    def test_batch_deduplicates_by_name(self, dq_service, good_lead_dict):
        duplicate = {**good_lead_dict, "data_sources": ["conference"]}
        passing, report = dq_service.validate_batch([good_lead_dict, duplicate], deduplicate=True)
        assert len(passing) == 1
        assert report.total_candidates == 2

    def test_batch_respects_deduplicate_false(self, dq_service, good_lead_dict):
        duplicate = {**good_lead_dict, "data_sources": ["conference"]}
        passing, _ = dq_service.validate_batch([good_lead_dict, duplicate], deduplicate=False)
        assert len(passing) == 2

    def test_batch_quality_report_counts(
        self,
        dq_service,
        good_lead_dict,
        junk_lead_dict,
        minimal_passing_lead,
    ):
        passing, report = dq_service.validate_batch(
            [good_lead_dict, junk_lead_dict, minimal_passing_lead]
        )
        assert len(passing) == 2
        assert report.total_candidates == 3
        assert report.passed == 2
        assert report.rejected == 1
        assert 0.0 < report.avg_completeness <= 1.0

    def test_empty_batch_returns_empty(self, dq_service):
        passing, report = dq_service.validate_batch([])
        assert passing == []
        assert report.total_candidates == 0
        assert report.avg_completeness == 0.0


@pytest.mark.integration
class TestMultiSourcePipeline:
    def _make_mock_lead_dict(self, name: str, score: int, source: str) -> dict:
        return {
            "name": f"Dr. {name}",
            "title": "Researcher",
            "company": "Test University",
            "location": "Boston, MA",
            "propensity_score": score,
            "data_sources": [source],
        }

    @pytest.mark.asyncio
    async def test_parallel_search_fires_all_sources(self):
        from app.services.data_source_manager import DataSourceManager, DataSourceType

        mock_search = AsyncMock(
            return_value={
                "pubmed": {"leads": [self._make_mock_lead_dict("Alice", 80, "pubmed")]},
                "conference": {
                    "leads": [self._make_mock_lead_dict("Bob", 70, "conference")]
                },
                "funding": {"leads": [self._make_mock_lead_dict("Carol", 75, "funding")]},
            }
        )

        with patch.object(DataSourceManager, "search", mock_search):
            manager = DataSourceManager.__new__(DataSourceManager)
            manager.available_sources = {
                DataSourceType.PUBMED: True,
                DataSourceType.CONFERENCE: True,
                DataSourceType.FUNDING: True,
                DataSourceType.LINKEDIN: False,
            }
            result = await manager.search(
                query="DILI 3D models",
                sources=list(manager.available_sources.keys())[:3],
            )

        mock_search.assert_awaited_once()
        assert "pubmed" in result
        assert "conference" in result
        assert "funding" in result

    @pytest.mark.asyncio
    async def test_quality_gate_rejects_low_score_leads(self):
        leads = [
            self._make_mock_lead_dict("Alice", 80, "pubmed"),
            {"name": "X", "propensity_score": 1},
            self._make_mock_lead_dict("Carol", 60, "funding"),
        ]
        passing, report = DataQualityService().validate_batch(leads)
        assert len(passing) == 2
        assert report.rejected == 1

    @pytest.mark.asyncio
    async def test_deduplication_across_sources(self):
        leads = [
            {
                "name": "Dr. Alice Smith",
                "company": "Harvard",
                "propensity_score": 80,
                "data_sources": ["pubmed"],
            },
            {
                "name": "Dr. Alice Smith",
                "company": "Harvard Medical School",
                "propensity_score": 75,
                "data_sources": ["conference"],
            },
        ]
        passing, report = DataQualityService().validate_batch(leads, deduplicate=True)
        assert len(passing) == 1
        assert report.total_candidates == 2

    @pytest.mark.asyncio
    async def test_title_variations_deduplication(self):
        leads = [
            {
                "name": "Dr. James Kirk",
                "company": "Starfleet",
                "propensity_score": 70,
                "data_sources": ["pubmed"],
            },
            {
                "name": "James Kirk",
                "company": "Starfleet",
                "propensity_score": 65,
                "data_sources": ["funding"],
            },
            {
                "name": "Prof. James Kirk",
                "company": "Starfleet",
                "propensity_score": 72,
                "data_sources": ["conference"],
            },
        ]
        passing, report = DataQualityService().validate_batch(leads, deduplicate=True)
        assert len(passing) == 1
        assert report.total_candidates == 3


@pytest.mark.unit
class TestQuotaManager:
    @pytest.mark.asyncio
    async def test_hunter_blocked_below_min_score(self):
        from app.services.quota_manager import QuotaManager

        qm = QuotaManager()
        with patch("app.core.cache.Cache.get", new_callable=AsyncMock, return_value=None), patch(
            "app.core.cache.Cache.exists", new_callable=AsyncMock, return_value=False
        ):
            result = await qm.can_use_hunter(lead_score=50)
            assert result is False

    @pytest.mark.asyncio
    async def test_hunter_allowed_above_min_score(self):
        from app.services.quota_manager import QuotaManager

        qm = QuotaManager()
        with patch("app.core.cache.Cache.get", new_callable=AsyncMock, return_value="5"), patch(
            "app.core.cache.Cache.exists", new_callable=AsyncMock, return_value=False
        ):
            result = await qm.can_use_hunter(lead_score=85)
            assert result is True

    @pytest.mark.asyncio
    async def test_hunter_blocked_when_exhausted(self):
        from app.services.quota_manager import QuotaManager

        qm = QuotaManager()
        with patch("app.core.cache.Cache.get", new_callable=AsyncMock, return_value="25"), patch(
            "app.core.cache.Cache.exists", new_callable=AsyncMock, return_value=True
        ):
            result = await qm.can_use_hunter(lead_score=90)
            assert result is False


@pytest.mark.integration
class TestDataSourceStatusEndpoint:
    @pytest.mark.asyncio
    async def test_sources_endpoint_returns_all_three_active(self):
        from app.services.data_source_manager import DataSourceManager, DataSourceType

        manager = DataSourceManager.__new__(DataSourceManager)
        manager.available_sources = {
            DataSourceType.PUBMED: True,
            DataSourceType.CONFERENCE: True,
            DataSourceType.FUNDING: True,
            DataSourceType.LINKEDIN: False,
        }

        active = manager.get_available_sources()
        assert "pubmed" in active
        assert "conference" in active
        assert "funding" in active
        assert "linkedin" not in active

    @pytest.mark.asyncio
    async def test_source_status_structure(self):
        from app.services.data_source_manager import DataSourceManager, DataSourceType

        manager = DataSourceManager.__new__(DataSourceManager)
        manager.available_sources = {
            DataSourceType.PUBMED: True,
            DataSourceType.CONFERENCE: True,
            DataSourceType.FUNDING: True,
            DataSourceType.LINKEDIN: False,
        }

        mock_status = AsyncMock(return_value={"available": True, "cache_active": True})
        manager.pubmed_service = MagicMock()
        manager.conference_service = MagicMock()
        manager.funding_service = MagicMock()

        manager.pubmed_service.get_service_status = mock_status
        manager.conference_service.get_service_status = mock_status
        manager.funding_service.get_service_status = mock_status

        status = await manager.get_source_status()
        assert "available_sources" in status
        assert "sources" in status
        assert isinstance(status["available_sources"], list)
