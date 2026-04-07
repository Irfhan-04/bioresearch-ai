"""Enrichment service for researcher records."""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import Cache, CacheKey
from app.core.config import settings
from app.models.researcher import Researcher
from app.models.user import User
from app.services.company_enricher import get_company_enricher
from app.services.contact_service import get_contact_service
from app.services.linkedin_service import get_linkedin_service
from app.services.pubmed_enrichment import get_pubmed_enrichment_service
from app.services.quota_manager import get_quota_manager


class EnrichmentService:
    def __init__(self):
        self.hunter_api_key = settings.HUNTER_API_KEY

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
        if "linkedin" in services and researcher.name and researcher.company:
            tasks.append(("linkedin", self._find_linkedin(researcher)))
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
        result = await finder.find_email(researcher, get_quota_manager())
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
            lead=researcher,
            quota_manager=get_quota_manager(),
        )
        await Cache.set(cache_key, result, ttl=86_400)
        return result

    async def _find_linkedin(self, researcher: Researcher) -> Optional[Dict[str, Any]]:
        result = await get_linkedin_service().find_profile_url(researcher)
        return result if result.get("url") else None

    async def _enrich_pubmed(self, researcher: Researcher, db: AsyncSession) -> dict:
        return await get_pubmed_enrichment_service().enrich_lead_pubmed(lead=researcher, db=db)

    async def _apply_enrichments(self, researcher: Researcher, enrichments: Dict[str, Any], db: AsyncSession):
        if "email" in enrichments and enrichments["email"] and enrichments["email"].get("email"):
            researcher.email = enrichments["email"]["email"]
            researcher.set_enrichment("email", enrichments["email"])
        if "company" in enrichments and enrichments["company"]:
            researcher.set_enrichment("company", enrichments["company"])
        if "linkedin" in enrichments and enrichments["linkedin"]:
            researcher.set_enrichment("linkedin", enrichments["linkedin"])
        await db.commit()
        await db.refresh(researcher)

    def _get_available_services(self) -> List[str]:
        return ["email", "company", "linkedin", "pubmed"]

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
