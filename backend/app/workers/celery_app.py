"""
Celery Configuration for Background Jobs
Handles scheduled tasks, pipeline execution, and async jobs
"""

from datetime import timedelta

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "biotech_lead_generator",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

# Celery Configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Task execution settings
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max
    task_soft_time_limit=25 * 60,  # Soft limit at 25 minutes
    task_acks_late=True,  # Acknowledge after task completion
    task_reject_on_worker_lost=True,
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,
    # Worker settings
    worker_prefetch_multiplier=1,  # One task at a time
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
    # Rate limiting
    task_default_rate_limit="10/m",  # 10 tasks per minute by default
    # Error handling
    task_autoretry_for=(Exception,),
    task_retry_kwargs={"max_retries": 3},
    task_retry_backoff=True,
    task_retry_backoff_max=600,  # Max 10 minutes
    task_retry_jitter=True,
)

# Scheduled Tasks (Celery Beat)
celery_app.conf.beat_schedule = {
    # Check for pipelines to run every minute
    "check-scheduled-pipelines": {
        "task": "app.workers.tasks.check_scheduled_pipelines",
        "schedule": crontab(minute="*/1"),  # Every minute
    },
    # Clean up expired exports daily at 2 AM
    "cleanup-expired-exports": {
        "task": "app.workers.tasks.cleanup_expired_exports",
        "schedule": crontab(hour=2, minute=0),  # Daily at 2:00 AM
    },
    # Send daily digest emails at 9 AM
    "send-daily-digests": {
        "task": "app.workers.tasks.send_daily_digests",
        "schedule": crontab(hour=9, minute=0),  # Daily at 9:00 AM
    },
    "daily-score-recalculate": {
        "task": "app.workers.tasks.batch_rescore_all_users_task",
        "schedule": crontab(hour=3, minute=30),
    },
    "daily-smart-alerts": {
        "task": "app.workers.tasks.run_smart_alerts_task",
        "schedule": crontab(hour=8, minute=0),
    },
    # Reset monthly usage counters on 1st of month
    "reset-monthly-usage": {
        "task": "app.workers.tasks.reset_monthly_usage",
        "schedule": crontab(day_of_month=1, hour=0, minute=0),  # 1st at midnight
    },
    # Reset Hunter + Clearbit quota counters on 1st of month at 00:05 UTC
    "reset-quota-counters": {
        "task": "app.workers.tasks.reset_quota_counters_task",
        "schedule": crontab(day_of_month=1, hour=0, minute=5),
    },
    # Refresh conference speaker data once a year in January
    # SOT/AACR/ASHP programmes are typically published Nov–Jan
    "refresh-conference-data": {
        "task":     "app.workers.tasks.refresh_conference_data_task",
        "schedule": crontab(month_of_year=1, day_of_month=15, hour=3, minute=0),
        # Runs: January 15 at 03:00 UTC every year
        # Manual trigger: refresh_conference_data_task.delay()
    },
    # Refresh NIH funding cache every quarter (Jan / Apr / Jul / Oct)
    "refresh-nih-funding-cache": {
        "task":     "app.workers.tasks.refresh_nih_funding_cache_task",
        "schedule": crontab(month_of_year="1,4,7,10", day_of_month=1, hour=4, minute=0),
        # Runs: 1st of January, April, July, October at 4:00 AM UTC
        # Why quarterly: NIH announces new grant awards each fiscal quarter
        # Manual trigger: refresh_nih_funding_cache_task.delay()
    },
}


# Task Routes (send specific tasks to specific queues)
celery_app.conf.task_routes = {
    "app.workers.tasks.execute_pipeline_task": {"queue": "pipelines"},
    "app.workers.tasks.enrich_lead_task": {"queue": "enrichment"},
    "app.workers.tasks.export_data_task": {"queue": "exports"},
    "app.workers.tasks.send_email_task": {"queue": "emails"},
}


# Queue Priorities
celery_app.conf.task_queue_max_priority = 10
celery_app.conf.task_default_priority = 5


if __name__ == "__main__":
    # For testing
    celery_app.start()
