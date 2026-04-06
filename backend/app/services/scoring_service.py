"""Scoring Service — Phase 2.5."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from app.models.lead import Lead

logger = logging.getLogger(__name__)

DEFAULT_WEIGHTS: Dict[str, float] = {
    "seniority_score": 10.0,
    "title_relevance": 10.0,
    "is_decision_maker": 5.0,
    "has_recent_pub": 8.0,
    "pub_count_norm": 9.0,
    "h_index_norm": 8.0,
    "has_nih_active": 12.0,
    "nih_award_norm": 8.0,
    "has_private_funding": 5.0,
    "has_email": 5.0,
    "email_confidence": 5.0,
    "has_linkedin_verified": 5.0,
    "is_conference_speaker": 5.0,
    "institution_type_score": 3.0,
    "recency_score": 2.0,
}

_SENIOR_TITLES = {
    "director",
    "head of",
    "vp ",
    "vice president",
    "chief",
    "principal",
    "senior scientist",
    "fellow",
    "group leader",
    "section chief",
    "president",
    "founder",
    "co-founder",
    "cso",
    "cmo",
}
_DECISION_MAKER_TITLES = {
    "director",
    "head of",
    "vp",
    "vice president",
    "chief",
    "president",
    "founder",
    "cso",
    "cmo",
}
_RELEVANT_TITLE_KEYWORDS = {
    "toxicol",
    "safety",
    "pharmacol",
    "hepat",
    "liver",
    "dili",
    "adme",
    "in vitro",
    "preclinical",
    "nonclinical",
    "drug",
    "biomarker",
    "research",
    "scientist",
    "investigator",
    "pi ",
}
_PHARMA_FUNDING_KEYWORDS = {
    "series a",
    "series b",
    "series c",
    "series d",
    "public",
    "ipo",
    "acquired",
    "seed",
    "pre-seed",
}


class FeatureExtractor:
    """Convert a lead into a normalized 15-dimensional feature vector."""

    def extract(self, lead: Lead) -> Dict[str, float]:
        enrichment = lead.enrichment_data or {}
        pubmed_data = enrichment.get("pubmed", {})
        nih_data = enrichment.get("nih_grants", {})
        linkedin_data = enrichment.get("linkedin", {})
        email_data = enrichment.get("email", {})
        conf_data = enrichment.get("conference", {})

        return {
            "seniority_score": self._seniority_score(lead.title),
            "title_relevance": self._title_relevance(lead.title),
            "is_decision_maker": self._is_decision_maker(lead.title),
            "has_recent_pub": 1.0 if lead.recent_publication else 0.0,
            "pub_count_norm": self._normalise(lead.publication_count or 0, max_val=20),
            "h_index_norm": self._normalise(pubmed_data.get("h_index_approx", 0), max_val=15),
            "has_nih_active": 1.0 if nih_data.get("active_grants", 0) > 0 else 0.0,
            "nih_award_norm": self._normalise(nih_data.get("max_award", 0), max_val=1_000_000),
            "has_private_funding": self._private_funding_score(lead.company_funding),
            "has_email": 1.0 if lead.email else 0.0,
            "email_confidence": float(email_data.get("confidence", 0.0) or 0.0),
            "has_linkedin_verified": 1.0
            if (lead.linkedin_url and linkedin_data.get("confidence", 0) >= 0.75)
            else 0.0,
            "is_conference_speaker": 1.0 if conf_data else 0.0,
            "institution_type_score": self._institution_score(
                pubmed_data.get("institution_type", conf_data.get("institution_type", "unknown"))
            ),
            "recency_score": float(pubmed_data.get("recency_score", 0.0) or 0.0),
        }

    @staticmethod
    def _seniority_score(title: Optional[str]) -> float:
        if not title:
            return 0.2
        lowered = title.lower()
        if any(keyword in lowered for keyword in _SENIOR_TITLES):
            return 1.0
        if any(keyword in lowered for keyword in {"senior", "lead", "principal"}):
            return 0.7
        if any(keyword in lowered for keyword in {"scientist", "researcher", "investigator"}):
            return 0.5
        return 0.3

    @staticmethod
    def _title_relevance(title: Optional[str]) -> float:
        if not title:
            return 0.1
        lowered = title.lower()
        matches = sum(1 for keyword in _RELEVANT_TITLE_KEYWORDS if keyword in lowered)
        return min(matches / 3, 1.0)

    @staticmethod
    def _is_decision_maker(title: Optional[str]) -> float:
        if not title:
            return 0.0
        lowered = title.lower()
        return 1.0 if any(keyword in lowered for keyword in _DECISION_MAKER_TITLES) else 0.0

    @staticmethod
    def _private_funding_score(funding: Optional[str]) -> float:
        if not funding:
            return 0.0
        lowered = funding.lower()
        if "nih" in lowered:
            return 0.0
        for keyword in _PHARMA_FUNDING_KEYWORDS:
            if keyword in lowered:
                if any(stage in lowered for stage in {"series c", "series d", "public"}):
                    return 1.0
                if "series b" in lowered:
                    return 0.8
                if "series a" in lowered:
                    return 0.6
                if "seed" in lowered:
                    return 0.3
                return 0.5
        return 0.0

    @staticmethod
    def _institution_score(institution_type: str) -> float:
        mapping = {
            "pharma": 1.0,
            "cro": 0.8,
            "hospital": 0.6,
            "academic": 0.4,
            "unknown": 0.2,
        }
        return mapping.get(institution_type, 0.2)

    @staticmethod
    def _normalise(value: float, max_val: float) -> float:
        if max_val <= 0:
            return 0.0
        return min(float(value) / max_val, 1.0)


class WeightedScorer:
    """Compute a 0-100 score using weighted normalized features."""

    def __init__(self, weight_overrides: Optional[Dict[str, float]] = None):
        self._weights = {**DEFAULT_WEIGHTS, **(weight_overrides or {})}
        self._total_weight = sum(self._weights.values())
        if self._total_weight <= 0:
            raise ValueError("Scoring weights must sum to a positive value")

    def score(self, features: Dict[str, float]) -> int:
        raw = sum(features.get(name, 0.0) * weight for name, weight in self._weights.items())
        normalized = (raw / self._total_weight) * 100
        return max(0, min(100, round(normalized)))

    def score_breakdown(self, features: Dict[str, float]) -> Dict[str, float]:
        return {
            name: round(features.get(name, 0.0) * weight / self._total_weight * 100, 2)
            for name, weight in self._weights.items()
        }


class ScoringService:
    """Orchestrate feature extraction, weighted scoring, and persistence."""

    def __init__(self) -> None:
        self._extractor = FeatureExtractor()

    def score_lead_sync(
        self, lead: Lead, weight_overrides: Optional[Dict[str, float]] = None
    ) -> Tuple[int, Dict[str, float]]:
        scorer = WeightedScorer(weight_overrides)
        features = self._extractor.extract(lead)
        score = scorer.score(features)
        breakdown = scorer.score_breakdown(features)
        return score, breakdown

    async def score_lead(
        self,
        lead: Lead,
        db,
        weight_overrides: Optional[Dict[str, float]] = None,
        persist: bool = True,
    ) -> Tuple[int, Dict[str, float]]:
        score, breakdown = self.score_lead_sync(lead, weight_overrides)

        if persist:
            lead.propensity_score = score
            lead.update_priority_tier()

            scoring_history = (lead.enrichment_data or {}).get("score_history", [])
            scoring_history.append(
                {
                    "score": score,
                    "scored_at": datetime.utcnow().isoformat(),
                    "algorithm": "weighted_feature_scoring_v1",
                }
            )
            lead.set_enrichment("score_history", scoring_history[-10:])
            lead.set_enrichment("score_breakdown", breakdown)

            db.add(lead)
            await db.commit()

        return score, breakdown

    async def batch_rescore(
        self,
        user_id: UUID,
        db,
        weight_overrides: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        from sqlalchemy import select
        from app.models.lead import Lead as LeadModel

        result = await db.execute(select(LeadModel).where(LeadModel.user_id == user_id))
        leads = result.scalars().all()

        scored = 0
        score_sum = 0
        tier_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNSCORED": 0}

        for lead in leads:
            try:
                score, _ = await self.score_lead(lead, db, weight_overrides, persist=True)
                scored += 1
                score_sum += score
                tier = lead.get_priority_tier()
                tier_counts[tier] = tier_counts.get(tier, 0) + 1
            except Exception as exc:
                logger.warning("Rescore failed for lead %s: %s", lead.id, exc)

        await db.commit()
        return {
            "leads_rescored": scored,
            "average_score": round(score_sum / scored, 1) if scored else 0,
            "tier_distribution": tier_counts,
        }

    def get_feature_names(self) -> List[str]:
        return list(DEFAULT_WEIGHTS.keys())

    def get_default_weights(self) -> Dict[str, float]:
        return dict(DEFAULT_WEIGHTS)


_scoring_service: Optional[ScoringService] = None


def get_scoring_service() -> ScoringService:
    global _scoring_service
    if _scoring_service is None:
        _scoring_service = ScoringService()
    return _scoring_service


__all__ = [
    "ScoringService",
    "FeatureExtractor",
    "WeightedScorer",
    "DEFAULT_WEIGHTS",
    "get_scoring_service",
]
