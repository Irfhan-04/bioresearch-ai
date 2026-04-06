"""Billing endpoints — Stripe Checkout, Portal, and subscription sync."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user, get_db
from app.models.user import User
from app.schemas.base import SuccessResponse
from app.services.billing_service import (
    create_checkout_session,
    create_customer_portal_session,
    get_billing_summary,
    sync_subscription_from_stripe,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class CheckoutRequest(BaseModel):
    price_id: str


class SyncRequest(BaseModel):
    subscription_id: str


@router.get("/summary")
async def get_billing_summary_endpoint(
    current_user: User = Depends(get_current_active_user),
):
    summary = await get_billing_summary(current_user)
    return {"success": True, "data": summary}


@router.post("/checkout")
async def create_checkout(
    body: CheckoutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        url = await create_checkout_session(current_user, body.price_id, db)
        return {"success": True, "data": {"checkout_url": url}}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Checkout error for user %s: %s", current_user.id, exc)
        raise HTTPException(
            status_code=502, detail="Could not create checkout session."
        ) from exc


@router.post("/portal")
async def create_portal(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        url = await create_customer_portal_session(current_user, db)
        return {"success": True, "data": {"portal_url": url}}
    except Exception as exc:
        logger.error("Portal error for user %s: %s", current_user.id, exc)
        raise HTTPException(
            status_code=502, detail="Could not open billing portal."
        ) from exc


@router.post("/sync", response_model=SuccessResponse)
async def sync_billing(
    body: SyncRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        await sync_subscription_from_stripe(
            current_user, body.subscription_id, db
        )
        return SuccessResponse(message="Subscription synced successfully.")
    except Exception as exc:
        logger.error("Stripe sync error for user %s: %s", current_user.id, exc)
        raise HTTPException(
            status_code=502, detail="Could not sync subscription."
        ) from exc
    