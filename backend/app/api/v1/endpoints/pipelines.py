"""
Pipeline Management Endpoints
Create, manage, and execute automated data pipelines
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import (APIRouter, BackgroundTasks, Depends, HTTPException, Query,
                     status)
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user, get_db
from app.models.pipeline import Pipeline, PipelineSchedule, PipelineStatus
from app.models.user import User
from app.schemas.base import (MessageResponse, PaginatedResponse,
                              SuccessResponse)
from app.schemas.pipeline import (PipelineCreate, PipelineResponse,
                                  PipelineRunRequest, PipelineUpdate)
from app.services.pipeline_service import get_pipeline_service

router = APIRouter()


# ============================================================================
# CREATE PIPELINE
# ============================================================================


@router.post(
    "",
    response_model=PipelineResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create pipeline",
    description="Create new automated data pipeline",
)
async def create_pipeline(
    pipeline_data: PipelineCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create new pipeline

    **Pipeline Configuration:**
    ```json
    {
      "data_sources": ["pubmed", "linkedin"],
      "search_queries": [
        {
          "source": "pubmed",
          "query": "drug-induced liver injury 3D models",
          "years_back": 2
        }
      ],
      "filters": {
        "min_score": 70,
        "locations": ["Cambridge, MA", "Boston, MA"]
      },
      "enrichment": {
        "find_email": true,
        "get_company_data": true
      },
      "notifications": {
        "email_on_completion": true,
        "email_on_error": true
      }
    }
    ```

    **Schedules:**
    - `manual`: Run only when triggered
    - `daily`: Run every day at midnight
    - `weekly`: Run every Monday
    - `monthly`: Run on 1st of month
    - `custom`: Use cron expression
    """
    service = get_pipeline_service()

    try:
        pipeline = await service.create_pipeline(
            user=current_user,
            db=db,
            name=pipeline_data.name,
            description=pipeline_data.description,
            schedule=pipeline_data.schedule,
            cron_expression=pipeline_data.cron_expression,
            config=pipeline_data.config,
        )

        return PipelineResponse.model_validate(pipeline, from_attributes=True)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# LIST PIPELINES
# ============================================================================


@router.get(
    "",
    response_model=PaginatedResponse,
    summary="List pipelines",
    description="Get user's pipelines with pagination",
)
async def list_pipelines(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Items per page"),
    status: Optional[PipelineStatus] = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List user's pipelines

    Returns all pipelines created by the user with:
    - Current status
    - Last run information
    - Next scheduled run
    - Statistics
    """
    # Build query
    query = select(Pipeline).where(Pipeline.user_id == current_user.id)

    # Apply status filter
    if status:
        query = query.where(Pipeline.status == status)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    # Get paginated results
    query = query.order_by(Pipeline.created_at.desc())
    query = query.offset((page - 1) * size).limit(size)

    result = await db.execute(query)
    pipelines = result.scalars().all()

    # Convert to response
    pipeline_responses = [
        PipelineResponse.model_validate(p, from_attributes=True) for p in pipelines
    ]

    return PaginatedResponse.create(
        items=pipeline_responses, page=page, size=size, total=total
    )


# ============================================================================
# GET PIPELINE
# ============================================================================


@router.get(
    "/{pipeline_id}",
    response_model=PipelineResponse,
    summary="Get pipeline",
    description="Get pipeline details",
)
async def get_pipeline(
    pipeline_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get pipeline details

    Returns complete pipeline information including:
    - Configuration
    - Schedule
    - Execution history
    - Statistics
    """
    result = await db.execute(
        select(Pipeline).where(
            and_(Pipeline.id == pipeline_id, Pipeline.user_id == current_user.id)
        )
    )
    pipeline = result.scalar_one_or_none()

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline not found"
        )

    return PipelineResponse.model_validate(pipeline, from_attributes=True)


# ============================================================================
# UPDATE PIPELINE
# ============================================================================


