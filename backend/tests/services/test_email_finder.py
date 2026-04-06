"""Unit tests for EmailFinder — Phase 2.3 Step 5."""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.email_finder import (
    _ascii_slug,
    _company_to_academic_domain,
    _company_to_domain_guess,
    _is_plausible_email,
    _lookup_university_domain,
    _parse_name,
)


@pytest.fixture
def mock_redis():
    """
    Patch Cache.get / Cache.exists so quota checks never hit real Redis.
    Returns zero-usage state (counter = 0, not exhausted).
    """
    with (
        patch("app.core.cache.Cache.get", new_callable=AsyncMock, return_value=None),
        patch("app.core.cache.Cache.exists", new_callable=AsyncMock, return_value=False),
    ):
        yield


class TestParseName:
    def test_standard(self):
        assert _parse_name("Sarah Chen") == ("sarah", "chen")

    def test_with_title(self):
        first, last = _parse_name("Dr. Sarah Chen")
        assert first == "sarah" and last == "chen"

    def test_middle_initial(self):
        first, last = _parse_name("Sarah E. Chen")
        assert first == "sarah" and last == "chen"

    def test_empty(self):
        assert _parse_name("") == ("", "")


class TestAsciiSlug:
    def test_accent_stripping(self):
        assert _ascii_slug("François") == "francois"

    def test_already_ascii(self):
        assert _ascii_slug("sarah") == "sarah"


class TestIsPlausibleEmail:
    def test_valid(self):
        assert _is_plausible_email("sarah.chen@harvard.edu")
        assert _is_plausible_email("jsmith@nih.gov")

    def test_invalid_no_at(self):
        assert not _is_plausible_email("sarahchenharvard.edu")

    def test_invalid_no_dot(self):
        assert not _is_plausible_email("sarah@harvard")

    def test_empty(self):
        assert not _is_plausible_email("")


class TestUniversityDomainLookup:
    def test_harvard(self):
        assert _lookup_university_domain("Harvard University") == "harvard.edu"

    def test_mit(self):
        assert (
            _lookup_university_domain("Massachusetts Institute of Technology (MIT)")
            == "mit.edu"
        )

    def test_ucsf_partial(self):
        assert _lookup_university_domain("UCSF Department of Toxicology") == "ucsf.edu"

    def test_unknown_university(self):
        assert _lookup_university_domain("Acme University") == ""


class TestCompanyDomainGuess:
    def test_strips_inc(self):
        assert _company_to_domain_guess("Genentech Inc.") == "genentech.com"

    def test_strips_llc(self):
        assert _company_to_domain_guess("BioTech LLC") == "biotech.com"

    def test_empty(self):
        assert _company_to_domain_guess("") == ""


class TestAcademicDomainGuess:
    def test_company_to_academic_domain(self):
        assert _company_to_academic_domain("University of Michigan") == "michigan.edu"


class TestQuotaManager:
    @pytest.mark.asyncio
    async def test_hunter_denied_below_threshold(self):
        from app.services.quota_manager import QuotaManager

        qm = QuotaManager()
        assert await qm.can_use_hunter(69) is False

    @pytest.mark.asyncio
    async def test_hunter_permitted_at_threshold(self, mock_redis):
        from app.services.quota_manager import QuotaManager

        qm = QuotaManager()
        assert await qm.can_use_hunter(70) is True

    @pytest.mark.asyncio
    async def test_hunter_permitted_above_threshold(self, mock_redis):
        from app.services.quota_manager import QuotaManager

        qm = QuotaManager()
        assert await qm.can_use_hunter(95) is True

    @pytest.mark.asyncio
    async def test_clearbit_denied_below_threshold(self):
        from app.services.quota_manager import QuotaManager

        qm = QuotaManager()
        assert await qm.can_use_clearbit(49) is False

    @pytest.mark.asyncio
    async def test_clearbit_permitted_at_threshold(self, mock_redis):
        from app.services.quota_manager import QuotaManager

        qm = QuotaManager()
        assert await qm.can_use_clearbit(50) is True

    @pytest.mark.asyncio
    async def test_clearbit_permitted_above_threshold(self, mock_redis):
        from app.services.quota_manager import QuotaManager

        qm = QuotaManager()
        assert await qm.can_use_clearbit(80) is True
