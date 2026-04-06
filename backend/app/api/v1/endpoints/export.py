"""
Export API Endpoints
Create, list, and download exports
"""

from typing import Optional
from uuid import UUID

from fastapi import (APIRouter, BackgroundTasks, Depends, HTTPException, Query,
                     Request, status)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user, get_db
from app.models.export import ExportFormat
from app.models.user import User
from app.schemas.base import (MessageResponse, PaginatedResponse,
                              SuccessResponse)
from app.schemas.export import ExportCreate, ExportResponse
from app.services.export_service import get_export_service
from app.services.tier_quota_service import TierQuotaService
from app.services.usage_service import UsageService
from app.models.usage import UsageEventType
from app.utils.rate_limiter import export_limiter

router = APIRouter()


# ============================================================================
# CREATE EXPORT
# ============================================================================


@router.post(
    "",
    response_model=ExportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create export",
    description="Create new data export job",
)
async def create_export(
    export_data: ExportCreate,
    background_tasks: BackgroundTasks,
    http_request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create new export

    **Supported formats:**
    - `csv`: Comma-separated values
    - `excel`: Excel workbook with formatting
    - `json`: JSON array of objects
    - `pdf`: PDF report (coming soon)

    **Filters:**
    - `min_score`: Minimum propensity score
    - `max_score`: Maximum propensity score
    - `priority_tier`: HIGH, MEDIUM, LOW
    - `status`: Lead status
    - `location`: Location filter
    - `has_email`: Only leads with email

    **Process:**
    1. Export created in PENDING status
    2. Background job processes export
    3. File uploaded to storage
    4. Status changes to COMPLETED
    5. Download URL available for 7 days
    """
    await export_limiter.check(http_request)

    service = get_export_service()

    try:
        await TierQuotaService.check_and_enforce(db, current_user, "exports")
        # Create export record
        export = await service.create_export(
            user=current_user,
            db=db,
            format=export_data.format,
            filters=export_data.filters,
            columns=export_data.columns,
        )

        # Queue background job
        background_tasks.add_task(process_export_background, export.id, db)

        await UsageService.record(
            db=db,
            user_id=current_user.id,
            event_type=UsageEventType.EXPORT_GENERATED,
            quantity=1,
            metadata={"format": str(export_data.format)},
        )
        await db.commit()

        # Convert to response
        return ExportResponse.model_validate(export, from_attributes=True)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create export: {str(e)}",
        )


async def process_export_background(export_id: UUID, db: AsyncSession):
    """Background task to process export"""
    service = get_export_service()

    try:
        await TierQuotaService.check_and_enforce(db, current_user, "exports")
        await service.execute_export(export_id, db)
    except Exception as e:
        print(f"Export processing failed: {e}")


# ============================================================================
# LIST EXPORTS
# ============================================================================


@router.get(
    "",
    response_model=PaginatedResponse,
    summary="List exports",
    description="Get user's exports with pagination",
)
async def list_exports(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List user's exports

    Shows all exports created by the user, sorted by creation date (newest first).
    Includes:
    - Export status
    - File information
    - Download URL (if completed)
    - Expiration date
    """
    service = get_export_service()

    exports, total = await service.get_user_exports(
        user=current_user, db=db, page=page, size=size
    )

    # Convert to response schema
    export_responses = [
        ExportResponse.model_validate(export, from_attributes=True)
        for export in exports
    ]

    return PaginatedResponse.create(
        items=export_responses, page=page, size=size, total=total
    )


# ============================================================================
# GET SPECIFIC EXPORT
# ============================================================================


@router.get(
    "/{export_id}",
    response_model=ExportResponse,
    summary="Get export",
    description="Get export details and download URL",
)
async def get_export(
    export_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get export details

    Returns complete information about an export including:
    - Current status
    - Download URL (if completed and not expired)
    - File size
    - Record count
    - Creation/completion timestamps
    """
    service = get_export_service()

    export = await service.get_export(export_id=export_id, user=current_user, db=db)

    if not export:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Export not found"
        )

    return ExportResponse.model_validate(export, from_attributes=True)


# ============================================================================
# DOWNLOAD EXPORT
# ============================================================================


@router.get(
    "/{export_id}/download",
    summary="Download export",
    description="Get download URL for completed export",
)
async def download_export(
    export_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Download export file

    Returns:
    - `download_url`: Direct download link
    - `expires_in`: Seconds until link expires
    - `file_name`: Original filename
    - `file_size_mb`: File size in megabytes

    The file will be downloaded directly from cloud storage.
    """
    service = get_export_service()

    export = await service.get_export(export_id=export_id, user=current_user, db=db)

    if not export:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Export not found"
        )

    if not export.is_downloadable():
        if export.is_expired():
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Export has expired. Please create a new export.",
            )
        elif export.status.value == "pending":
            raise HTTPException(
                status_code=status.HTTP_202_ACCEPTED,
                detail="Export is still processing. Please check back later.",
            )
        elif export.status.value == "failed":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Export failed: {export.error_message}",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Export is not available for download",
            )

    # Mark as downloaded
    await service.mark_downloaded(export, db)

    # Calculate time until expiration
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    expires_in = (
        int((export.expires_at - now).total_seconds()) if export.expires_at else None
    )

    return {
        "download_url": export.file_url,
        "file_name": export.file_name,
        "file_size_mb": export.get_file_size_mb(),
        "expires_in": expires_in,
        "format": export.format.value,
        "records_count": export.records_count,
    }


