"""
Webhook Integration Endpoints - FIXED
Allow external services to trigger pipelines and receive events
"""

import hashlib
import hmac
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_active_user, get_db
from app.models.user import User
from app.models.webhook import Webhook, WebhookEvent, WebhookEventType
from app.schemas.base import MessageResponse, PaginatedResponse
from app.schemas.webhook import (WebhookCreate, WebhookEventResponse,
                                 WebhookResponse, WebhookTestResponse,
                                 WebhookUpdate)

router = APIRouter()


# ============================================================================
# WEBHOOK MANAGEMENT
# ============================================================================


@router.post(
    "",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create webhook",
    description="Register webhook endpoint for event notifications",
)
async def create_webhook(
    webhook_data: WebhookCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create webhook endpoint

    **Available Events:**
    - `pipeline.completed` - Pipeline execution completed
    - `pipeline.failed` - Pipeline execution failed
    - `lead.created` - New lead created
    - `lead.enriched` - Lead enrichment completed
    - `export.ready` - Export file ready for download

    **Security:**
    - Each webhook gets a unique secret key
    - All requests include `X-Webhook-Signature` header
    - Verify signature: `HMAC-SHA256(secret, payload)`
    """
    # Generate secret key
    import secrets

    secret_key = secrets.token_urlsafe(32)

    # CRITICAL FIX: Convert HttpUrl to string
    webhook_url = str(webhook_data.url)

    # Create webhook
    webhook = Webhook(
        user_id=current_user.id,
        name=webhook_data.name,
        url=webhook_url,  # Use converted string
        events=webhook_data.events,
        secret_key=secret_key,
        is_active=True,
    )

    db.add(webhook)
    await db.commit()
    await db.refresh(webhook)

    return WebhookResponse.model_validate(webhook, from_attributes=True)


@router.get(
    "",
    response_model=PaginatedResponse,
    summary="List webhooks",
    description="Get user's webhooks",
)
async def list_webhooks(
    page: int = 1,
    size: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's webhooks"""
    from sqlalchemy import func

    # Build query
    query = select(Webhook).where(Webhook.user_id == current_user.id)

    # Get total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    # Get paginated results
    query = query.order_by(Webhook.created_at.desc())
    query = query.offset((page - 1) * size).limit(size)

    result = await db.execute(query)
    webhooks = result.scalars().all()

    return PaginatedResponse.create(
        items=[
            WebhookResponse.model_validate(w, from_attributes=True) for w in webhooks
        ],
        page=page,
        size=size,
        total=total,
    )


@router.get(
    "/{webhook_id}",
    response_model=WebhookResponse,
    summary="Get webhook",
    description="Get webhook details",
)
async def get_webhook(
    webhook_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get webhook details"""
    result = await db.execute(
        select(Webhook).where(
            and_(Webhook.id == webhook_id, Webhook.user_id == current_user.id)
        )
    )
    webhook = result.scalar_one_or_none()

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found"
        )

    return WebhookResponse.model_validate(webhook, from_attributes=True)


@router.put(
    "/{webhook_id}",
    response_model=WebhookResponse,
    summary="Update webhook",
    description="Update webhook configuration",
)
async def update_webhook(
    webhook_id: UUID,
    webhook_updates: WebhookUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update webhook"""
    result = await db.execute(
        select(Webhook).where(
            and_(Webhook.id == webhook_id, Webhook.user_id == current_user.id)
        )
    )
    webhook = result.scalar_one_or_none()

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found"
        )

    # Update fields - CRITICAL FIX: Convert URL to string if present
    update_dict = webhook_updates.model_dump(exclude_none=True)
    if "url" in update_dict:
        update_dict["url"] = str(update_dict["url"])

    for field, value in update_dict.items():
        setattr(webhook, field, value)

    await db.commit()
    await db.refresh(webhook)

    return WebhookResponse.model_validate(webhook, from_attributes=True)


@router.delete(
    "/{webhook_id}",
    response_model=MessageResponse,
    summary="Delete webhook",
    description="Delete webhook",
)
async def delete_webhook(
    webhook_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete webhook"""
    result = await db.execute(
        select(Webhook).where(
            and_(Webhook.id == webhook_id, Webhook.user_id == current_user.id)
        )
    )
    webhook = result.scalar_one_or_none()

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found"
        )

    await db.delete(webhook)
    await db.commit()

    return MessageResponse(message="Webhook deleted successfully")


# ============================================================================
# WEBHOOK TESTING & DEBUGGING
# ============================================================================


@router.post(
    "/{webhook_id}/test",
    response_model=WebhookTestResponse,
    summary="Test webhook",
    description="Send test event to webhook",
)
async def test_webhook(
    webhook_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Test webhook endpoint

    Sends a test event to verify webhook is configured correctly
    """
    result = await db.execute(
        select(Webhook).where(
            and_(Webhook.id == webhook_id, Webhook.user_id == current_user.id)
        )
    )
    webhook = result.scalar_one_or_none()

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found"
        )

    # Send test event - FIXED: Pass db parameter
    from app.services.webhook_service import get_webhook_service

    service = get_webhook_service()
    success = await service.send_test_event(webhook, db)

    return WebhookTestResponse(
        success=success,
        message="Test event sent successfully"
        if success
        else "Failed to send test event",
    )


@router.get(
    "/{webhook_id}/events",
    response_model=PaginatedResponse,
    summary="Get webhook events",
    description="Get webhook event history",
)
async def get_webhook_events(
    webhook_id: UUID,
    page: int = 1,
    size: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get webhook event history

    Shows recent webhook deliveries with:
    - Event type
    - Status (success/failure)
    - Response code
    - Timestamp
    - Payload
    """
    from sqlalchemy import func

    # Verify webhook ownership
    result = await db.execute(
        select(Webhook).where(
            and_(Webhook.id == webhook_id, Webhook.user_id == current_user.id)
        )
    )
    webhook = result.scalar_one_or_none()

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found"
        )

    # Get events
    query = select(WebhookEvent).where(WebhookEvent.webhook_id == webhook_id)

    # Get total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    # Get paginated results
    query = query.order_by(WebhookEvent.created_at.desc())
    query = query.offset((page - 1) * size).limit(size)

    result = await db.execute(query)
    events = result.scalars().all()

    return PaginatedResponse.create(
        items=[
            WebhookEventResponse.model_validate(e, from_attributes=True) for e in events
        ],
        page=page,
        size=size,
        total=total,
    )


# ============================================================================
# INCOMING WEBHOOK TRIGGERS
# ============================================================================


@router.post(
    "/trigger/{user_id}/{webhook_secret}",
    response_model=MessageResponse,
    summary="Trigger webhook",
    description="External endpoint to trigger pipeline via webhook",
)
async def trigger_webhook(
    user_id: UUID,
    webhook_secret: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    External webhook trigger endpoint
    
    **Usage:**
    ```bash
    curl -X POST "https://api.yourdomain.com/webhooks/trigger/{user_id}/{secret}" \
      -H "Content-Type: application/json" \
      -d '{
        "pipeline_id": "...",
        "override_config": {...}
      }'
    ```
    
    **Example integrations:**
    - Zapier: Trigger on new Google Sheet row
    - Make: Trigger on Airtable update
    - GitHub Actions: Trigger on repository event
    - Slack: Trigger on slash command
    """
    # Verify webhook secret
    result = await db.execute(
        select(Webhook).where(
            and_(
                Webhook.user_id == user_id,
                Webhook.secret_key == webhook_secret,
                Webhook.is_active == True,
            )
        )
    )
    webhook = result.scalar_one_or_none()

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook credentials",
        )

    # Parse payload
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload"
        )

    # Get pipeline ID
    pipeline_id = payload.get("pipeline_id")
    if not pipeline_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="pipeline_id required"
        )

    # Queue pipeline execution
    from app.models.pipeline import Pipeline
    from app.services.pipeline_service import get_pipeline_service

    result = await db.execute(
        select(Pipeline).where(
            and_(Pipeline.id == UUID(pipeline_id), Pipeline.user_id == user_id)
        )
    )
    pipeline = result.scalar_one_or_none()

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline not found"
        )

    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    # Queue execution
    service = get_pipeline_service()
    job_id = await service.queue_pipeline_run(
        pipeline=pipeline,
        user=user,
        db=db,
        override_config=payload.get("override_config"),
    )

    return MessageResponse(
        message="Pipeline queued for execution", data={"job_id": job_id}
    )
