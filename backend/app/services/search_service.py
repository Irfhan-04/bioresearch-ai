"""
Search Service
Handles search execution, history tracking, and result management.
Scoring is delegated to ScoringService (Phase 2.5).
"""

import time
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead
from app.models.search import Search
from app.models.user import User
from app.services.data_source_manager import (DataSourceType,
                                              get_data_source_manager)


class SearchService:
    """
    Service for executing searches and managing search history
    """

    def __init__(self):
        """Initialize search service."""
        self.data_source_manager = get_data_source_manager()

    async def execute_search(
        self,
        query: str,
        search_type: str,
        user: User,
        db: AsyncSession,
        filters: Optional[Dict] = None,
        save_search: bool = False,
        saved_name: Optional[str] = None,
        create_leads: bool = True,
        max_results: int = 50,
    ) -> Dict:
        """
        Execute a search and optionally create leads

        Args:
            query: Search query
            search_type: Type of search (pubmed, linkedin, etc.)
            user: User executing search
            db: Database session
            filters: Additional filters
            save_search: Whether to save this search
            saved_name: Name for saved search
            create_leads: Whether to create lead records
            max_results: Maximum results to return

        Returns:
            Search results dictionary
        """
        start_time = time.time()

        # Map search type to data source
        source_mapping = {
            "pubmed": DataSourceType.PUBMED,
            "linkedin": DataSourceType.LINKEDIN,
            "conference": DataSourceType.CONFERENCE,
            "funding": DataSourceType.FUNDING,
        }

        source = source_mapping.get(search_type)
        if not source:
            raise ValueError(f"Unknown search type: {search_type}")

        # Unpack optional advanced PubMed filters from request filters dict
        pubmed_kwargs = {}
        if filters:
            for field in (
                "journals",
                "mesh_terms",
                "study_type",
                "min_year",
                "max_year",
                "years_back",
            ):
                if field in filters:
                    pubmed_kwargs[field] = filters[field]

        # Execute search across data sources
        search_results = await self.data_source_manager.search(
            query=query,
            sources=[source],
            max_results_per_source=max_results,
            **pubmed_kwargs,
        )

        # Aggregate results
        aggregated = await self.data_source_manager.aggregate_results(
            search_results, deduplicate=True
        )

        # Create leads if requested
        created_leads = []
        lead_ids = []

        if create_leads and aggregated:
            # Normalize the user ID before attaching it to generated leads.
            user_id_str = str(user.id)

            for lead_dict in aggregated:
                # Convert to Lead model
                lead = self._dict_to_lead(lead_dict, user_id_str)

                # Calculate score using the Phase 2.5 scoring service.
                lead.propensity_score = self._calculate_default_score(lead)
                lead.update_priority_tier()

                # Save to database
                db.add(lead)
                created_leads.append(lead)

            await db.commit()

            # Refresh to get IDs
            for lead in created_leads:
                await db.refresh(lead)
                lead_ids.append(str(lead.id))

            # Update ranks
            await self._update_lead_ranks(user_id_str, db)

        # Calculate execution time
        execution_time = int((time.time() - start_time) * 1000)

        # Create search history record
        search_record = Search(
            user_id=user.id,
            query=query,
            search_type=search_type,
            filters=filters or {},
            results_count=len(aggregated),
            results_snapshot=lead_ids,
            is_saved=save_search,
            saved_name=saved_name,
            execution_time_ms=execution_time,
        )

        db.add(search_record)
        await db.commit()
        await db.refresh(search_record)

        # Update user usage stats
        user.increment_usage("searches_this_month")
        if created_leads:
            user.increment_usage("leads_created_this_month", len(created_leads))
        await db.commit()

        # Return results
        return {
            "search_id": str(search_record.id),
            "query": query,
            "search_type": search_type,
            "results_count": len(aggregated),
            "leads_created": len(created_leads),
            "execution_time_ms": execution_time,
            "results": aggregated if not create_leads else [],
            "lead_ids": lead_ids if create_leads else [],
            "is_saved": save_search,
            "saved_name": saved_name,
        }

    def _calculate_default_score(self, lead: Lead) -> int:
        """Calculate lead propensity score using the Phase 2.5 ScoringService."""
        try:
            from app.services.scoring_service import get_scoring_service

            score, _ = get_scoring_service().score_lead_sync(lead)
            return score
        except Exception as exc:
            logger.warning("ScoringService failed, using baseline: %s", exc)
            base = 50
            if lead.email:
                base += 8
            if lead.linkedin_url:
                base += 5
            if lead.recent_publication:
                base += 10
            if lead.company_funding:
                base += 5
            if lead.publication_count and lead.publication_count > 0:
                base += min(lead.publication_count * 2, 12)
            nih = (lead.enrichment_data or {}).get("nih_grants", {})
            if nih.get("active_grants", 0) > 0:
                base += 10
            return min(base, 100)

    async def get_search_history(
        self,
        user: User,
        db: AsyncSession,
        page: int = 1,
        size: int = 50,
        saved_only: bool = False,
    ) -> tuple[List[Search], int]:
        """
        Get user's search history

        Args:
            user: User
            db: Database session
            page: Page number
            size: Items per page
            saved_only: Only return saved searches

        Returns:
            Tuple of (searches, total_count)
        """
        from sqlalchemy import func

        # Build query
        query = select(Search).where(Search.user_id == user.id)

        if saved_only:
            query = query.where(Search.is_saved == True)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar()

        # Get paginated results
        query = query.order_by(Search.created_at.desc())
        query = query.offset((page - 1) * size).limit(size)

        result = await db.execute(query)
        searches = result.scalars().all()

        return searches, total

    async def save_search(
        self, search_id: str, name: str, user: User, db: AsyncSession
    ) -> Search:
        """
        Save a search for later reference

        Args:
            search_id: Search ID
            name: Name for saved search
            user: User
            db: Database session

        Returns:
            Updated search record
        """
        from uuid import UUID

        from sqlalchemy import and_

        result = await db.execute(
            select(Search).where(
                and_(Search.id == UUID(search_id), Search.user_id == user.id)
            )
        )
        search = result.scalar_one_or_none()

        if not search:
            raise ValueError("Search not found")

        search.save_search(name)
        await db.commit()
        await db.refresh(search)

        return search

    async def rerun_search(
        self, search_id: str, user: User, db: AsyncSession, create_leads: bool = True
    ) -> Dict:
        """
        Re-run a previous search

        Args:
            search_id: Previous search ID
            user: User
            db: Database session
            create_leads: Whether to create new leads

        Returns:
            New search results
        """
        from uuid import UUID

        from sqlalchemy import and_

        # Get original search
        result = await db.execute(
            select(Search).where(
                and_(Search.id == UUID(search_id), Search.user_id == user.id)
            )
        )
        original_search = result.scalar_one_or_none()

        if not original_search:
            raise ValueError("Search not found")

        # Re-execute with original parameters
        return await self.execute_search(
            query=original_search.query,
            search_type=original_search.search_type,
            user=user,
            db=db,
            filters=original_search.filters,
            save_search=False,
            create_leads=create_leads,
        )

    def _dict_to_lead(self, lead_dict: Dict, user_id: str) -> Lead:
        """
        Convert dictionary to Lead model

        Args:
            lead_dict: Lead data dictionary
            user_id: User ID as string

        Returns:
            Lead model instance
        """
        # Determine primary data source
        sources = lead_dict.get("data_sources", ["unknown"])
        primary_source = sources[0] if sources else "unknown"

        # Convert based on source
        if primary_source == "pubmed":
            lead = self.data_source_manager.pubmed_service.convert_to_lead_model(
                lead_dict, user_id
            )
        elif primary_source == "conference":
            lead = self.data_source_manager.conference_service.convert_to_lead_model(
                lead_dict, user_id
            )
        elif primary_source == "funding":
            lead = self.data_source_manager.funding_service.convert_to_lead_model(
                lead_dict, user_id
            )
        else:
            # Generic fallback
            lead = Lead(
                user_id=user_id,
                name=lead_dict.get("name", "Unknown"),
                title=lead_dict.get("title"),
                company=lead_dict.get("company"),
                location=lead_dict.get("location"),
                email=lead_dict.get("email"),
                recent_publication=lead_dict.get("recent_publication", False),
                status="NEW",
            )

            for source in sources:
                lead.add_data_source(source)

        return lead

    async def _update_lead_ranks(self, user_id: str, db: AsyncSession):
        """Update lead ranks based on scores"""
        from uuid import UUID

        result = await db.execute(
            select(Lead)
            .where(Lead.user_id == UUID(user_id))
            .order_by(Lead.propensity_score.desc())
        )

        for rank, lead in enumerate(result.scalars().all(), start=1):
            lead.rank = rank

        await db.commit()


# Singleton instance
_search_service: Optional[SearchService] = None


def get_search_service() -> SearchService:
    """
    Get singleton SearchService instance

    Usage:
        service = get_search_service()
        results = await service.execute_search(
            "DILI 3D models",
            "pubmed",
            user,
            db
        )
    """
    global _search_service

    if _search_service is None:
        _search_service = SearchService()

    return _search_service


__all__ = [
    "SearchService",
    "get_search_service",
]
