"""Enrichment Service Tests."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.researcher import Researcher
from app.models.user import User
from app.services.enrichment_service import get_enrichment_service


@pytest.fixture
async def test_researcher(db_session: AsyncSession, test_user: User) -> Researcher:
    researcher = Researcher(
        user_id=test_user.id,
        name="Dr. John Smith",
        title="Principal Scientist",
        company="BioTech Inc",
        location="Cambridge, MA",
        status="NEW",
    )
    db_session.add(researcher)
    await db_session.commit()
    await db_session.refresh(researcher)
    return researcher


@pytest.fixture
async def test_researchers(db_session: AsyncSession, test_user: User) -> list[Researcher]:
    records = []
    for i in range(3):
        researcher = Researcher(
            user_id=test_user.id,
            name=f"Dr. Researcher {i}",
            title="Scientist",
            company=f"Company {i}",
            status="NEW",
        )
        db_session.add(researcher)
        records.append(researcher)
    await db_session.commit()
    for record in records:
        await db_session.refresh(record)
    return records


@pytest.mark.asyncio
@pytest.mark.service
class TestEnrichmentService:
    async def test_enrich_researcher_email(self, db_session: AsyncSession, test_researcher: Researcher):
        service = get_enrichment_service()
        result = await service.enrich_researcher(researcher=test_researcher, db=db_session, services=["email"])
        assert "enrichments" in result
        assert "errors" in result

    async def test_enrich_researcher_company(self, db_session: AsyncSession, test_researcher: Researcher):
        service = get_enrichment_service()
        result = await service.enrich_researcher(researcher=test_researcher, db=db_session, services=["company"])
        assert result is not None

    async def test_batch_enrichment(self, db_session: AsyncSession, test_user: User, test_researchers: list[Researcher]):
        service = get_enrichment_service()
        researcher_ids = [r.id for r in test_researchers]
        result = await service.enrich_researchers_batch(
            researcher_ids=researcher_ids,
            user=test_user,
            db=db_session,
            services=["email"],
        )
        assert result["total"] == 3

    async def test_enrichment_status(self, test_researcher: Researcher):
        service = get_enrichment_service()
        status = await service.get_enrichment_status(test_researcher)
        assert "researcher_id" in status
        assert "completion_percentage" in status
