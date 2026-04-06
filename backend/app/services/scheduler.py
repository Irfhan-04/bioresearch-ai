"""
Intelligent Automation Scheduler
Smart scheduling system that optimizes pipeline execution
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pipeline import Pipeline, PipelineSchedule, PipelineStatus
from app.models.user import User


class AutomationScheduler:
    """
    Intelligent scheduler for pipeline automation

    Features:
    - Load balancing across time slots
    - Peak usage avoidance
    - Adaptive scheduling based on success rates
    - Resource optimization
    - Priority-based execution
    """

    def __init__(self):
        """Initialize scheduler"""
        self.max_concurrent_per_user = 3
        self.peak_hours = {9, 10, 11, 14, 15, 16}  # Business hours
        self.quiet_hours = {0, 1, 2, 3, 4, 5, 6}

    async def get_pipelines_to_execute(
        self, db: AsyncSession, limit: Optional[int] = None
    ) -> List[Pipeline]:
        """
        Get pipelines that should be executed now

        Uses intelligent scheduling to:
        - Avoid overloading the system
        - Balance load across users
        - Prioritize high-success pipelines
        - Skip during maintenance windows

        Args:
            db: Database session
            limit: Max pipelines to return

        Returns:
            List of pipelines to execute
        """
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)

        # Get pipelines due for execution
        query = (
            select(Pipeline)
            .where(
                and_(
                    Pipeline.status == PipelineStatus.ACTIVE,
                    Pipeline.next_run_at <= now,
                )
            )
            .order_by(
                # Priority: High success rate first
                Pipeline.success_count.desc(),
                # Then by scheduled time
                Pipeline.next_run_at.asc(),
            )
        )

        if limit:
            query = query.limit(limit)

        result = await db.execute(query)
        pipelines = result.scalars().all()

        # Apply intelligent filtering
        filtered = []
        user_counts = {}

        for pipeline in pipelines:
            # Check user concurrent limit
            user_id = str(pipeline.user_id)
            current_count = user_counts.get(user_id, 0)

            if current_count >= self.max_concurrent_per_user:
                continue

            # Skip if pipeline is already running
            if pipeline.status == PipelineStatus.RUNNING:
                continue

            # Check if pipeline is healthy
            if not self._is_pipeline_healthy(pipeline):
                # Pause unhealthy pipelines
                pipeline.pause()
                await db.commit()
                continue

            filtered.append(pipeline)
            user_counts[user_id] = current_count + 1

        return filtered

    async def optimize_schedule(self, pipeline: Pipeline, db: AsyncSession) -> datetime:
        """
        Optimize pipeline schedule based on performance

        Args:
            pipeline: Pipeline to optimize
            db: Database session

        Returns:
            Optimized next run time
        """
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)

        # Calculate base next run
        base_next = pipeline.calculate_next_run()

        # Adjust based on success rate
        success_rate = pipeline.get_success_rate()

        if success_rate < 50:
            # Low success rate: slow down
            delay_hours = 2
        elif success_rate < 75:
            # Medium success rate: slight delay
            delay_hours = 1
        else:
            # High success rate: no delay
            delay_hours = 0

        # Adjust based on time of day
        hour = base_next.hour

        if hour in self.peak_hours:
            # Shift to quiet hours
            delay_hours += 6

        # Apply delay
        optimized = base_next + timedelta(hours=delay_hours)

        return optimized

    async def rebalance_schedules(self, db: AsyncSession, user: Optional[User] = None):
        """
        Rebalance all pipeline schedules to optimize load

        Args:
            db: Database session
            user: Optional user to rebalance (or all users)
        """
        # Get pipelines to rebalance
        query = select(Pipeline).where(Pipeline.status == PipelineStatus.ACTIVE)

        if user:
            query = query.where(Pipeline.user_id == user.id)

        result = await db.execute(query)
        pipelines = result.scalars().all()

        # Group by schedule type
        by_schedule = {}
        for pipeline in pipelines:
            schedule = pipeline.schedule.value
            if schedule not in by_schedule:
                by_schedule[schedule] = []
            by_schedule[schedule].append(pipeline)

        # Distribute daily pipelines across 24 hours
        if "daily" in by_schedule:
            daily_pipelines = by_schedule["daily"]
            interval_hours = 24 / len(daily_pipelines) if daily_pipelines else 24

            for i, pipeline in enumerate(daily_pipelines):
                # Stagger across the day
                hour_offset = int(i * interval_hours)
                next_run = pipeline.next_run_at

                # Adjust hour
                next_run = next_run.replace(hour=hour_offset % 24)

                # Avoid peak hours
                while next_run.hour in self.peak_hours:
                    next_run += timedelta(hours=1)

                pipeline.next_run_at = next_run

        await db.commit()

    async def estimate_execution_time(self, pipeline: Pipeline) -> int:
        """
        Estimate pipeline execution time in seconds

        Args:
            pipeline: Pipeline to estimate

        Returns:
            Estimated seconds
        """
        # Base time per search query
        base_time = 30  # 30 seconds

        # Get config
        config = pipeline.config or {}
        search_queries = config.get("search_queries", [])

        # Calculate based on queries
        estimated = len(search_queries) * base_time

        # Add enrichment time
        if config.get("enrichment"):
            estimated += 60  # 1 minute for enrichment

        # Add buffer based on history
        if pipeline.run_count > 0:
            # Use average from history (simplified)
            estimated = int(estimated * 1.2)  # 20% buffer

        return estimated

    async def predict_next_failure(self, pipeline: Pipeline) -> Optional[datetime]:
        """
        Predict when pipeline might fail next

        Args:
            pipeline: Pipeline to analyze

        Returns:
            Predicted failure time or None
        """
        # Simplified prediction based on failure pattern
        if pipeline.error_count == 0:
            return None

        failure_rate = pipeline.error_count / max(pipeline.run_count, 1)

        if failure_rate > 0.5:
            # High failure rate: likely to fail soon
            return datetime.utcnow() + timedelta(hours=24)
        elif failure_rate > 0.25:
            # Medium failure rate
            return datetime.utcnow() + timedelta(days=7)

        return None

    def _is_pipeline_healthy(self, pipeline: Pipeline) -> bool:
        """
        Check if pipeline is healthy enough to run

        Args:
            pipeline: Pipeline to check

        Returns:
            True if healthy
        """
        # New pipelines are healthy
        if pipeline.run_count == 0:
            return True

        # Check success rate
        success_rate = pipeline.get_success_rate()

        if success_rate < 25:
            # Too many failures
            return False

        # Check recent failures
        if pipeline.error_count >= 5:
            # Too many total errors
            if pipeline.last_success_at:
                days_since_success = (datetime.utcnow() - pipeline.last_success_at).days
                if days_since_success > 7:
                    return False

        return True

    async def suggest_schedule_optimization(
        self, pipeline: Pipeline, db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Suggest optimizations for pipeline schedule

        Args:
            pipeline: Pipeline to analyze
            db: Database session

        Returns:
            Optimization suggestions
        """
        suggestions = {
            "current_schedule": pipeline.schedule.value,
            "recommendations": [],
            "estimated_improvement": 0,
        }

        success_rate = pipeline.get_success_rate()

        # Check if schedule is appropriate
        if pipeline.schedule == PipelineSchedule.DAILY:
            if success_rate < 50:
                suggestions["recommendations"].append(
                    {
                        "type": "frequency",
                        "message": "Consider switching to weekly schedule due to low success rate",
                        "suggested_schedule": "weekly",
                    }
                )
                suggestions["estimated_improvement"] = 25

        # Check timing
        if pipeline.next_run_at:
            hour = pipeline.next_run_at.hour

            if hour in self.peak_hours:
                suggestions["recommendations"].append(
                    {
                        "type": "timing",
                        "message": f"Running at {hour}:00 is during peak hours. Consider quiet hours (2-6 AM)",
                        "suggested_hour": 3,
                    }
                )
                suggestions["estimated_improvement"] = 15

        # Check for rate limiting issues
        if pipeline.last_run_results:
            errors = pipeline.last_run_results.get("errors", [])
            rate_limit_errors = [e for e in errors if "rate limit" in str(e).lower()]

            if rate_limit_errors:
                suggestions["recommendations"].append(
                    {
                        "type": "rate_limit",
                        "message": "Detected rate limiting. Consider spacing out queries or upgrading API tier",
                    }
                )

        return suggestions


# Singleton instance
_scheduler: Optional[AutomationScheduler] = None


def get_scheduler() -> AutomationScheduler:
    """
    Get singleton AutomationScheduler instance

    Usage:
        scheduler = get_scheduler()
        pipelines = await scheduler.get_pipelines_to_execute(db)
    """
    global _scheduler

    if _scheduler is None:
        _scheduler = AutomationScheduler()

    return _scheduler


__all__ = [
    "AutomationScheduler",
    "get_scheduler",
]