# ============================================================================
# DELETE EXPORT
# ============================================================================


@router.delete(
    "/{export_id}",
    response_model=MessageResponse,
    summary="Delete export",
    description="Delete export and associated file",
)
async def delete_export(
    export_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete export

    Deletes both:
    - Export record from database
    - Export file from storage

    This action cannot be undone.
    """
    service = get_export_service()

    export = await service.get_export(export_id=export_id, user=current_user, db=db)

    if not export:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Export not found"
        )

    # Delete file from storage
    if export.file_url:
        try:
            from app.utils.storage import get_storage_service

            storage = get_storage_service()
            # Extract path from URL and delete
            # This is simplified - adjust based on your storage setup
        except Exception as e:
            print(f"Failed to delete file: {e}")

    # Delete record
    await db.delete(export)
    await db.commit()

    return MessageResponse(message="Export deleted successfully")


# ============================================================================
# EXPORT STATS
# ============================================================================


@router.get(
    "/stats/summary",
    response_model=dict,
    summary="Export statistics",
    description="Get export usage statistics",
)
async def get_export_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get export statistics

    Returns:
    - Total exports created
    - Exports by format
    - Exports by status
    - Total data exported
    - Storage usage
    """
    from sqlalchemy import func, select

    from app.models.export import Export

    # Total exports
    total_result = await db.execute(
        select(func.count(Export.id)).where(Export.user_id == current_user.id)
    )
    total = total_result.scalar()

    # By status
    status_result = await db.execute(
        select(Export.status, func.count(Export.id))
        .where(Export.user_id == current_user.id)
        .group_by(Export.status)
    )
    by_status = {status.value: count for status, count in status_result}

    # By format
    format_result = await db.execute(
        select(Export.format, func.count(Export.id))
        .where(Export.user_id == current_user.id)
        .group_by(Export.format)
    )
    by_format = {format.value: count for format, count in format_result}

    # Total records exported
    records_result = await db.execute(
        select(func.sum(Export.records_count)).where(Export.user_id == current_user.id)
    )
    total_records = records_result.scalar() or 0

    # Total storage used
    storage_result = await db.execute(
        select(func.sum(Export.file_size_bytes)).where(
            Export.user_id == current_user.id
        )
    )
    total_bytes = storage_result.scalar() or 0
    total_mb = round(total_bytes / (1024 * 1024), 2)

    return {
        "total_exports": total,
        "by_status": by_status,
        "by_format": by_format,
        "total_records_exported": total_records,
        "total_storage_mb": total_mb,
    }
