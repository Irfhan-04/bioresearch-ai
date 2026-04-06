"""Scoring service shim (temporary, Week 1 compatibility)."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select

from app.models.researcher import Researcher

logger = logging.getLogger(__name__)


class ScoringService:
    """Minimal scoring service retained only to keep imports stable."""

    def score_researcher_sync(
        self, researcher: Researcher, weight_overrides: Optional[Dict[str, float]] = None
    ) -> Tuple[int, Dict[str, float]]:
        _ = weight_overrides
        relevance_score = int(getattr(researcher, "propensity_score", 0) or 0)
        relevance_tier = researcher.get_priority_tier() if hasattr(researcher, "get_priority_tier") else "UNSCORED"
        return relevance_score, {"relevance_score": float(relevance_score), "relevance_tier": relevance_tier}

    async def score_researcher(
        self,
        researcher: Researcher,
        db,
        weight_overrides: Optional[Dict[str, float]] = None,
        persist: bool = True,
    ) -> Tuple[int, Dict[str, float]]:
        relevance_score, breakdown = self.score_researcher_sync(researcher, weight_overrides)
        if persist:
            if hasattr(researcher, "propensity_score"):
                researcher.propensity_score = relevance_score
            if hasattr(researcher, "update_priority_tier"):
                researcher.update_priority_tier()
            history = (researcher.enrichment_data or {}).get("score_history", [])
            history.append({"relevance_score": relevance_score, "scored_at": datetime.utcnow().isoformat()})
            researcher.set_enrichment("score_history", history[-10:])
            db.add(researcher)
            await db.commit()
        return relevance_score, breakdown

    async def batch_rescore_researchers(
        self,
        user_id: UUID,
        db,
        weight_overrides: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        _ = weight_overrides
        result = await db.execute(select(Researcher).where(Researcher.user_id == user_id))
        researchers = result.scalars().all()

        rescored = 0
        score_sum = 0
        relevance_tiers: Dict[str, int] = {}

        for researcher in researchers:
            try:
                relevance_score, _ = await self.score_researcher(researcher, db, persist=True)
                rescored += 1
                score_sum += relevance_score
                tier = researcher.get_priority_tier() if hasattr(researcher, "get_priority_tier") else "UNSCORED"
                relevance_tiers[tier] = relevance_tiers.get(tier, 0) + 1
            except Exception as exc:
                logger.warning("Rescore failed for researcher %s: %s", researcher.id, exc)

        return {
            "researchers_rescored": rescored,
            "average_relevance_score": round(score_sum / rescored, 1) if rescored else 0,
            "relevance_tier_distribution": relevance_tiers,
        }

    def get_feature_names(self) -> List[str]:
        return ["relevance_score", "relevance_tier"]

    def get_default_weights(self) -> Dict[str, float]:
        return {}


_scoring_service: Optional[ScoringService] = None


def get_scoring_service() -> ScoringService:
    global _scoring_service
    if _scoring_service is None:
        _scoring_service = ScoringService()
    return _scoring_service
