"""
Unit tests for enhanced PubMedService (Phase 2.3 Step 1)
Uses mocking — no real NCBI calls in CI.

Changes vs original:
  - AsyncMock added to imports (was missing)
  - TestGetAuthorProfile added
  - TestHighlyCitedTag added
"""

from unittest.mock import AsyncMock, MagicMock, patch

from unittest.mock import MagicMock, patch

import pytest

from app.services.pubmed_service import PubMedService


@pytest.fixture
def service():
    with patch("app.services.pubmed_service.PubMedScraper") as mock_scraper_cls:
        mock_scraper = MagicMock()
        mock_scraper_cls.return_value = mock_scraper
        svc = PubMedService()
        svc._scraper = mock_scraper
        yield svc, mock_scraper


class TestBuildCacheKey:
    def test_same_inputs_produce_same_key(self):
        k1 = PubMedService._build_cache_key("pubmed:results", "DILI query", "50")
        k2 = PubMedService._build_cache_key("pubmed:results", "DILI query", "50")
        assert k1 == k2

    def test_different_inputs_produce_different_keys(self):
        k1 = PubMedService._build_cache_key("pubmed:results", "query A")
        k2 = PubMedService._build_cache_key("pubmed:results", "query B")
        assert k1 != k2

    def test_key_has_readable_prefix(self):
        key = PubMedService._build_cache_key("pubmed:results", "test query")
        assert key.startswith("pubmed:results:")

    def test_key_length_is_fixed_regardless_of_input_length(self):
        """SHA-256 digest is always 64 hex chars; prefix + ':' + 64 chars."""
        short = PubMedService._build_cache_key("pubmed:results", "a")
        long_ = PubMedService._build_cache_key("pubmed:results", "a" * 500)
        assert len(short) == len(long_)

class TestComputeHIndex:
    def test_h_index_basic(self):
        articles = [
            {"citation_count": 10},
            {"citation_count": 5},
            {"citation_count": 3},
            {"citation_count": 1},
        ]
        assert PubMedService._compute_h_index(articles) == 3

    def test_h_index_zero_citations(self):
        articles = [{"citation_count": 0}, {"citation_count": 0}]
        assert PubMedService._compute_h_index(articles) == 0

    def test_h_index_empty(self):
        assert PubMedService._compute_h_index([]) == 0

    def test_h_index_all_equal(self):
        articles = [{"citation_count": 5}] * 5
        assert PubMedService._compute_h_index(articles) == 5


class TestClassifyInstitution:
    def test_academic(self):
        assert (
            PubMedService._classify_institution(
                "Department of Toxicology, Harvard University, Cambridge, MA"
            )
            == "academic"
        )

    def test_pharma(self):
        assert (
            PubMedService._classify_institution(
                "Genentech Inc., South San Francisco, CA"
            )
            == "pharma"
        )

    def test_hospital(self):
        assert (
            PubMedService._classify_institution(
                "Massachusetts General Hospital, Boston, MA"
            )
            == "hospital"
        )

    def test_cro(self):
        assert (
            PubMedService._classify_institution(
                "Charles River Laboratories, Wilmington, MA"
            )
            == "cro"
        )

    def test_unknown(self):
        assert PubMedService._classify_institution("") == "unknown"

    def test_case_insensitive(self):
        assert PubMedService._classify_institution("HARVARD UNIVERSITY") == "academic"


class TestBuildQuery:
    def test_base_query_only(self):
        svc = PubMedService.__new__(PubMedService)
        q = svc._build_query(
            "DILI 3D",
            journals=None,
            mesh_terms=None,
            study_type=None,
            min_year=None,
            max_year=None,
            years_back=3,
        )
        assert q == "DILI 3D"

    def test_with_mesh_terms(self):
        svc = PubMedService.__new__(PubMedService)
        q = svc._build_query(
            "DILI",
            journals=None,
            mesh_terms=["Drug-Induced Liver Injury"],
            study_type=None,
            min_year=None,
            max_year=None,
            years_back=3,
        )
        assert '"Drug-Induced Liver Injury"[MeSH Terms]' in q

    def test_with_year_range(self):
        svc = PubMedService.__new__(PubMedService)
        q = svc._build_query(
            "organoids",
            journals=None,
            mesh_terms=None,
            study_type=None,
            min_year=2022,
            max_year=2025,
            years_back=3,
        )
        assert "2022:2025[pdat]" in q

    def test_with_journals(self):
        svc = PubMedService.__new__(PubMedService)
        q = svc._build_query(
            "hepatotoxicity",
            journals=["Journal of Hepatology", "Hepatology"],
            mesh_terms=None,
            study_type=None,
            min_year=None,
            max_year=None,
            years_back=3,
        )
        assert '"Journal of Hepatology"[Journal]' in q
        assert '"Hepatology"[Journal]' in q

    def test_with_study_type(self):
        svc = PubMedService.__new__(PubMedService)
        q = svc._build_query(
            "toxicity",
            journals=None,
            mesh_terms=None,
            study_type="Clinical Trial",
            min_year=None,
            max_year=None,
            years_back=3,
        )
        assert '"Clinical Trial"[pt]' in q