@router.put(
    "/{pipeline_id}",
    response_model=PipelineResponse,
    summary="Update pipeline",
    description="Update pipeline configuration",
)
async def update_pipeline(
    pipeline_id: UUID,
    pipeline_updates: PipelineUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update pipeline

    Can update:
    - Name and description
    - Schedule
    - Configuration
    - Status (activate/pause/disable)
    """
    result = await db.execute(
        select(Pipeline).where(
            and_(Pipeline.id == pipeline_id, Pipeline.user_id == current_user.id)
        )
    )
    pipeline = result.scalar_one_or_none()

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline not found"
        )

    # Update fields
    for field, value in pipeline_updates.model_dump(exclude_none=True).items():
        setattr(pipeline, field, value)

    await db.commit()
    await db.refresh(pipeline)

    return PipelineResponse.model_validate(pipeline, from_attributes=True)


# ============================================================================
# DELETE PIPELINE
# ============================================================================


@router.delete(
    "/{pipeline_id}",
    response_model=MessageResponse,
    summary="Delete pipeline",
    description="Delete pipeline",
)
async def delete_pipeline(
    pipeline_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete pipeline

    This will:
    - Stop any running jobs
    - Cancel scheduled runs
    - Delete pipeline record

    Cannot be undone.
    """
    result = await db.execute(
        select(Pipeline).where(
            and_(Pipeline.id == pipeline_id, Pipeline.user_id == current_user.id)
        )
    )
    pipeline = result.scalar_one_or_none()

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline not found"
        )

    await db.delete(pipeline)
    await db.commit()

    return MessageResponse(message="Pipeline deleted successfully")


# ============================================================================
# RUN PIPELINE
# ============================================================================


@router.post(
    "/{pipeline_id}/run",
    response_model=SuccessResponse,
    summary="Run pipeline",
    description="Manually trigger pipeline execution",
)
async def run_pipeline(
    pipeline_id: UUID,
    request: PipelineRunRequest = PipelineRunRequest(),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Run pipeline manually

    **Options:**
    - `override_config`: Temporary config override for this run only

    **Process:**
    1. Validates pipeline exists and is not disabled
    2. Queues background job
    3. Returns immediately with job ID
    4. Pipeline runs asynchronously
    5. Sends notification on completion

    **Example override:**
    ```json
    {
      "override_config": {
        "search_queries": [
          {
            "source": "pubmed",
            "query": "DILI organoids 2024"
          }
        ]
      }
    }
    ```
    """
    service = get_pipeline_service()

    try:
        # Get pipeline
        result = await db.execute(
            select(Pipeline).where(
                and_(Pipeline.id == pipeline_id, Pipeline.user_id == current_user.id)
            )
        )
        pipeline = result.scalar_one_or_none()

        if not pipeline:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline not found"
            )

        # Check if pipeline is disabled
        if pipeline.status == PipelineStatus.DISABLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pipeline is disabled. Enable it first.",
            )

        # Queue execution
        job_id = await service.queue_pipeline_run(
            pipeline=pipeline,
            user=current_user,
            db=db,
            override_config=request.override_config,
        )

        return SuccessResponse(
            message="Pipeline queued for execution",
            data={
                "pipeline_id": str(pipeline.id),
                "job_id": job_id,
                "status": "queued",
            },
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# PIPELINE STATUS CONTROLS
# ============================================================================


@router.post(
    "/{pipeline_id}/activate",
    response_model=PipelineResponse,
    summary="Activate pipeline",
    description="Enable pipeline and resume scheduled runs",
)
async def activate_pipeline(
    pipeline_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Activate pipeline"""
    result = await db.execute(
        select(Pipeline).where(
            and_(Pipeline.id == pipeline_id, Pipeline.user_id == current_user.id)
        )
    )
    pipeline = result.scalar_one_or_none()

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline not found"
        )

    pipeline.activate()
    pipeline.next_run_at = pipeline.calculate_next_run()

    await db.commit()
    await db.refresh(pipeline)

    return PipelineResponse.model_validate(pipeline, from_attributes=True)


