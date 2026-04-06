"""
Celery Background Tasks
All asynchronous background jobs
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.export import Export
from app.models.pipeline import Pipeline
from app.models.user import User
from app.services.email_service import get_email_service
from app.services.enrichment_service import get_enrichment_service
from app.services.export_service import get_export_service
from app.services.pipeline_service import get_pipeline_service
from app.services.scheduler import get_scheduler
from app.workers.celery_app import celery_app


# Helper to run async functions in Celery
def run_async(coro):
    """Run async function in sync context"""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


# ============================================================================
# PIPELINE TASKS
# ============================================================================


@celery_app.task(
    name="app.workers.tasks.execute_pipeline_task",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
)
def execute_pipeline_task(
    self, pipeline_id: str, user_id: str, override_config: Dict = None
):
    """
    Execute a pipeline in background

    Args:
        pipeline_id: Pipeline ID
        user_id: User ID
        override_config: Optional config override
    """
    try:

        async def _execute():
            async with async_session_factory() as db:
                # Get pipeline
                result = await db.execute(
                    select(Pipeline).where(Pipeline.id == UUID(pipeline_id))
                )
                pipeline = result.scalar_one_or_none()

                if not pipeline:
                    raise ValueError(f"Pipeline {pipeline_id} not found")

                # Get user
                result = await db.execute(select(User).where(User.id == UUID(user_id)))
                user = result.scalar_one_or_none()

                if not user:
                    raise ValueError(f"User {user_id} not found")

                # Execute pipeline
                service = get_pipeline_service()
                results = await service.execute_pipeline(
                    pipeline=pipeline, user=user, db=db, override_config=override_config
                )

                return results

        # Run async function
        results = run_async(_execute())

        return {"status": "success", "pipeline_id": pipeline_id, "results": results}

    except Exception as exc:
        # Retry on failure
        raise self.retry(exc=exc)


@celery_app.task(name="app.workers.tasks.check_scheduled_pipelines")
def check_scheduled_pipelines():
    """Use intelligent scheduler"""

    async def _check():
        async with async_session_factory() as db:
            scheduler = get_scheduler()

            # Get pipelines using intelligent scheduling
            pipelines = await scheduler.get_pipelines_to_execute(
                db=db, limit=10  # Process 10 at a time
            )

            # Queue each pipeline
            for pipeline in pipelines:
                execute_pipeline_task.delay(
                    pipeline_id=str(pipeline.id), user_id=str(pipeline.user_id)
                )

            return len(pipelines)

    count = run_async(_check())
    return {"status": "success", "pipelines_queued": count}


# ============================================================================
# ENRICHMENT TASKS
# ============================================================================


@celery_app.task(name="app.workers.tasks.enrich_lead_task", bind=True, max_retries=3)
def enrich_lead_task(self, lead_id: str, user_id: str, services: List[str] = None):
    """
    Enrich a single lead

    Args:
        lead_id: Lead ID
        user_id: User ID
        services: Services to use
    """
    try:

        async def _enrich():
            async with async_session_factory() as db:
                from app.models.lead import Lead

                # Get lead
                result = await db.execute(select(Lead).where(Lead.id == UUID(lead_id)))
                lead = result.scalar_one_or_none()

                if not lead:
                    raise ValueError(f"Lead {lead_id} not found")

                # Enrich
                service = get_enrichment_service()
                results = await service.enrich_lead(lead=lead, db=db, services=services)

                return results

        results = run_async(_enrich())

        return {"status": "success", "lead_id": lead_id, "results": results}

    except Exception as exc:
        raise self.retry(exc=exc)


# ============================================================================
# EXPORT TASKS
# ============================================================================


@celery_app.task(name="app.workers.tasks.export_data_task", bind=True, max_retries=2)
def export_data_task(self, export_id: str):
    """
    Generate export file

    Args:
        export_id: Export ID
    """
    try:

        async def _export():
            async with async_session_factory() as db:
                service = get_export_service()

                # Execute export
                export = await service.execute_export(export_id=UUID(export_id), db=db)

                # Send notification email
                if export.file_url:
                    result = await db.execute(
                        select(User).where(User.id == export.user_id)
                    )
                    user = result.scalar_one_or_none()

                    if user:
                        email_service = get_email_service()
                        await email_service.send_export_ready_email(
                            to_email=user.email,
                            user_name=user.full_name,
                            file_name=export.file_name,
                            download_url=export.file_url,
                            records_count=export.records_count,
                        )

                return export.to_dict()

        export_data = run_async(_export())

        return {"status": "success", "export_id": export_id, "export": export_data}

    except Exception as exc:
        # Mark export as failed
        async def _mark_failed():
            async with async_session_factory() as db:
                result = await db.execute(
                    select(Export).where(Export.id == UUID(export_id))
                )
                export = result.scalar_one_or_none()

                if export:
                    export.mark_as_failed(str(exc))
                    await db.commit()

        run_async(_mark_failed())
        raise self.retry(exc=exc)


@celery_app.task(name="app.workers.tasks.cleanup_expired_exports")
def cleanup_expired_exports():
    """
    Clean up expired exports

    Runs daily at 2 AM
    """

    async def _cleanup():
        async with async_session_factory() as db:
            service = get_export_service()
            deleted = await service.delete_expired_exports(db, days=7)
            return deleted

    count = run_async(_cleanup())

    return {"status": "success", "deleted_count": count}


# ============================================================================
# EMAIL TASKS
# ============================================================================


@celery_app.task(name="app.workers.tasks.send_email_task")
def send_email_task(email_type: str, **kwargs):
    """
    Send email

    Args:
        email_type: Type of email to send
        **kwargs: Email-specific arguments
    """

    async def _send():
        service = get_email_service()

        if email_type == "welcome":
            return await service.send_welcome_email(**kwargs)
        elif email_type == "pipeline_completion":
            return await service.send_pipeline_completion_email(**kwargs)
        elif email_type == "pipeline_error":
            return await service.send_pipeline_error_email(**kwargs)
        elif email_type == "export_ready":
            return await service.send_export_ready_email(**kwargs)
        elif email_type == "usage_warning":
            return await service.send_usage_warning_email(**kwargs)
        else:
            raise ValueError(f"Unknown email type: {email_type}")

    success = run_async(_send())

    return {"status": "success" if success else "failed", "email_type": email_type}


@celery_app.task(name="app.workers.tasks.send_daily_digests")
def send_daily_digests():
    """Send daily digest emails to active users who have opted in."""

    async def _send():
        from datetime import date, timedelta
        from sqlalchemy import func as sa_func
        from app.models.lead import Lead
        from app.models.usage import UsageEvent, UsageEventType

        async with async_session_factory() as db:
            email_svc = get_email_service()
            yesterday = date.today() - timedelta(days=1)
            users_result = await db.execute(select(User).where(User.is_active == True))
            users = users_result.scalars().all()

            sent = 0
            for user in users:
                if not user.get_preference("email_notifications", True) or not user.email:
                    continue

                leads_result = await db.execute(
                    select(Lead)
                    .where(Lead.user_id == user.id, Lead.created_at >= yesterday)
                    .order_by(Lead.propensity_score.desc())
                    .limit(10)
                )
                new_leads = leads_result.scalars().all()
                if not new_leads:
                    continue

                pipelines_run = (await db.execute(
                    select(sa_func.count(UsageEvent.id)).where(
                        UsageEvent.user_id == user.id,
                        UsageEvent.event_type == UsageEventType.PIPELINE_RUN,
                        UsageEvent.occurred_at >= yesterday,
                    )
                )).scalar() or 0
                searches_run = (await db.execute(
                    select(sa_func.count(UsageEvent.id)).where(
                        UsageEvent.user_id == user.id,
                        UsageEvent.event_type == UsageEventType.SEARCH_EXECUTED,
                        UsageEvent.occurred_at >= yesterday,
                    )
                )).scalar() or 0

                stats = {
                    "leads_today": len(new_leads),
                    "pipelines_run": int(pipelines_run),
                    "searches_run": int(searches_run),
                    "high_value_count": sum(1 for lead in new_leads if (lead.propensity_score or 0) >= 70),
                    "top_leads": [
                        {
                            "name": lead.name,
                            "company": lead.company or "—",
                            "score": lead.propensity_score or 0,
                            "source": (lead.data_sources or ["unknown"])[0],
                        }
                        for lead in new_leads[:5]
                    ],
                }
                await email_svc.send_daily_digest(
                    to_email=user.email,
                    user_name=user.full_name or user.email.split("@")[0],
                    stats=stats,
                )
                sent += 1

        return {"status": "success", "digests_sent": sent}

    return run_async(_send())


# ============================================================================
# MAINTENANCE TASKS
# ============================================================================


@celery_app.task(name="app.workers.tasks.reset_monthly_usage")
def reset_monthly_usage():
    """
    Reset monthly usage counters for all users

    Runs on 1st of each month at midnight
    """

    async def _reset():
        async with async_session_factory() as db:
            result = await db.execute(select(User))
            users = result.scalars().all()

            for user in users:
                user.reset_monthly_usage()

            await db.commit()
            return len(users)

    count = run_async(_reset())

    return {"status": "success", "users_reset": count}


@celery_app.task(name="app.workers.tasks.health_check")
def health_check():
    """
    System health check

    Runs every 5 minutes
    """

    async def _check():
        from app.core.cache import get_async_redis
        from app.core.database import check_db_connection

        # Check database
        db_status = await check_db_connection()

        # Check Redis
        try:
            redis = await get_async_redis()
            await redis.ping()
            cache_status = True
        except Exception:
            cache_status = False

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "database": "healthy" if db_status else "unhealthy",
            "cache": "healthy" if cache_status else "unhealthy",
            "celery": "healthy",
        }

    status = run_async(_check())

    # Log issues if any
    if status["database"] != "healthy" or status["cache"] != "healthy":
        print(f"[HEALTH CHECK WARNING] {status}")

    return status


# ============================================================================
# UTILITY TASKS
# ============================================================================


@celery_app.task(name="app.workers.tasks.recalculate_all_scores")
def recalculate_all_scores():
    """
    Recalculate scores for all leads

    Can be triggered manually or scheduled
    """

    async def _recalculate():
        from app.models.lead import Lead
        from app.services.scoring_service import ScoringService

        async with async_session_factory() as db:
            result = await db.execute(select(Lead))
            leads = result.scalars().all()

            service = ScoringService()

            for lead in leads:
                lead.propensity_score = service.calculate_score(lead)
                lead.update_priority_tier()

            await db.commit()
            return len(leads)

    count = run_async(_recalculate())

    return {"status": "success", "leads_updated": count}


# ============================================================================
# WEBHOOK TASKS
# ============================================================================


@celery_app.task(name="app.workers.tasks.trigger_webhook")
def trigger_webhook(webhook_url: str, event_type: str, payload: Dict):
    """
    Trigger webhook

    Args:
        webhook_url: Webhook URL
        event_type: Event type
        payload: Event payload
    """
    import hashlib
    import hmac

    import requests

    try:
        # Generate signature
        signature = hmac.new(
            settings.SECRET_KEY.encode(),
            payload.encode() if isinstance(payload, str) else str(payload).encode(),
            hashlib.sha256,
        ).hexdigest()

        # Send webhook
        response = requests.post(
            webhook_url,
            json={
                "event": event_type,
                "payload": payload,
                "timestamp": datetime.utcnow().isoformat(),
            },
            headers={
                "X-Webhook-Signature": signature,
                "Content-Type": "application/json",
            },
            timeout=10,
        )

        return {
            "status": "success" if response.status_code == 200 else "failed",
            "status_code": response.status_code,
            "webhook_url": webhook_url,
        }

    except Exception as e:
        return {"status": "error", "error": str(e), "webhook_url": webhook_url}


# ============================================================================
# CONFERENCE DATA TASKS
# ============================================================================


@celery_app.task(
    name="app.workers.tasks.refresh_conference_data_task",
    bind=False,
    max_retries=2,
    default_retry_delay=3600,  # retry after 1 hour on failure
)
def refresh_conference_data_task(
    conferences: List[str] = None,
    year: int = None,
):
    """
    Annual task: scrape fresh conference speaker data and update Redis cache.

    Triggered automatically every January 15 by Celery Beat.
    Can also be run manually:
        from app.workers.tasks import refresh_conference_data_task
        refresh_conference_data_task.delay()

    Args:
        conferences: Keys to refresh. None = ["sot", "aacr", "ashp"]
        year:        Conference year. None = current year.
    """
    conferences = conferences or ["sot", "aacr", "ashp"]
    year        = year or datetime.now().year

    async def _refresh():
        from app.services.conference_service import get_conference_service
        service = get_conference_service()

        results = {}
        for conf_key in conferences:
            try:
                # Delete stale cache so _get_speakers does a fresh scrape
                from app.core.cache import Cache
                cache_key = f"conference:speakers:{conf_key}:{year}"
                await Cache.delete(cache_key)

                speakers = await service.get_all_speakers(conf_key, year)
                results[conf_key] = {
                    "status":   "success",
                    "speakers": len(speakers),
                    "year":     year,
                }
            except Exception as exc:
                results[conf_key] = {
                    "status": "error",
                    "error":  str(exc),
                }

        return results

    result  = run_async(_refresh())
    total   = sum(r.get("speakers", 0) for r in result.values() if isinstance(r, dict))
    success = [k for k, v in result.items() if v.get("status") == "success"]
    failed  = [k for k, v in result.items() if v.get("status") == "error"]

    print(
        f"[conference-refresh] {year}: "
        f"{total} speakers cached. "
        f"Success: {success}. "
        f"Failed: {failed}."
    )
    return result

# ============================================================================
# NIH FUNDING CACHE REFRESH TASK
# ============================================================================


@celery_app.task(
    name="app.workers.tasks.refresh_nih_funding_cache_task",
    bind=False,
    max_retries=2,
    default_retry_delay=1800,   # retry after 30 minutes
)
def refresh_nih_funding_cache_task(queries: List[str] = None):
    """
    Quarterly task: pre-warm the NIH RePORTER cache for common biotech queries.

    Runs Jan / Apr / Jul / Oct — aligned with NIH fiscal quarters.
    This ensures search results are always fresh and served from Redis.

    Args:
        queries: Custom query list. None = default DILI/biotech queries.
    """
    default_queries = [
        "drug-induced liver injury",
        "hepatotoxicity 3D models",
        "organoid toxicology",
        "DILI biomarkers",
        "microphysiological systems",
        "organ-on-chip liver",
        "new approach methodologies toxicity",
        "3D hepatocyte culture safety",
    ]
    queries = queries or default_queries

    async def _refresh():
        from app.services.funding_service import (
            get_funding_service, _build_cache_key,
            _tokenise_query, _default_fiscal_years,
        )
        from app.core.cache import Cache

        service = get_funding_service()
        results = {}

        for query in queries:
            try:
                # Delete stale cache entry
                keywords     = _tokenise_query(query)
                fiscal_years = _default_fiscal_years()
                stale_key    = _build_cache_key(
                    "nih:keywords",
                    ":".join(keywords),
                    ":".join(str(y) for y in sorted(fiscal_years)),
                    "True",
                )
                await Cache.delete(stale_key)

                # Fetch fresh data (will re-cache automatically)
                leads = await service.search_leads(
                    query=query, use_cache=False, max_results=50
                )
                results[query] = {"status": "success", "leads": len(leads)}
            except Exception as exc:
                results[query] = {"status": "error", "error": str(exc)}

        return results

    result  = run_async(_refresh())
    success = sum(1 for v in result.values() if v.get("status") == "success")
    total   = sum(v.get("leads", 0) for v in result.values())

    print(
        f"[nih-cache-refresh] {success}/{len(queries)} queries refreshed. "
        f"{total} leads cached."
    )
    return result


# ============================================================================
# MULTI-SOURCE FULL PIPELINE TASK
# ============================================================================


@celery_app.task(
    name="app.workers.tasks.run_full_pipeline_task",
    bind=True,
    max_retries=2,
    default_retry_delay=600,
)
def run_full_pipeline_task(
    self,
    query: str,
    user_id: str,
    sources: list = None,
    max_results_per_source: int = 50,
    run_enrichment: bool = True,
):
    """Run the full parallel multi-source lead generation pipeline."""

    async def _run():
        async with async_session_factory() as db:
            result = await db.execute(select(User).where(User.id == UUID(user_id)))
            user = result.scalar_one_or_none()
            if not user:
                raise ValueError(f"User {user_id} not found")

            pipeline_svc = get_pipeline_service()
            return await pipeline_svc.run_multi_source_pipeline(
                query=query,
                user=user,
                db=db,
                sources=sources,
                max_results_per_source=max_results_per_source,
                run_enrichment=run_enrichment,
            )

    try:
        result = run_async(_run())
        print(
            f"[full-pipeline] '{query}' → "
            f"{result.get('leads_saved', 0)} leads saved, "
            f"{result.get('leads_rejected', 0)} rejected."
        )
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


# ============================================================================
# MONTHLY QUOTA RESET TASK
# ============================================================================


@celery_app.task(
    name="app.workers.tasks.reset_quota_counters_task",
    bind=False,
)
def reset_quota_counters_task():
    """Reset Hunter and Clearbit Redis quota counters monthly."""

    async def _reset():
        from app.services.quota_manager import get_quota_manager

        qm = get_quota_manager()
        await qm.reset_all_quotas()

    run_async(_reset())
    print("[quota-reset] Hunter + Clearbit Redis counters reset for new month.")


@celery_app.task(name="app.workers.tasks.run_smart_alerts_task")
def run_smart_alerts_task():
    """Evaluate all active smart alert rules for all users."""

    async def _run():
        from app.services.smart_alert_service import get_smart_alert_service

        async with async_session_factory() as db:
            svc = get_smart_alert_service()
            result = await db.execute(select(User).where(User.is_active == True))
            total_fired = 0
            for user in result.scalars().all():
                stats = await svc.evaluate_all_rules(user, db)
                total_fired += stats.get("alerts_fired", 0)
        return {"status": "success", "total_alerts_fired": total_fired}

    return run_async(_run())


@celery_app.task(name="app.workers.tasks.batch_rescore_all_users_task")
def batch_rescore_all_users_task():
    """Rescore all leads for all active users using the Phase 2.5 scoring service."""

    async def _run():
        from app.services.scoring_service import get_scoring_service

        async with async_session_factory() as db:
            svc = get_scoring_service()
            result = await db.execute(select(User).where(User.is_active == True))
            total_leads = 0
            for user in result.scalars().all():
                weight_overrides = user.preferences.get("scoring_weights") if user.preferences else None
                summary = await svc.batch_rescore(user.id, db, weight_overrides)
                total_leads += summary.get("leads_rescored", 0)
        return {"status": "success", "total_leads_rescored": total_leads}

    return run_async(_run())
