"""Scoring API endpoints backed by the Phase 2.5 scoring service."""

from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user, get_db
from app.models.lead import Lead
from app.models.user import User
from app.schemas.base import BulkOperationResponse
from app.services.scoring_service import DEFAULT_WEIGHTS, get_scoring_service

router = APIRouter()


def _validate_weight_overrides(overrides: Dict[str, float]) -> Dict[str, float]:
    effective_weights = {**DEFAULT_WEIGHTS, **overrides}
    if sum(effective_weights.values()) <= 0:
        raise HTTPException(status_code=422, detail="Scoring weights must sum to a positive value")
    return overrides


class ScoreWeights(BaseModel):
    seniority_score: Optional[float] = Field(None, ge=0)
    title_relevance: Optional[float] = Field(None, ge=0)
    is_decision_maker: Optional[float] = Field(None, ge=0)
    has_recent_pub: Optional[float] = Field(None, ge=0)
    pub_count_norm: Optional[float] = Field(None, ge=0)
    h_index_norm: Optional[float] = Field(None, ge=0)
    has_nih_active: Optional[float] = Field(None, ge=0)
    nih_award_norm: Optional[float] = Field(None, ge=0)
    has_private_funding: Optional[float] = Field(None, ge=0)
    has_email: Optional[float] = Field(None, ge=0)
    email_confidence: Optional[float] = Field(None, ge=0)
    has_linkedin_verified: Optional[float] = Field(None, ge=0)
    is_conference_speaker: Optional[float] = Field(None, ge=0)
    institution_type_score: Optional[float] = Field(None, ge=0)
    recency_score: Optional[float] = Field(None, ge=0)

    def to_overrides(self) -> Dict[str, float]:
        return {key: value for key, value in self.model_dump().items() if value is not None}


class RecalculateRequest(BaseModel):
    weights: Optional[ScoreWeights] = None
    override_score: Optional[int] = Field(None, ge=0, le=100)


class BulkRecalculateRequest(BaseModel):
    lead_ids: List[UUID] = Field(..., min_length=1, max_length=500)
    weights: Optional[ScoreWeights] = None


@router.post("/leads/{lead_id}/recalculate", response_model=dict, summary="Recalculate lead score")
async def recalculate_lead_score(lead_id: UUID, request: RecalculateRequest, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lead).where(Lead.id == lead_id, Lead.user_id == current_user.id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(404, "Lead not found")
    old_score = lead.propensity_score
    svc = get_scoring_service()
    if request.override_score is not None:
        lead.propensity_score = request.override_score
        lead.update_priority_tier()
        await db.commit()
        return {"lead_id": str(lead_id), "old_score": old_score, "new_score": lead.propensity_score, "priority_tier": lead.priority_tier, "method": "manual_override"}
    weight_overrides = _validate_weight_overrides(request.weights.to_overrides()) if request.weights else None
    score, breakdown = await svc.score_lead(lead, db, weight_overrides)
    return {"lead_id": str(lead_id), "old_score": old_score, "new_score": score, "priority_tier": lead.priority_tier, "breakdown": breakdown, "method": "weighted_feature_scoring_v1"}


@router.post("/leads/bulk/recalculate", response_model=BulkOperationResponse, summary="Recalculate multiple lead scores")
async def bulk_recalculate_scores(request: BulkRecalculateRequest, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    svc = get_scoring_service()
    weight_overrides = _validate_weight_overrides(request.weights.to_overrides()) if request.weights else None
    success_count = 0
    errors = []
    result = await db.execute(select(Lead).where(Lead.id.in_(request.lead_ids), Lead.user_id == current_user.id))
    leads = result.scalars().all()
    found_ids = {lead.id for lead in leads}
    for lead in leads:
        try:
            await svc.score_lead(lead, db, weight_overrides)
            success_count += 1
        except Exception as exc:
            errors.append({"id": str(lead.id), "error": str(exc)})
    await db.commit()
    for lead_id in request.lead_ids:
        if lead_id not in found_ids:
            errors.append({"id": str(lead_id), "error": "not_found"})
    return BulkOperationResponse(success_count=success_count, failure_count=len(errors), total=len(request.lead_ids), errors=errors)


@router.post("/leads/all/recalculate", response_model=dict, summary="Rescore all leads for current user")
async def rescore_all_leads(current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    weight_overrides = current_user.preferences.get("scoring_weights") if current_user.preferences else None
    summary = await get_scoring_service().batch_rescore(current_user.id, db, weight_overrides)
    return {"status": "complete", **summary}


@router.get("/config", response_model=dict, summary="Get scoring configuration")
async def get_scoring_config(current_user: User = Depends(get_current_active_user)):
    user_weights = current_user.preferences.get("scoring_weights", {}) if current_user.preferences else {}
    return {
        "default_weights": DEFAULT_WEIGHTS,
        "user_overrides": user_weights,
        "effective_weights": {**DEFAULT_WEIGHTS, **user_weights},
        "algorithm": "weighted_feature_scoring_v1",
        "feature_count": len(DEFAULT_WEIGHTS),
    }


@router.put("/config", response_model=dict, summary="Update scoring weights")
async def update_scoring_config(weights: ScoreWeights, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    overrides = _validate_weight_overrides(weights.to_overrides())
    if not current_user.preferences:
        current_user.preferences = {}
    current_user.preferences["scoring_weights"] = overrides
    db.add(current_user)
    await db.commit()
    return {"status": "saved", "overrides": overrides}


@router.get("/stats", response_model=dict, summary="Scoring statistics")
async def get_scoring_stats(current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(
            func.count(Lead.id).label("total"),
            func.avg(Lead.propensity_score).label("average"),
            func.min(Lead.propensity_score).label("minimum"),
            func.max(Lead.propensity_score).label("maximum"),
        ).where(Lead.user_id == current_user.id)
    )
    stats = result.first()
    tier_result = await db.execute(select(Lead.priority_tier, func.count(Lead.id)).where(Lead.user_id == current_user.id).group_by(Lead.priority_tier))
    distribution = {tier: count for tier, count in tier_result}
    return {
        "total_leads": stats.total or 0,
        "average_score": round(float(stats.average), 2) if stats.average else 0,
        "min_score": stats.minimum or 0,
        "max_score": stats.maximum or 0,
        "tier_distribution": {
            "HIGH": distribution.get("HIGH", 0),
            "MEDIUM": distribution.get("MEDIUM", 0),
            "LOW": distribution.get("LOW", 0),
        },
        "algorithm": "weighted_feature_scoring_v1",
    }
