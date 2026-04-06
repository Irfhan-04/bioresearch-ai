"""
Enrichment Service Tests
Test lead enrichment functionality
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead
from app.models.user import User
from app.services.enrichment_service import get_enrichment_service


@pytest.mark.asyncio
@pytest.mark.service
class TestEnrichmentService:
    """Test enrichment service"""

    async def test_enrich_lead_email(
        self, db_session: AsyncSession, test_lead: Lead
    ):
        """Test finding email for lead"""
        service = get_enrichment_service()

        # Remove email first
        test_lead.email = None
        await db_session.commit()

        result = await service.enrich_lead(
            lead=test_lead, db=db_session, services=["email"]
        )

        assert "enrichments" in result
        assert "errors" in result

    async def test_enrich_lead_company(
        self, db_session: AsyncSession, test_lead: Lead
    ):
        """Test enriching company data"""
        service = get_enrichment_service()

        result = await service.enrich_lead(
            lead=test_lead, db=db_session, services=["company"]
        )

        assert result is not None

    async def test_enrich_lead_linkedin(
        self, db_session: AsyncSession, test_lead: Lead
    ):
        """Test finding LinkedIn profile"""
        service = get_enrichment_service()

        result = await service.enrich_lead(
            lead=test_lead, db=db_session, services=["linkedin"]
        )

        assert result is not None

    async def test_enrich_lead_all_services(
        self, db_session: AsyncSession, test_lead: Lead
    ):
        """Test enriching with all services"""
        service = get_enrichment_service()

        result = await service.enrich_lead(lead=test_lead, db=db_session, services=None)

        assert "enrichments" in result

    async def test_batch_enrichment(
        self, db_session: AsyncSession, test_user: User, test_leads: list[Lead]
    ):
        """Test batch lead enrichment"""
        service = get_enrichment_service()

        lead_ids = [lead.id for lead in test_leads[:3]]

        result = await service.enrich_leads_batch(
            lead_ids=lead_ids, user=test_user, db=db_session, services=["email"]
        )

        assert result["total"] == 3
        assert result["successful"] + result["failed"] == 3

    async def test_enrichment_status(
        self, db_session: AsyncSession, test_lead: Lead
    ):
        """Test getting enrichment status"""
        service = get_enrichment_service()

        status = await service.get_enrichment_status(test_lead)

        assert "lead_id" in status
        assert "enriched_fields" in status
        assert "missing_fields" in status
        assert "completion_percentage" in status