class TestGetAuthorProfileShape:
    """Verify get_author_profile() returns expected keys for mock data."""

    @pytest.mark.asyncio
    async def test_returns_expected_keys_on_success(self, service):
        svc, mock_scraper = service

        mock_scraper.search_pubmed.return_value = ["12345678"]
        mock_scraper.fetch_article_details.return_value = [
            {
                "pmid": "12345678",
                "title": "DILI modelling with 3D hepatocytes",
                "year": 2023,
                "journal": "Toxicological Sciences",
                "authors": [{"affiliation": "Harvard University, Cambridge MA"}],
            }
        ]

        with (
            patch("app.core.cache.Cache.get", new_callable=AsyncMock, return_value=None),
            patch("app.core.cache.Cache.set", new_callable=AsyncMock, return_value=True),
            patch.object(svc, "_fetch_citation_counts", return_value={"12345678": 42}),
        ):
            profile = await svc.get_author_profile("Jane Smith", use_cache=False)

        required_keys = {
            "publication_count",
            "total_citations",
            "h_index_approx",
            "most_cited_paper",
            "publications",
            "recent_journals",
            "institution_type",
            "publication_velocity",
            "recency_score",
            "cached_at",
        }
        assert required_keys.issubset(profile.keys())
        assert profile["publication_count"] == 1
        assert profile["total_citations"] == 42
        assert profile["institution_type"] == "academic"

    @pytest.mark.asyncio
    async def test_invalid_name_returns_error(self, service):
        svc, _ = service
        result = await svc.get_author_profile("Unknown")
        assert result.get("error") == "invalid_author_name"

    @pytest.mark.asyncio
    async def test_empty_name_returns_error(self, service):
        svc, _ = service
        result = await svc.get_author_profile("")
        assert "error" in result


class TestHighlyCitedThreshold:
    """Verify highly-cited threshold and score boost behavior."""

    @pytest.mark.asyncio
    async def test_tag_applied_at_threshold(self):
        from app.services.pubmed_enrichment import PubMedEnrichmentService

        mock_pubmed = MagicMock()
        mock_pubmed.get_author_profile = AsyncMock(
            return_value={
                "publication_count": 5,
                "total_citations": 100,
                "h_index_approx": 4,
                "institution_type": "academic",
                "publication_velocity": 1.0,
                "recency_score": 0.8,
                "most_cited_paper": None,
                "recent_journals": [],
                "cached_at": "2025-01-01T00:00:00",
            }
        )

        svc = PubMedEnrichmentService(pubmed_service=mock_pubmed)

        lead = MagicMock()
        lead.name = "Dr Jane Smith"
        lead.propensity_score = 60
        lead.tags = []
        lead.add_tag = lambda t: lead.tags.append(t)
        lead.set_enrichment = MagicMock()
        lead.update_priority_tier = MagicMock()

        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        result = await svc.enrich_lead_pubmed(lead=lead, db=db)

        assert result["status"] == "success"
        assert "highly-cited" in lead.tags
        assert "highly-cited" in result["tags_applied"]

    @pytest.mark.asyncio
    async def test_tag_not_applied_below_threshold(self):
        from app.services.pubmed_enrichment import PubMedEnrichmentService

        mock_pubmed = MagicMock()
        mock_pubmed.get_author_profile = AsyncMock(
            return_value={
                "publication_count": 3,
                "total_citations": 99,
                "h_index_approx": 3,
                "institution_type": "pharma",
                "publication_velocity": 0.6,
                "recency_score": 0.5,
                "most_cited_paper": None,
                "recent_journals": [],
                "cached_at": "2025-01-01T00:00:00",
            }
        )

        svc = PubMedEnrichmentService(pubmed_service=mock_pubmed)

        lead = MagicMock()
        lead.name = "Dr John Doe"
        lead.propensity_score = 55
        lead.tags = []
        lead.add_tag = lambda t: lead.tags.append(t)
        lead.set_enrichment = MagicMock()
        lead.update_priority_tier = MagicMock()

        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        result = await svc.enrich_lead_pubmed(lead=lead, db=db)

        assert result["status"] == "success"
        assert "highly-cited" not in lead.tags
        assert "highly-cited" not in result["tags_applied"]

    def test_score_boost_ceiling(self):
        from app.services.pubmed_enrichment import PubMedEnrichmentService

        svc = PubMedEnrichmentService.__new__(PubMedEnrichmentService)
        boost = svc._compute_score_boost(
            {
                "h_index_approx": 999,
                "recency_score": 1.0,
                "publication_velocity": 999.0,
            }
        )
        assert boost == 25

    def test_score_boost_zero_for_empty_profile(self):
        from app.services.pubmed_enrichment import PubMedEnrichmentService

        svc = PubMedEnrichmentService.__new__(PubMedEnrichmentService)
        boost = svc._compute_score_boost({})
        assert boost == 0
