"""
PubMed Enrichment Service — Phase 2.3 Step 1 Fix
=================================================

Bridges the gap between:
  - EnrichmentService.enrich_lead() — the entry point
  - PubMedService.get_author_profile() — the data source

Fixes the broken call chain documented in the Phase 2.3 Step 1 audit:

  POST /api/v1/enrich/{lead_id}?services=pubmed
     → EnrichmentService._enrich_pubmed()         [NEW in Fix 4]
     → PubMedEnrichmentService.enrich_lead_pubmed()  [THIS FILE]
     → PubMedService.get_author_profile()          [EXISTS — Phase 2.3 Step 1]

Additional data quality features implemented here:
  - score_boost  — integer points added to propensity_score based on citations/h-index
  - highly-cited — tag applied when total_citations >= 100
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead
from app.services.pubmed_service import PubMedService, get_pubmed_service

logger = logging.getLogger(__name__)

# ── Thresholds ────────────────────────────────────────────────────────────────
_HIGHLY_CITED_THRESHOLD = 100
_MAX_SCORE_BOOST = 25


class PubMedEnrichmentService:
    """Enriches a Lead using PubMed citation data."""

    def __init__(self, pubmed_service: Optional[PubMedService] = None) -> None:
        self._pubmed = pubmed_service or get_pubmed_service()

    async def enrich_lead_pubmed(
        self,
        lead: Lead,
        db: AsyncSession,
        max_publications: int = 20,
        years_back: int = 5,
    ) -> Dict[str, Any]:
        """Fetch a citation profile for the lead's author and apply enrichment."""
        if not lead.name or lead.name == "Unknown":
            return {
                "status": "error",
                "reason": "lead_has_no_name",
                "score_boost": 0,
                "tags_applied": [],
            }

        try:
            profile = await self._pubmed.get_author_profile(
                author_name=lead.name,
                max_publications=max_publications,
                years_back=years_back,
            )
        except Exception as exc:
            logger.error(
                "get_author_profile() raised for lead %s (%s): %s",
                lead.id,
                lead.name,
                exc,
                exc_info=True,
            )
            return {
                "status": "error",
                "reason": str(exc),
                "score_boost": 0,
                "tags_applied": [],
            }

        if "error" in profile:
            return {
                "status": "error",
                "reason": profile["error"],
                "score_boost": 0,
                "tags_applied": [],
            }

        score_boost = self._compute_score_boost(profile)
        tags_applied: list[str] = []

        total_citations = profile.get("total_citations", 0)
        if total_citations >= _HIGHLY_CITED_THRESHOLD:
            lead.add_tag("highly-cited")
            tags_applied.append("highly-cited")
            logger.debug(
                "Tag 'highly-cited' applied to lead %s (citations=%d)",
                lead.id,
                total_citations,
            )

        institution_type = profile.get("institution_type", "unknown")
        if institution_type != "unknown":
            tag = f"institution:{institution_type}"
            lead.add_tag(tag)
            tags_applied.append(tag)

        pub_count = profile.get("publication_count", 0)
        if pub_count > 0:
            lead.publication_count = pub_count

        if score_boost > 0 and lead.propensity_score is not None:
            lead.propensity_score = min(100, lead.propensity_score + score_boost)
            lead.update_priority_tier()

        enrichment_payload = {
            "publication_count": pub_count,
            "total_citations": total_citations,
            "h_index_approx": profile.get("h_index_approx", 0),
            "institution_type": institution_type,
            "publication_velocity": profile.get("publication_velocity", 0.0),
            "recency_score": profile.get("recency_score", 0.0),
            "most_cited_paper": profile.get("most_cited_paper"),
            "recent_journals": profile.get("recent_journals", []),
            "score_boost": score_boost,
            "tags_applied": tags_applied,
            "cached_at": profile.get("cached_at"),
        }
        lead.set_enrichment("pubmed", enrichment_payload)
        await db.commit()
        await db.refresh(lead)

        logger.info(
            "PubMed enrichment complete for lead %s (%s): pubs=%d, cit=%d, h=%d, boost=%d, tags=%s",
            lead.id,
            lead.name,
            pub_count,
            total_citations,
            profile.get("h_index_approx", 0),
            score_boost,
            tags_applied,
        )

        return {
            "status": "success",
            "publication_count": pub_count,
            "total_citations": total_citations,
            "h_index_approx": profile.get("h_index_approx", 0),
            "institution_type": institution_type,
            "publication_velocity": profile.get("publication_velocity", 0.0),
            "recency_score": profile.get("recency_score", 0.0),
            "most_cited_paper": profile.get("most_cited_paper"),
            "score_boost": score_boost,
            "tags_applied": tags_applied,
        }

    @staticmethod
    def _compute_score_boost(profile: Dict[str, Any]) -> int:
        """Compute extra score points earned from PubMed citation signals."""
        h_index = profile.get("h_index_approx", 0)
        recency = profile.get("recency_score", 0.0)
        velocity = profile.get("publication_velocity", 0.0)

        h_pts = min(h_index, 10)
        r_pts = round(recency * 8)
        v_pts = min(round(velocity * 2), 7)

        total = h_pts + r_pts + v_pts
        return min(total, _MAX_SCORE_BOOST)


_pubmed_enrichment_service: Optional[PubMedEnrichmentService] = None


def get_pubmed_enrichment_service() -> PubMedEnrichmentService:
    global _pubmed_enrichment_service
    if _pubmed_enrichment_service is None:
        _pubmed_enrichment_service = PubMedEnrichmentService()
    return _pubmed_enrichment_service


__all__ = ["PubMedEnrichmentService", "get_pubmed_enrichment_service"]
