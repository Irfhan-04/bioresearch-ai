"""Unit tests for FundingService — Phase 2.3 Step 4"""

import pytest
from unittest.mock import MagicMock, patch
from app.services.funding_service import FundingService, _tokenise_query, _build_cache_key


class TestTokeniseQuery:
    def test_basic_split(self):
        tokens = _tokenise_query("drug-induced liver injury")
        assert "drug-induced" in tokens
        assert "liver" in tokens

    def test_removes_stopwords(self):
        tokens = _tokenise_query("the toxicology of drugs and cells")
        assert "the" not in tokens
        assert "and" not in tokens
        assert "toxicology" in tokens

    def test_max_five_tokens(self):
        tokens = _tokenise_query("one two three four five six seven eight")
        assert len(tokens) <= 5

    def test_deduplicates(self):
        tokens = _tokenise_query("liver liver injury liver")
        assert tokens.count("liver") == 1


class TestComputeFundingScoreBoost:
    def setup_method(self):
        self.svc = FundingService.__new__(FundingService)

    def test_no_grants_zero_boost(self):
        assert self.svc.compute_funding_score_boost([]) == 0

    def test_active_grant_base_boost(self):
        grants = [{"is_active": True, "mechanism": "R21", "award_amount": 200_000, "uses_3d_models": False}]
        boost  = self.svc.compute_funding_score_boost(grants)
        assert boost >= 20

    def test_r01_adds_boost(self):
        grants = [{"is_active": True, "mechanism": "R01", "award_amount": 400_000, "uses_3d_models": False}]
        boost  = self.svc.compute_funding_score_boost(grants)
        assert boost >= 28  # 20 active + 8 R01

    def test_3d_models_adds_boost(self):
        grants = [{"is_active": True, "mechanism": "R01", "award_amount": 500_000, "uses_3d_models": True}]
        boost  = self.svc.compute_funding_score_boost(grants)
        assert boost >= 33  # 20 + 8 + 5

    def test_max_boost_capped_at_38(self):
        grants = [{"is_active": True, "mechanism": "R01", "award_amount": 900_000, "uses_3d_models": True}]
        boost  = self.svc.compute_funding_score_boost(grants)
        assert boost <= 38


class TestBuildCacheKey:
    def test_consistent_output(self):
        k1 = _build_cache_key("nih:keywords", "dili", "2024", "True")
        k2 = _build_cache_key("nih:keywords", "dili", "2024", "True")
        assert k1 == k2

    def test_different_parts_different_key(self):
        k1 = _build_cache_key("nih:keywords", "dili")
        k2 = _build_cache_key("nih:keywords", "hepatocyte")
        assert k1 != k2

    def test_prefix_preserved(self):
        key = _build_cache_key("nih:pi", "sarah-chen")
        assert key.startswith("nih:pi:")


class TestParseNIHName:
    def test_standard_format(self):
        from src.data_sources.funding_scraper import _parse_nih_name
        first, last = _parse_nih_name("SMITH, JOHN A")
        assert first == "John"
        assert last  == "Smith"

    def test_hyphenated_last_name(self):
        from src.data_sources.funding_scraper import _parse_nih_name
        first, last = _parse_nih_name("CHEN-WILSON, SARAH")
        assert first == "Sarah"
        assert "Chen" in last

    def test_empty_string(self):
        from src.data_sources.funding_scraper import _parse_nih_name
        first, last = _parse_nih_name("")
        assert first == ""
        assert last  == ""
