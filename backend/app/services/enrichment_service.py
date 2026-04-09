"""Enrichment service for researcher records."""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import Cache, CacheKey
from app.models.researcher import Researcher
from app.models.user import User
from app.services.company_enricher import get_company_enricher
from app.services.contact_service import get_contact_service
from app.services.embedding_service import get_embedding_service
from app.services.intelligence_service import get_intelligence_service
from app.services.pubmed_enrichment import get_pubmed_enrichment_service
from app.services.research_area_classifier import (
    classify_research_area,
    compute_domain_coverage_score,
)
from app.services.scoring_service import get_scoring_service

logger = logging.getLogger(__name__)


class EnrichmentService:
    def __init__(self):
        pass

    async def enrich_researcher(
        self, researcher: Researcher, db: AsyncSession, services: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        results = {"researcher_id": str(researcher.id), "enrichments": {}, "errors": []}
        services = services or self._get_available_services()
        tasks = []

        if "email" in services and not researcher.email:
            tasks.append(("email", self._find_email(researcher)))
        if "company" in services and researcher.company:
            tasks.append(("company", self._enrich_company(researcher.company, researcher=researcher)))
        if "pubmed" in services and researcher.name:
            tasks.append(("pubmed", self._enrich_pubmed(researcher, db)))

        if tasks:
            enrichment_results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
            for (service, _), result in zip(tasks, enrichment_results):
                if isinstance(result, Exception):
                    results["errors"].append({"service": service, "error": str(result)})
                else:
                    results["enrichments"][service] = result

        if results["enrichments"]:
            await self._apply_enrichments(researcher, results["enrichments"], db)

        return results

    async def enrich_researchers_batch(
        self,
        researcher_ids: List[UUID],
        user: User,
        db: AsyncSession,
        services: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        results = {"total": len(researcher_ids), "successful": 0, "failed": 0, "results": []}
        for researcher_id in researcher_ids:
            record = (await db.execute(select(Researcher).where(Researcher.id == researcher_id, Researcher.user_id == user.id))).scalar_one_or_none()
            if not record:
                results["failed"] += 1
                results["results"].append({"researcher_id": str(researcher_id), "status": "not_found"})
                continue
            enrichment_result = await self.enrich_researcher(record, db, services)
            results["successful"] += 1
            results["results"].append({"researcher_id": str(researcher_id), "status": "success", **enrichment_result})
        return results

    async def _find_email(self, researcher: Researcher) -> Optional[Dict[str, Any]]:
        cache_key = CacheKey.enrichment(str(researcher.id), "email")
        cached = await Cache.get(cache_key)
        if cached:
            return cached

        finder = get_contact_service()
        result = await finder.find_email(researcher)
        if result and result.get("email"):
            await Cache.set(cache_key, result, ttl=86_400 * 30)
            return result
        return None

    async def _enrich_company(self, company_name: str, researcher: Optional[Researcher] = None) -> Optional[Dict[str, Any]]:
        cache_key = f"company:{company_name.lower().replace(' ', '_')[:80]}"
        cached = await Cache.get(cache_key)
        if cached:
            return cached

        result = await get_company_enricher().enrich_company(
            company_name=company_name,
            researcher=researcher,
            quota_manager=None,
        )
        await Cache.set(cache_key, result, ttl=86_400)
        return result

    async def _find_linkedin(self, researcher: Researcher) -> Optional[Dict[str, Any]]:
        """LinkedIn enrichment disabled — Proxycurl removed from portfolio stack."""
        return None

    async def _enrich_pubmed(self, researcher: Researcher, db: AsyncSession) -> dict:
        return await get_pubmed_enrichment_service().enrich_researcher_pubmed(researcher=researcher, db=db)

    async def _apply_enrichments(self, researcher: Researcher, enrichments: Dict[str, Any], db: AsyncSession):
        if "email" in enrichments and enrichments["email"] and enrichments["email"].get("email"):
            researcher.email = enrichments["email"]["email"]
            researcher.set_enrichment("email", enrichments["email"])
        if "company" in enrichments and enrichments["company"]:
            researcher.set_enrichment("company", enrichments["company"])
        if "pubmed" in enrichments and enrichments["pubmed"]:
            pubmed_data = enrichments["pubmed"]
            if pubmed_data.get("abstract_text"):
                researcher.abstract_text = pubmed_data["abstract_text"]
            if pubmed_data.get("publication_count"):
                researcher.publication_count = pubmed_data["publication_count"]
        await db.commit()
        await db.refresh(researcher)
        await self._run_ai_sequence(researcher, db)

    async def _run_ai_sequence(self, researcher: Researcher, db: AsyncSession) -> None:
        """
        Run the full AI enrichment sequence after basic enrichments are applied.

        Order:
        1. Classify research area (classifier)
        2. Compute domain_coverage_score (classifier-derived ML feature)
        3. Index researcher in ChromaDB + compute abstract_relevance_score (embeddings)
        4. Score with XGBoost + SHAP (ML scorer)
        """
        try:
            title = researcher.publication_title or researcher.title
            abstract = researcher.abstract_text

            research_area = classify_research_area(
                title=title,
                abstract=abstract,
            )
            researcher.research_area = research_area

            domain_score = compute_domain_coverage_score(
                title=title,
                abstract=abstract,
            )
            researcher.domain_coverage_score = domain_score

            embedding_svc = get_embedding_service()
            abstract_relevance = await embedding_svc.compute_abstract_relevance(
                title=title,
                abstract=abstract,
            )
            researcher.abstract_relevance_score = abstract_relevance

            doc_id = await embedding_svc.index_researcher(
                researcher_id=str(researcher.id),
                user_id=str(researcher.user_id),
                title=title,
                abstract=abstract,
                research_area=research_area,
                name=researcher.name,
            )
            researcher.abstract_embedding_id = doc_id

            db.add(researcher)
            await db.commit()
            await db.refresh(researcher)

            scoring_svc = get_scoring_service()
            scoring_result = await scoring_svc.score_and_persist(researcher, db)

            intelligence_svc = get_intelligence_service()
            intelligence = await intelligence_svc.generate(researcher)
            if intelligence is not None:
                researcher.intelligence = intelligence
                researcher.intelligence_generated_at = datetime.utcnow()
                db.add(researcher)
                await db.commit()
                await db.refresh(researcher)

            logger.info(
                "AI sequence complete for %s: area=%s score=%d tier=%s",
                researcher.id,
                research_area,
                scoring_result["relevance_score"],
                scoring_result["relevance_tier"],
            )
        except Exception as exc:
            logger.error("AI sequence failed for %s: %s", researcher.id, exc, exc_info=True)

    def _get_available_services(self) -> List[str]:
        return ["email", "company", "pubmed"]

    async def get_enrichment_status(self, researcher: Researcher) -> Dict[str, Any]:
        enriched_fields = []
        missing_fields = []
        for field in ("email", "linkedin_url", "company", "recent_publication"):
            if getattr(researcher, field, None):
                enriched_fields.append(field)
            else:
                missing_fields.append(field)
        total_fields = len(enriched_fields) + len(missing_fields)
        return {
            "researcher_id": str(researcher.id),
            "enriched_fields": enriched_fields,
            "missing_fields": missing_fields,
            "enrichment_data": researcher.enrichment_data or {},
            "completion_percentage": round((len(enriched_fields) / total_fields) * 100, 2) if total_fields else 0,
            "last_enriched": datetime.utcnow().isoformat(),
        }


enrichment_service: Optional[EnrichmentService] = None


def get_enrichment_service() -> EnrichmentService:
    global enrichment_service
    if enrichment_service is None:
        enrichment_service = EnrichmentService()
    return enrichment_service
