"""
Pipeline Service - WITHOUT SCORING (Phase 2)
Handles pipeline creation, execution, and management
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead
from app.models.pipeline import Pipeline, PipelineSchedule, PipelineStatus
from app.models.user import User
from app.services.data_quality_service import get_data_quality_service
from app.services.data_source_manager import DataSourceType, get_data_source_manager
from app.services.email_service import get_email_service
from app.services.search_service import get_search_service
from app.services.smart_alert_service import get_smart_alert_service
from app.services.webhook_service import get_webhook_service


PIPELINE_TEMPLATES: dict = {
    "dili_toxicology": {
        "name": "DILI & Liver Toxicology Researchers",
        "description": "Finds PIs publishing on drug-induced liver injury, hepatotoxicity, and 3D hepatocyte models.",
        "schedule": "weekly",
        "config": {
            "search_queries": [
                {"source": "pubmed", "query": "drug-induced liver injury 3D hepatocyte models"},
                {"source": "pubmed", "query": "hepatotoxicity in vitro organoid"},
                {"source": "funding", "query": "DILI liver safety pharmacology"},
                {"source": "conference", "query": "hepatotoxicity liver injury toxicology"},
            ],
            "filters": {"min_score": 55},
            "enrichment": {"auto_enrich": True, "services": ["email", "company"]},
            "notifications": {"email_on_completion": True},
        },
    },
    "oncology_research": {
        "name": "Oncology Drug Safety Researchers",
        "description": "Targets cancer researchers working on drug safety, biomarker discovery, and translational models.",
        "schedule": "weekly",
        "config": {
            "search_queries": [
                {"source": "pubmed", "query": "oncology drug safety biomarker preclinical"},
                {"source": "funding", "query": "cancer drug toxicity biomarker"},
                {"source": "conference", "query": "oncology safety pharmacology"},
            ],
            "filters": {"min_score": 55},
            "enrichment": {"auto_enrich": True, "services": ["email", "company"]},
            "notifications": {"email_on_completion": True},
        },
    },
    "pharma_safety_scientists": {
        "name": "Pharma Safety Scientists",
        "description": "Targets Directors and VPs of Safety/Toxicology at pharma and biotech companies.",
        "schedule": "monthly",
        "config": {
            "search_queries": [
                {"source": "pubmed", "query": "safety pharmacology preclinical ADME"},
                {"source": "funding", "query": "drug safety assessment new approach methodologies"},
            ],
            "filters": {"min_score": 65},
            "enrichment": {"auto_enrich": True, "services": ["email", "company", "linkedin"]},
            "notifications": {"email_on_completion": True, "email_on_error": True},
        },
    },
    "nih_grant_holders": {
        "name": "Active NIH Grant Holders",
        "description": "Finds PIs with active NIH R01/U01 grants in liver disease, toxicology, and drug safety.",
        "schedule": "monthly",
        "config": {
            "search_queries": [
                {"source": "funding", "query": "hepatotoxicity drug safety liver"},
                {"source": "funding", "query": "drug-induced organ injury biomarker"},
            ],
            "filters": {"min_score": 60},
            "enrichment": {"auto_enrich": True, "services": ["email"]},
            "notifications": {"email_on_completion": True},
        },
    },
}


class PipelineService:
    """
    Pipeline execution and management service

    Features:
    - Pipeline creation and configuration
    - Scheduled execution
    - Manual triggering
    - Result tracking
    - Email notifications
    - Webhook triggers
    """

    def __init__(self):
        """Initialize pipeline service"""
        self.search_service = get_search_service()
        # SCORING DISABLED - Phase 2 feature
        # self.scoring_service = ScoringService()
        self.email_service = get_email_service()
        self.webhook_service = get_webhook_service()
        self.smart_alert_service = get_smart_alert_service()

    @staticmethod
    def list_templates() -> List[Dict[str, Any]]:
        return [
            {
                "key": key,
                "name": template["name"],
                "description": template["description"],
                "schedule": template["schedule"],
                "query_count": len(template["config"]["search_queries"]),
            }
            for key, template in PIPELINE_TEMPLATES.items()
        ]

    @staticmethod
    def get_template(template_key: str) -> Optional[Dict[str, Any]]:
        return PIPELINE_TEMPLATES.get(template_key)

    async def create_from_template(
        self,
        user: User,
        db: AsyncSession,
        template_key: str,
        name_override: Optional[str] = None,
    ) -> Pipeline:
        template = self.get_template(template_key)
        if not template:
            raise ValueError(f"Unknown template '{template_key}'. Available: {list(PIPELINE_TEMPLATES)}")

        schedule_map = {
            "manual": PipelineSchedule.MANUAL,
            "daily": PipelineSchedule.DAILY,
            "weekly": PipelineSchedule.WEEKLY,
            "monthly": PipelineSchedule.MONTHLY,
        }
        return await self.create_pipeline(
            user=user,
            db=db,
            name=name_override or template["name"],
            description=template["description"],
            schedule=schedule_map.get(template["schedule"], PipelineSchedule.WEEKLY),
            cron_expression=None,
            config=template["config"],
        )

    async def create_pipeline(
        self,
        user: User,
        db: AsyncSession,
        name: str,
        description: Optional[str],
        schedule: PipelineSchedule,
        cron_expression: Optional[str],
        config: Dict[str, Any],
    ) -> Pipeline:
        """
        Create new pipeline

        Args:
            user: User creating pipeline
            db: Database session
            name: Pipeline name
            description: Pipeline description
            schedule: Schedule type
            cron_expression: Custom cron expression
            config: Pipeline configuration

        Returns:
            Created pipeline
        """
        # Validate config
        self._validate_config(config)

        # Create pipeline
        pipeline = Pipeline(
            user_id=user.id,
            name=name,
            description=description,
            schedule=schedule,
            cron_expression=cron_expression,
            config=config,
            status=PipelineStatus.ACTIVE,
        )

        # Calculate next run
        if schedule != PipelineSchedule.MANUAL:
            pipeline.next_run_at = pipeline.calculate_next_run()

        db.add(pipeline)
        await db.commit()
        await db.refresh(pipeline)

        return pipeline

    async def execute_pipeline(
        self,
        pipeline: Pipeline,
        user: User,
        db: AsyncSession,
        override_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute pipeline

        Args:
            pipeline: Pipeline to execute
            user: User executing pipeline
            db: Database session
            override_config: Temporary config override

        Returns:
            Execution results
        """
        start_time = datetime.now()

        # Use override config or pipeline config
        config = override_config or pipeline.config

        # Mark as running
        pipeline.mark_running()
        await db.commit()

        results = {
            "pipeline_id": str(pipeline.id),
            "started_at": start_time.isoformat(),
            "leads_found": 0,
            "leads_created": 0,
            "leads_updated": 0,
            "leads_skipped": 0,
            "errors": [],
            "data_sources_used": [],
        }

        try:
            # Execute search queries
            search_queries = config.get("search_queries", [])
            all_leads = []

            for query_config in search_queries:
                try:
                    # Execute search
                    source = query_config.get("source", "pubmed")

                    if source == "all":
                        search_result = await self.run_multi_source_pipeline(
                            query=query_config.get("query"),
                            user=user,
                            db=db,
                            filters=config.get("filters", {}),
                            run_enrichment=config.get("enrichment", {}).get("auto_enrich", False),
                        )
                        results["leads_found"] += search_result.get("leads_found", 0)
                        results["leads_created"] += search_result.get("leads_saved", 0)
                        results["data_sources_used"].extend(search_result.get("sources_used", []))
                    else:
                        search_result = await self.search_service.execute_search(
                            query=query_config.get("query"),
                            search_type=source,
                            user=user,
                            db=db,
                            filters=config.get("filters", {}),
                            create_leads=True,
                        )

                        results["leads_found"] += search_result["results_count"]
                        results["leads_created"] += search_result["leads_created"]
                        results["data_sources_used"].append(source)

                except Exception as e:
                    results["errors"].append(
                        {"query": query_config.get("query"), "error": str(e)}
                    )

            # Apply filters
            filters = config.get("filters", {})
            if filters.get("min_score"):
                # Re-query leads to get those above threshold
                min_score = filters["min_score"]
                result = await db.execute(
                    select(Lead).where(
                        Lead.user_id == user.id, Lead.propensity_score >= min_score
                    )
                )
                filtered_leads = result.scalars().all()

            # Apply enrichment if configured
            enrichment_config = config.get("enrichment", {})
            if enrichment_config:
                await self._apply_enrichment(
                    user=user, db=db, enrichment_config=enrichment_config
                )

            # Calculate execution time
            end_time = datetime.now()
            execution_time = int((end_time - start_time).total_seconds())

            results["execution_time_seconds"] = execution_time
            results["completed_at"] = end_time.isoformat()

            # Mark as complete
            success = len(results["errors"]) == 0
            pipeline.mark_run_complete(
                success=success,
                results=results,
                next_run_at=pipeline.calculate_next_run(),
            )

            await db.commit()

            # Send notification if configured
            notifications = config.get("notifications", {})
            if notifications.get("email_on_completion") and success:
                await self._send_completion_email(user=user, pipeline=pipeline, results=results)
            elif notifications.get("email_on_error") and not success:
                await self._send_error_email(user=user, pipeline=pipeline, results=results)

            if success:
                await self.webhook_service.notify_pipeline_completed(user, pipeline.name, str(pipeline.id), results, db)
                await self.smart_alert_service.evaluate_all_rules(user, db, {"pipeline_id": str(pipeline.id), "results": results})
            else:
                await self.webhook_service.notify_pipeline_failed(user, pipeline.name, str(pipeline.id), "Pipeline completed with errors", db)

            return results

        except Exception as e:
            # Mark as failed
            error_results = {**results, "errors": [{"error": str(e)}]}

            pipeline.mark_run_complete(success=False, results=error_results)

            await db.commit()

            # Send error notification
            notifications = config.get("notifications", {})
            if notifications.get("email_on_error"):
                await self._send_error_email(user=user, pipeline=pipeline, results=error_results)
            await self.webhook_service.notify_pipeline_failed(user, pipeline.name, str(pipeline.id), str(e), db)

            raise

    async def run_multi_source_pipeline(
        self,
        query: str,
        user: User,
        db: AsyncSession,
        sources: Optional[List[str]] = None,
        max_results_per_source: int = 50,
        run_enrichment: bool = True,
        enrichment_services: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a parallel multi-source search with quality gating."""
        import time

        from app.services.enrichment_service import get_enrichment_service

        start = time.monotonic()

        source_names = sources or ["pubmed", "conference", "funding"]
        manager = get_data_source_manager()
        quality_svc = get_data_quality_service()
        enrichment_svc = get_enrichment_service()

        source_type_map = {
            "pubmed": DataSourceType.PUBMED,
            "conference": DataSourceType.CONFERENCE,
            "funding": DataSourceType.FUNDING,
            "linkedin": DataSourceType.LINKEDIN,
        }

        active_sources = [
            source_type_map[name]
            for name in source_names
            if name in source_type_map and manager.is_source_available(source_type_map[name])
        ]

        if not active_sources:
            return {"error": "No active sources available", "leads_saved": 0}

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

        raw_results = await manager.search(
            query=query,
            sources=active_sources,
            max_results_per_source=max_results_per_source,
            **pubmed_kwargs,
        )
        all_lead_dicts = await manager.aggregate_results(raw_results, deduplicate=True)

        source_breakdown = {
            source: len(raw_results.get(source, {}).get("leads", []))
            for source in source_names
        }

        passing_dicts, quality_report = quality_svc.validate_batch(
            all_lead_dicts,
            deduplicate=False,
        )

        saved_leads = []
        for lead_dict in passing_dicts:
            sources_used = lead_dict.get("data_sources", [])

            if "pubmed" in sources_used:
                lead_obj = manager.pubmed_service.convert_to_lead_model(lead_dict, str(user.id))
            elif "conference" in sources_used:
                lead_obj = manager.conference_service.convert_to_lead_model(lead_dict, str(user.id))
            elif "funding" in sources_used:
                lead_obj = manager.funding_service.convert_to_lead_model(lead_dict, str(user.id))
            else:
                lead_obj = manager.pubmed_service.convert_to_lead_model(lead_dict, str(user.id))

            db.add(lead_obj)
            saved_leads.append(lead_obj)

        if saved_leads:
            await db.commit()
            for lead_obj in saved_leads:
                await db.refresh(lead_obj)

        enrichment_summary: Dict[str, Any] = {"skipped": True}
        if run_enrichment and saved_leads:
            enrich_services = enrichment_services or ["email", "company"]
            top_leads = sorted(
                saved_leads,
                key=lambda lead: (lead.propensity_score or 0),
                reverse=True,
            )[:10]

            enrich_results = {"attempted": len(top_leads), "succeeded": 0, "errors": []}
            for lead_obj in top_leads:
                try:
                    await enrichment_svc.enrich_lead(
                        lead=lead_obj,
                        db=db,
                        services=enrich_services,
                    )
                    enrich_results["succeeded"] += 1
                except Exception as exc:
                    enrich_results["errors"].append(str(exc))

            enrichment_summary = enrich_results

        elapsed = round(time.monotonic() - start, 2)

        return {
            "query": query,
            "sources_used": [source.value for source in active_sources],
            "source_breakdown": source_breakdown,
            "leads_found": len(all_lead_dicts),
            "leads_saved": len(saved_leads),
            "leads_rejected": quality_report.rejected,
            "quality_report": {
                "total_candidates": quality_report.total_candidates,
                "avg_completeness": quality_report.avg_completeness,
                "rejection_reasons": quality_report.rejection_reasons,
            },
            "enrichment_summary": enrichment_summary,
            "execution_time_seconds": elapsed,
        }

    async def queue_pipeline_run(
        self,
        pipeline: Pipeline,
        user: User,
        db: AsyncSession,
        override_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Queue pipeline for background execution

        Args:
            pipeline: Pipeline to run
            user: User
            db: Database session
            override_config: Config override

        Returns:
            Job ID
        """
        # For MVP: Execute immediately
        # In production: Use Celery
        job_id = str(uuid.uuid4())

        # Execute in background (simplified)
        asyncio.create_task(self.execute_pipeline(pipeline, user, db, override_config))

        return job_id

    async def _apply_enrichment(
        self, user: User, db: AsyncSession, enrichment_config: Dict[str, Any]
    ):
        """Apply enrichment to recent leads"""
        from app.services.enrichment_service import get_enrichment_service

        enrichment_service = get_enrichment_service()

        # Get recent leads without email
        if enrichment_config.get("find_email"):
            result = await db.execute(
                select(Lead)
                .where(Lead.user_id == user.id, Lead.email.is_(None))
                .limit(10)  # Limit to avoid API costs
            )
            leads = result.scalars().all()

            for lead in leads:
                try:
                    await enrichment_service.enrich_lead(
                        lead=lead, db=db, services=["email"]
                    )
                except Exception as e:
                    print(f"Enrichment failed for {lead.id}: {e}")

    async def _send_completion_email(
        self, user: User, pipeline: Pipeline, results: Dict[str, Any]
    ):
        """Send completion notification email"""
        await self.email_service.send_pipeline_completion_email(
            to_email=user.email,
            user_name=user.full_name,
            pipeline_name=pipeline.name,
            leads_created=results["leads_created"],
            execution_time=results["execution_time_seconds"],
        )

    async def _send_error_email(
        self, user: User, pipeline: Pipeline, results: Dict[str, Any]
    ):
        """Send error notification email"""
        await self.email_service.send_pipeline_error_email(
            to_email=user.email,
            user_name=user.full_name,
            pipeline_name=pipeline.name,
            errors=results["errors"],
        )

    def _validate_config(self, config: Dict[str, Any]):
        """Validate pipeline configuration"""
        # Check required fields
        if "search_queries" not in config:
            raise ValueError("Config must include 'search_queries'")

        if not config["search_queries"]:
            raise ValueError("At least one search query required")

        # Validate each query
        for query in config["search_queries"]:
            if "query" not in query:
                raise ValueError("Each query must have 'query' field")
            if "source" not in query:
                raise ValueError("Each query must have 'source' field")

    async def get_pipelines_to_run(self, db: AsyncSession) -> List[Pipeline]:
        """
        Get pipelines that should run now

        Used by scheduler
        """
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)

        result = await db.execute(
            select(Pipeline).where(
                Pipeline.status == PipelineStatus.ACTIVE, Pipeline.next_run_at <= now
            )
        )

        return result.scalars().all()


# Singleton instance
_pipeline_service: Optional[PipelineService] = None


def get_pipeline_service() -> PipelineService:
    """
    Get singleton PipelineService instance

    Usage:
        service = get_pipeline_service()
        pipeline = await service.create_pipeline(user, db, ...)
    """
    global _pipeline_service

    if _pipeline_service is None:
        _pipeline_service = PipelineService()

    return _pipeline_service


__all__ = [
    "PipelineService",
    "get_pipeline_service",
]
