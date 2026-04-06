"""CRM integration API endpoints for Phase 2.6A."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user, get_db
from app.models.crm import CrmConnection, CrmSyncLog
from app.models.lead import Lead
from app.models.user import User
from app.schemas.crm import (
    CrmConnectionCreate,
    CrmConnectionResponse,
    CrmConnectionUpdate,
    CrmSyncLogResponse,
    SyncRequest,
)
from app.services.crm_service import encrypt_credentials, get_crm_service

router = APIRouter()


@router.get("", response_model=List[CrmConnectionResponse])
async def list_crm_connections(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List the current user's CRM connections."""

    result = await db.execute(
        select(CrmConnection)
        .where(CrmConnection.user_id == current_user.id)
        .order_by(CrmConnection.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=CrmConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_crm_connection(
    payload: CrmConnectionCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a CRM connection with encrypted credentials."""

    connection = CrmConnection(
        user_id=current_user.id,
        provider=payload.provider,
        name=payload.name,
        credentials_encrypted=encrypt_credentials(payload.credentials),
        field_map=payload.field_map,
        sync_direction=payload.sync_direction,
        auto_sync=payload.auto_sync,
        sync_filter=payload.sync_filter,
    )
    db.add(connection)
    await db.commit()
    await db.refresh(connection)
    return connection


@router.get("/{conn_id}", response_model=CrmConnectionResponse)
async def get_crm_connection(
    conn_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch a CRM connection owned by the current user."""

    result = await db.execute(
        select(CrmConnection).where(
            CrmConnection.id == conn_id,
            CrmConnection.user_id == current_user.id,
        )
    )
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(status_code=404, detail="CRM connection not found")
    return connection


@router.patch("/{conn_id}", response_model=CrmConnectionResponse)
async def update_crm_connection(
    conn_id: UUID,
    payload: CrmConnectionUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a CRM connection."""

    result = await db.execute(
        select(CrmConnection).where(
            CrmConnection.id == conn_id,
            CrmConnection.user_id == current_user.id,
        )
    )
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(status_code=404, detail="CRM connection not found")

    update_data = payload.model_dump(exclude_none=True)
    if "credentials" in update_data:
        connection.credentials_encrypted = encrypt_credentials(
            update_data.pop("credentials")
        )

    for field_name, value in update_data.items():
        setattr(connection, field_name, value)

    db.add(connection)
    await db.commit()
    await db.refresh(connection)
    return connection


@router.delete("/{conn_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_crm_connection(
    conn_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a CRM connection."""

    result = await db.execute(
        select(CrmConnection).where(
            CrmConnection.id == conn_id,
            CrmConnection.user_id == current_user.id,
        )
    )
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(status_code=404, detail="CRM connection not found")

    await db.delete(connection)
    await db.commit()


@router.post("/{conn_id}/test", response_model=dict, summary="Validate CRM credentials")
async def test_crm_connection(
    conn_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Test CRM credentials for a connection."""

    result = await db.execute(
        select(CrmConnection).where(
            CrmConnection.id == conn_id,
            CrmConnection.user_id == current_user.id,
        )
    )
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(status_code=404, detail="CRM connection not found")
    return await get_crm_service().test_connection(connection)


@router.post("/{conn_id}/sync", response_model=CrmSyncLogResponse, summary="Sync leads to CRM")
async def sync_leads(
    conn_id: UUID,
    request: SyncRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Sync selected or filtered leads to the CRM."""

    connection_result = await db.execute(
        select(CrmConnection).where(
            CrmConnection.id == conn_id,
            CrmConnection.user_id == current_user.id,
            CrmConnection.is_active.is_(True),
        )
    )
    connection = connection_result.scalar_one_or_none()
    if not connection:
        raise HTTPException(status_code=404, detail="Active CRM connection not found")

    query = select(Lead).where(Lead.user_id == current_user.id)
    if request.lead_ids:
        query = query.where(Lead.id.in_(request.lead_ids))
    elif connection.sync_filter:
        if minimum_score := connection.sync_filter.get("min_score"):
            query = query.where(Lead.propensity_score >= minimum_score)
        if statuses := connection.sync_filter.get("status"):
            query = query.where(Lead.status.in_(statuses))
    query = query.limit(500)

    lead_result = await db.execute(query)
    leads = lead_result.scalars().all()

    return await get_crm_service().sync_leads(
        connection,
        leads,
        db,
        dry_run=request.dry_run,
    )


@router.get("/{conn_id}/logs", response_model=List[CrmSyncLogResponse], summary="Sync history")
async def get_sync_logs(
    conn_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch CRM sync history for a connection."""

    result = await db.execute(
        select(CrmSyncLog)
        .join(CrmConnection, CrmConnection.id == CrmSyncLog.connection_id)
        .where(
            CrmConnection.id == conn_id,
            CrmConnection.user_id == current_user.id,
        )
        .order_by(CrmSyncLog.started_at.desc())
        .limit(limit)
    )
    return result.scalars().all()
