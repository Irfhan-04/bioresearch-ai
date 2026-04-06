"""
Enrichment Service - Production Quality
Email finding, company data, and lead enrichment
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import Cache, CacheKey
from app.core.config import settings
from app.models.lead import Lead
from app.models.user import User
from app.services.linkedin_service import get_linkedin_service
from app.services.pubmed_enrichment import get_pubmed_enrichment_service
from app.services.email_finder import get_email_finder
from app.services.company_enricher import get_company_enricher
from app.services.quota_manager import get_quota_manager


class EnrichmentService:
    """
    Lead enrichment service

    Features:
    - Email finding (Hunter.io, Apollo, etc.)
    - Company data (Clearbit, Crunchbase)
    - Social profiles (LinkedIn, Twitter)
    - Phone number validation
    - Caching for cost optimization
    """

    def __init__(self):
        """Initialize enrichment service"""
        self.hunter_api_key = settings.HUNTER_API_KEY
        self.clearbit_api_key = settings.CLEARBIT_API_KEY
        self.proxycurl_api_key = settings.PROXYCURL_API_KEY

    async def enrich_lead(
        self, lead: Lead, db: AsyncSession, services: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Enrich a single lead

        Args:
            lead: Lead to enrich
            db: Database session
            services: List of services to use (None = all available)

        Returns:
            Enrichment results
        """
        results = {"lead_id": str(lead.id), "enrichments": {}, "errors": []}

        # Determine which services to use
        services = services or self._get_available_services()

        # Run enrichment tasks
        tasks = []

        if "email" in services and not lead.email:
            tasks.append(("email", self._find_email(lead)))

        if "company" in services and lead.company:
            tasks.append(("company", self._enrich_company(
                lead.company, pi_name=lead.name, lead=lead
            )))

        if "linkedin" in services and lead.name and lead.company:
            tasks.append(("linkedin", self._find_linkedin(lead)))

        if "pubmed" in services and lead.name:
            tasks.append(("pubmed", self._enrich_pubmed(lead, db)))

        # Execute all tasks concurrently
        if tasks:
            enrichment_results = await asyncio.gather(
                *[task for _, task in tasks], return_exceptions=True
            )

            for (service, _), result in zip(tasks, enrichment_results):
                if isinstance(result, Exception):
                    results["errors"].append({"service": service, "error": str(result)})
                else:
                    results["enrichments"][service] = result

        # Update lead with enrichments
        if results["enrichments"]:
            await self._apply_enrichments(lead, results["enrichments"], db)

        return results

    async def enrich_leads_batch(
        self,
        lead_ids: List[UUID],
        user: User,
        db: AsyncSession,
        services: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Enrich multiple leads

        Args:
            lead_ids: List of lead IDs
            user: User performing enrichment
            db: Database session
            services: Services to use

        Returns:
            Batch enrichment results
        """
        results = {"total": len(lead_ids), "successful": 0, "failed": 0, "results": []}

        for lead_id in lead_ids:
            try:
                # Get lead
                result = await db.execute(
                    select(Lead).where(Lead.id == lead_id, Lead.user_id == user.id)
                )
                lead = result.scalar_one_or_none()

                if not lead:
                    results["failed"] += 1
                    results["results"].append(
                        {"lead_id": str(lead_id), "status": "not_found"}
                    )
                    continue

                # Enrich lead
                enrichment_result = await self.enrich_lead(lead, db, services)

                results["successful"] += 1
                results["results"].append(
                    {"lead_id": str(lead_id), "status": "success", **enrichment_result}
                )

            except Exception as e:
                results["failed"] += 1
                results["results"].append(
                    {"lead_id": str(lead_id), "status": "error", "error": str(e)}
                )

        return results

    async def _find_email(self, lead: Lead) -> Optional[Dict[str, Any]]:
        """
        Find email address for a lead using the four-layer EmailFinder waterfall.

        Layer 0: NIH email (from Step 4 grant record)
        Layer 1: Academic institution pattern (.edu domains)
        Layer 2: Hunter.io domain search (free 25/month, score ≥ 70 only)
        Layer 3: Pattern fallback (always free, honest low confidence)

        The mock is no longer called. All sources are labelled accurately.
        """
        cache_key = CacheKey.enrichment(str(lead.id), "email")
        cached = await Cache.get(cache_key)
        if cached:
            return cached

        finder = get_email_finder()
        quota_manager = get_quota_manager()
        result = await finder.find_email(lead, quota_manager)

        if result and result.get("email"):
            await Cache.set(cache_key, result, ttl=86_400 * 30)

        return result if result and result.get("email") else None

    async def _enrich_company(
        self,
        company_name: str,
        pi_name: Optional[str] = None,
        lead: Optional[Lead] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Enrich company data using the CompanyEnricher waterfall.

        Priority:
          1. NIH data already on the lead (Step 4) — free, no API call
          2. Clearbit API (50/month, quota-gated for pharma leads)
          3. Structural mock (fallback, always available)
        """
        cache_key = f"company:{company_name.lower().replace(' ', '_')[:80]}"
        cached = await Cache.get(cache_key)
        if cached:
            return cached

        enricher = get_company_enricher()
        quota_manager = get_quota_manager()

        result = await enricher.enrich_company(
            company_name=company_name,
            lead=lead,
            quota_manager=quota_manager,
        )

        ttl = 86_400 * 30 if result.get("source") in ("clearbit", "nih_reporter") else 86_400
        await Cache.set(cache_key, result, ttl=ttl)
        return result

    async def _find_linkedin(self, lead: Lead) -> Optional[Dict[str, Any]]:
        """
        Find LinkedIn profile URL using the free LinkedInService.

        Strategy (in order):
          1. Redis cache (7-day TTL)
          2. Google Custom Search API (100 req/day free)
          3. DuckDuckGo HTML scrape (free fallback)
          4. URL pattern generation (always-free baseline)

        Replaces Phase 2.1 mock entirely.
        """
        service = get_linkedin_service()
        result = await service.find_profile_url(lead)

        if result.get("url") and result.get("confidence", 0) >= 0.50:
            return result

        return None

    async def _enrich_pubmed(self, lead: Lead, db: AsyncSession) -> dict:
        """
        Delegate to PubMedEnrichmentService and return the enrichment result dict.
        Called when "pubmed" is in the requested services list.
        """
        svc = get_pubmed_enrichment_service()
        return await svc.enrich_lead_pubmed(lead=lead, db=db)

    async def _apply_enrichments(
        self, lead: Lead, enrichments: Dict[str, Any], db: AsyncSession
    ):
        """Apply enrichment data to lead"""
        # Email
        if "email" in enrichments and not lead.email:
            email_data = enrichments["email"]
            if email_data and "email" in email_data:
                lead.email = email_data["email"]
                lead.set_enrichment("email", email_data)

        # Company data
        if "company" in enrichments:
            company_data = enrichments["company"]
            if company_data:
                if "funding" in company_data and not lead.company_funding:
                    lead.company_funding = company_data["funding"].get("stage")
                if "size" in company_data and not lead.company_size:
                    lead.company_size = company_data["size"]
                lead.set_enrichment("company", company_data)

                # If NIH data was found, populate nih_grants slot and apply tags
                if company_data.get("source") == "nih_reporter":
                    grants = company_data.get("nih_grants", [])
                    lead.set_enrichment("nih_grants", {
                        "grants":        grants,
                        "total_grants":  len(grants),
                        "active_grants": sum(1 for g in grants if g.get("is_active")),
                        "max_award":     max(
                            (g.get("award_amount", 0) or 0 for g in grants), default=0
                        ),
                        "score_boost":   company_data.get("score_boost", 0),
                        "enriched_at":   datetime.utcnow().isoformat(),
                    })
                    lead.add_data_source("funding")
                    lead.add_tag("nih-funded")
                    if any(g.get("is_active") for g in grants):
                        lead.add_tag("active-grant")

        # LinkedIn — only write to lead.linkedin_url if confidence is high enough
        if "linkedin" in enrichments:
            linkedin_data = enrichments["linkedin"]
            if linkedin_data and linkedin_data.get("url"):
                confidence = linkedin_data.get("confidence", 0.0)
                lead.set_enrichment("linkedin", linkedin_data)
                lead.add_data_source("linkedin")
                if not lead.linkedin_url and confidence >= 0.75:
                    lead.linkedin_url = linkedin_data["url"]
                    lead.add_tag("linkedin-verified")

        # Save changes
        await db.commit()
        await db.refresh(lead)

    def _get_available_services(self) -> List[str]:
        """Get list of available enrichment services"""
        services = []

        # Always available (mock or real)
        services.extend(["email", "company", "linkedin"])
        # PubMed enrichment: free, always available when Biopython is installed
        services.append("pubmed")

        return services

    async def get_enrichment_status(self, lead: Lead) -> Dict[str, Any]:
        """
        Get enrichment status for a lead

        Returns which fields are enriched and which are missing
        """
        status = {
            "lead_id": str(lead.id),
            "enriched_fields": [],
            "missing_fields": [],
            "enrichment_data": lead.enrichment_data or {},
        }

        # Check which fields are enriched
        if lead.email:
            status["enriched_fields"].append("email")
        else:
            status["missing_fields"].append("email")

        if lead.linkedin_url:
            status["enriched_fields"].append("linkedin")
        else:
            status["missing_fields"].append("linkedin")

        if lead.phone:
            status["enriched_fields"].append("phone")
        else:
            status["missing_fields"].append("phone")

        if lead.company_funding and lead.company_funding != "Unknown":
            status["enriched_fields"].append("company_data")
        else:
            status["missing_fields"].append("company_data")

        status["completion_percentage"] = (
            len(status["enriched_fields"])
            / (len(status["enriched_fields"]) + len(status["missing_fields"]))
            * 100
        )

        return status


# Singleton instance
_enrichment_service: Optional[EnrichmentService] = None


def get_enrichment_service() -> EnrichmentService:
    """
    Get singleton EnrichmentService instance

    Usage:
        service = get_enrichment_service()
        result = await service.enrich_lead(lead, db)
    """
    global _enrichment_service

    if _enrichment_service is None:
        _enrichment_service = EnrichmentService()

    return _enrichment_service


__all__ = [
    "EnrichmentService",
    "get_enrichment_service",
]
