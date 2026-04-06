"""
Unit tests for LinkedInService — Phase 2.3 Step 2.
All network calls are mocked — no real HTTP requests in CI.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.linkedin_service import (
    LinkedInService,
    _extract_slug,
    _is_valid_linkedin_url,
    _name_parts,
    _normalise_linkedin_url,
    _strip_accents,
)


class TestGenerateUrlPatterns:
    def setup_method(self):
        self.svc = LinkedInService.__new__(LinkedInService)

    def test_strips_honorific(self):
        patterns = self.svc._generate_url_patterns("Dr. Sarah Chen", "Genentech")
        assert all("dr" not in p for p in patterns)
        assert all("/dr" not in p for p in patterns)

    def test_basic_pattern(self):
        patterns = self.svc._generate_url_patterns("Sarah Chen", "Genentech")
        assert "https://www.linkedin.com/in/sarah-chen" in patterns

    def test_middle_initial(self):
        patterns = self.svc._generate_url_patterns("Sarah E. Chen", "Genentech")
        assert any("sarah-e-chen" in p for p in patterns)

    def test_returns_max_seven(self):
        patterns = self.svc._generate_url_patterns(
            "James Alexander Robertson", "Big Pharma Inc"
        )
        assert len(patterns) <= 7

    def test_empty_name_returns_empty(self):
        patterns = self.svc._generate_url_patterns("", "Company")
        assert patterns == []

    def test_strips_prof_honorific(self):
        patterns = self.svc._generate_url_patterns("Prof. John Smith", "MIT")
        assert all("prof" not in p for p in patterns)

    def test_accent_normalisation(self):
        patterns = self.svc._generate_url_patterns("José García", "Roche")
        assert any("jose" in p for p in patterns)


class TestIsValidLinkedInUrl:
    def test_valid_url(self):
        assert _is_valid_linkedin_url("https://www.linkedin.com/in/sarah-chen")
        assert _is_valid_linkedin_url("https://linkedin.com/in/john-doe-42")

    def test_rejects_company_url(self):
        assert not _is_valid_linkedin_url("https://linkedin.com/company/genentech")

    def test_rejects_too_short_slug(self):
        assert not _is_valid_linkedin_url("https://linkedin.com/in/ab")

    def test_rejects_non_linkedin(self):
        assert not _is_valid_linkedin_url("https://twitter.com/sarahchen")

    def test_rejects_empty_string(self):
        assert not _is_valid_linkedin_url("")

    def test_valid_slug_with_numbers(self):
        assert _is_valid_linkedin_url("https://www.linkedin.com/in/sarah-chen-3b7a2")


class TestNameParts:
    def test_first_and_last(self):
        parts = _name_parts("Sarah Chen")
        assert parts["first"] == "sarah"
        assert parts["last"] == "chen"

    def test_strips_title(self):
        parts = _name_parts("Dr. Sarah Chen")
        assert parts["first"] == "sarah"

    def test_single_name(self):
        parts = _name_parts("Chen")
        assert parts["first"] == "chen"
        assert parts["last"] == ""

    def test_strips_phd(self):
        parts = _name_parts("Sarah Chen PhD")
        assert parts["first"] == "sarah"

    def test_handles_middle_name(self):
        parts = _name_parts("Sarah Elizabeth Chen")
        assert parts["first"] == "sarah"
        assert parts["last"] == "chen"


class TestComputeCseConfidence:
    def setup_method(self):
        self.svc = LinkedInService.__new__(LinkedInService)

    def test_base_confidence_is_high(self):
        conf = self.svc._compute_cse_confidence(
            "https://linkedin.com/in/random-slug", "Sarah Chen", "Genentech"
        )
        assert conf >= 0.85

    def test_name_match_boosts_confidence(self):
        conf_match = self.svc._compute_cse_confidence(
            "https://linkedin.com/in/sarah-chen-123", "Sarah Chen", "Genentech"
        )
        conf_no_match = self.svc._compute_cse_confidence(
            "https://linkedin.com/in/xyz-abc-789", "Sarah Chen", "Genentech"
        )
        assert conf_match > conf_no_match

    def test_max_confidence_capped(self):
        conf = self.svc._compute_cse_confidence(
            "https://linkedin.com/in/sarah-chen", "sarah", "genentech"
        )
        assert conf <= 0.97


class TestBuildCacheKey:
    def test_consistent_key(self):
        lead = MagicMock()
        lead.id = "test-uuid-123"
        lead.name = "Sarah Chen"
        svc = LinkedInService.__new__(LinkedInService)
        key1 = svc._build_cache_key(lead)
        key2 = svc._build_cache_key(lead)
        assert key1 == key2

    def test_different_leads_different_keys(self):
        lead1 = MagicMock()
        lead1.id = "uuid-1"
        lead1.name = "Sarah Chen"
        lead2 = MagicMock()
        lead2.id = "uuid-2"
        lead2.name = "John Smith"
        svc = LinkedInService.__new__(LinkedInService)
        assert svc._build_cache_key(lead1) != svc._build_cache_key(lead2)

    def test_key_has_prefix(self):
        lead = MagicMock()
        lead.id = "any-id"
        lead.name = "Any Name"
        svc = LinkedInService.__new__(LinkedInService)
        assert svc._build_cache_key(lead).startswith("linkedin:profile:")


class TestFindProfileUrl:
    @pytest.fixture
    def svc(self):
        with patch("app.services.linkedin_service.Cache") as mock_cache:
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock(return_value=True)
            instance = LinkedInService.__new__(LinkedInService)
            instance._google_api_key = None
            instance._google_cse_id = None
            instance._has_google_cse = False
            yield instance, mock_cache

    @pytest.mark.asyncio
    async def test_returns_pattern_result_when_no_apis(self, svc):
        service, _ = svc
        lead = MagicMock()
        lead.id = "lead-123"
        lead.name = "Sarah Chen"
        lead.company = "Genentech"
        result = await service.find_profile_url(lead)
        assert result["url"] is not None
        assert result["source"] in ("pattern", "duckduckgo", "not_found")

    @pytest.mark.asyncio
    async def test_returns_not_found_for_unknown_name(self, svc):
        service, _ = svc
        lead = MagicMock()
        lead.id = "lead-xyz"
        lead.name = "Unknown"
        lead.company = ""
        result = await service.find_profile_url(lead)
        assert result["source"] == "not_found"
        assert result["url"] is None

    @pytest.mark.asyncio
    async def test_cache_hit_skips_search(self, svc):
        service, mock_cache = svc
        mock_cache.get = AsyncMock(return_value={
            "url": "https://www.linkedin.com/in/sarah-chen",
            "confidence": 0.92,
            "source": "google_cse",
            "slug": "sarah-chen",
        })
        lead = MagicMock()
        lead.id = "lead-456"
        lead.name = "Sarah Chen"
        lead.company = "Genentech"
        result = await service.find_profile_url(lead)
        assert result["cached"] is True
        assert result["confidence"] == 0.92


class TestModuleHelpers:
    def test_strip_accents(self):
        assert _strip_accents("José") == "Jose"

    def test_extract_slug(self):
        assert _extract_slug("https://www.linkedin.com/in/sarah-chen") == "sarah-chen"

    def test_extract_slug_trailing_slash(self):
        assert _extract_slug("https://linkedin.com/in/sarah-chen/") == "sarah-chen"

    def test_normalise_adds_www(self):
        result = _normalise_linkedin_url("https://linkedin.com/in/sarah-chen")
        assert result == "https://www.linkedin.com/in/sarah-chen"