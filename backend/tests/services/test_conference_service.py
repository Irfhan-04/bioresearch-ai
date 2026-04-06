"""Unit tests for ConferenceService — Phase 2.3 Step 3"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.conference_service import (
    ConferenceService, _tokenise, _cache_key
)


class TestTokenise:
    def test_basic_split(self):
        tokens = _tokenise("drug-induced liver injury")
        assert "drug-induced" in tokens
        assert "liver" in tokens
        assert "injury" in tokens

    def test_removes_stopwords(self):
        tokens = _tokenise("the toxicology of drugs")
        assert "the" not in tokens
        assert "of" not in tokens
        assert "toxicology" in tokens

    def test_removes_short_tokens(self):
        tokens = _tokenise("3D in vitro models")
        assert "in" not in tokens    # 2 chars
        assert "3d" in tokens or "3D" in tokens


class TestCacheKey:
    def test_format(self):
        key = _cache_key("sot", 2025)
        assert key == "conference:speakers:sot:2025"

    def test_lowercase(self):
        key = _cache_key("SOT", 2025)
        assert "SOT" not in key


class TestRelevanceScore:
    def setup_method(self):
        self.svc = ConferenceService.__new__(ConferenceService)

    def test_presentation_title_match_highest(self):
        speaker = {
            "name": "Dr. Jane Doe",
            "title": "Scientist",
            "company": "Pharma Inc",
            "presentation_title": "DILI mechanisms in 3D hepatocyte models",
            "session_name": "",
        }
        score = self.svc._relevance_score(speaker, ["dili", "hepatocyte"])
        assert score >= 6   # +3 per term in presentation_title

    def test_no_match_returns_zero(self):
        speaker = {
            "name": "Dr. John Smith",
            "title": "Engineer",
            "company": "Tech Corp",
            "presentation_title": "Software architecture patterns",
            "session_name": "",
        }
        score = self.svc._relevance_score(speaker, ["dili", "hepatocyte", "toxicol"])
        assert score == 0

    def test_senior_role_bonus(self):
        base = {
            "name": "Dr. Senior",
            "company": "Pharma Inc",
            "presentation_title": "Toxicology update",
            "session_name": "",
        }
        speaker_senior = {**base, "title": "Director of Safety", "is_senior_role": True}
        speaker_junior = {**base, "title": "Scientist",          "is_senior_role": False}
        assert (
            self.svc._relevance_score(speaker_senior, ["toxicol"])
            > self.svc._relevance_score(speaker_junior, ["toxicol"])
        )


class TestConvertToLeadDict:
    def setup_method(self):
        self.svc = ConferenceService.__new__(ConferenceService)

    def test_required_fields_present(self):
        speaker = {
            "name": "Sarah Chen", "title": "PI",
            "company": "MIT", "conference_name": "SOT",
            "conference_key": "sot", "conference_year": 2025,
        }
        lead = self.svc._convert_to_lead_dict(speaker, score=10)
        assert lead["name"] == "Sarah Chen"
        assert lead["data_sources"] == ["conference"]
        assert lead["conference_key"] == "sot"

    def test_missing_fields_have_defaults(self):
        lead = self.svc._convert_to_lead_dict({"name": "Unknown"}, score=1)
        assert lead["company"] == "Unknown"
        assert lead["location"] == "Unknown"
        assert lead["email"] is None