@router.post(
    "/{pipeline_id}/pause",
    response_model=PipelineResponse,
    summary="Pause pipeline",
    description="Temporarily pause scheduled runs",
)
async def pause_pipeline(
    pipeline_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Pause pipeline"""
    result = await db.execute(
        select(Pipeline).where(
            and_(Pipeline.id == pipeline_id, Pipeline.user_id == current_user.id)
        )
    )
    pipeline = result.scalar_one_or_none()

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline not found"
        )

    pipeline.pause()
    await db.commit()
    await db.refresh(pipeline)

    return PipelineResponse.model_validate(pipeline, from_attributes=True)


# ============================================================================
# PIPELINE HISTORY
# ============================================================================


@router.get(
    "/{pipeline_id}/history",
    response_model=dict,
    summary="Get pipeline history",
    description="Get execution history for pipeline",
)
async def get_pipeline_history(
    pipeline_id: UUID,
    limit: int = Query(10, ge=1, le=100, description="Number of runs to return"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get pipeline execution history

    Returns recent runs with:
    - Execution time
    - Success/failure status
    - Leads created
    - Errors (if any)
    """
    result = await db.execute(
        select(Pipeline).where(
            and_(Pipeline.id == pipeline_id, Pipeline.user_id == current_user.id)
        )
    )
    pipeline = result.scalar_one_or_none()

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline not found"
        )

    # For MVP, return last run results
    # In production, store history in separate table
    return {
        "pipeline_id": str(pipeline.id),
        "last_run": {
            "timestamp": pipeline.last_run_at.isoformat()
            if pipeline.last_run_at
            else None,
            "status": pipeline.last_run_status,
            "results": pipeline.last_run_results,
        },
        "statistics": {
            "total_runs": pipeline.run_count,
            "successful_runs": pipeline.success_count,
            "failed_runs": pipeline.error_count,
            "success_rate": pipeline.get_success_rate(),
            "total_leads_generated": pipeline.total_leads_generated,
        },
    }


# ============================================================================
# PIPELINE STATISTICS
# ============================================================================


@router.get(
    "/stats/summary",
    response_model=dict,
    summary="Pipeline statistics",
    description="Get overall pipeline statistics",
)
async def get_pipeline_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get pipeline statistics

    Returns:
    - Total pipelines
    - Active pipelines
    - Total runs
    - Success rate
    - Total leads generated
    """
    # Total pipelines
    total_result = await db.execute(
        select(func.count(Pipeline.id)).where(Pipeline.user_id == current_user.id)
    )
    total = total_result.scalar()

    # By status
    status_result = await db.execute(
        select(Pipeline.status, func.count(Pipeline.id))
        .where(Pipeline.user_id == current_user.id)
        .group_by(Pipeline.status)
    )
    by_status = {status.value: count for status, count in status_result}

    # Total runs and success
    stats_result = await db.execute(
        select(
            func.sum(Pipeline.run_count),
            func.sum(Pipeline.success_count),
            func.sum(Pipeline.total_leads_generated),
        ).where(Pipeline.user_id == current_user.id)
    )
    total_runs, total_success, total_leads = stats_result.first()

    total_runs = total_runs or 0
    total_success = total_success or 0
    total_leads = total_leads or 0

    success_rate = (total_success / total_runs * 100) if total_runs > 0 else 0

    return {
        "total_pipelines": total,
        "by_status": by_status,
        "total_runs": total_runs,
        "successful_runs": total_success,
        "success_rate": round(success_rate, 2),
        "total_leads_generated": total_leads,
    }


@router.get(
    "/templates",
    response_model=List[dict],
    summary="List pipeline templates",
    description="Pre-built pipeline configurations for common biotech use cases",
)
async def list_pipeline_templates(
    current_user: User = Depends(get_current_active_user),
):
    service = get_pipeline_service()
    return service.list_templates()


@router.post(
    "/templates/{template_key}/apply",
    response_model=PipelineResponse,
    status_code=201,
    summary="Create pipeline from template",
)
async def create_from_template(
    template_key: str,
    name: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = get_pipeline_service()
    try:
        pipeline = await service.create_from_template(
            user=current_user,
            db=db,
            template_key=template_key,
            name_override=name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return PipelineResponse.model_validate(pipeline, from_attributes=True)
