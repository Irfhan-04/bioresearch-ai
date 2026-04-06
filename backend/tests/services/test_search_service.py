"""
Search Service Tests
Test search execution, history, and result management
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead
from app.models.search import Search
from app.models.user import User
from app.services.search_service import get_search_service


@pytest.mark.asyncio
@pytest.mark.service
class TestSearchService:
    """Test search service functionality"""

    async def test_execute_search_pubmed(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test executing PubMed search"""
        service = get_search_service()

        result = await service.execute_search(
            query="DILI 3D models",
            search_type="pubmed",
            user=test_user,
            db=db_session,
            max_results=5,
        )

        assert result["search_id"] is not None
        assert result["query"] == "DILI 3D models"
        assert result["search_type"] == "pubmed"
        assert result["results_count"] >= 0
        assert result["execution_time_ms"] > 0

    async def test_execute_search_creates_leads(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test search creates lead records"""
        service = get_search_service()

        result = await service.execute_search(
            query="hepatotoxicity",
            search_type="pubmed",
            user=test_user,
            db=db_session,
            create_leads=True,
            max_results=3,
        )

        assert result["leads_created"] >= 0
        assert len(result["lead_ids"]) == result["leads_created"]

    async def test_execute_search_with_filters(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test search with filters"""
        service = get_search_service()

        filters = {"years_back": 2}

        result = await service.execute_search(
            query="organoids",
            search_type="pubmed",
            user=test_user,
            db=db_session,
            filters=filters,
        )

        assert result["results_count"] >= 0

    async def test_save_search(
        self, db_session: AsyncSession, test_user: User, test_search: Search
    ):
        """Test saving a search"""
        service = get_search_service()

        saved = await service.save_search(
            search_id=str(test_search.id),
            name="My Saved Search",
            user=test_user,
            db=db_session,
        )

        assert saved.is_saved is True
        assert saved.saved_name == "My Saved Search"

    async def test_get_search_history(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test retrieving search history"""
        service = get_search_service()

        # Create some searches
        for i in range(3):
            await service.execute_search(
                query=f"test query {i}",
                search_type="pubmed",
                user=test_user,
                db=db_session,
                max_results=1,
            )

        searches, total = await service.get_search_history(
            user=test_user, db=db_session, page=1, size=10
        )

        assert total >= 3
        assert len(searches) >= 3

    async def test_rerun_search(
        self, db_session: AsyncSession, test_user: User, test_search: Search
    ):
        """Test re-running a previous search"""
        service = get_search_service()

        result = await service.rerun_search(
            search_id=str(test_search.id), user=test_user, db=db_session
        )

        assert result["query"] == test_search.query
        assert result["search_type"] == test_search.search_type

    async def test_invalid_search_type(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test search with invalid type"""
        service = get_search_service()

        with pytest.raises(ValueError):
            await service.execute_search(
                query="test",
                search_type="invalid_type",
                user=test_user,
                db=db_session,
            )