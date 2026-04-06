"""Stripe webhook endpoint — full event processing.

The `/stripe` route MUST be registered before the generic `/{webhook_id}`
catch-all route so FastAPI matches the literal path first.
"""

from __future__ import annotations

import logging

import stripe
from fastapi import APIRouter, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.services.billing_service import sync_subscription_from_stripe

logger = logging.getLogger(__name__)
router = APIRouter()

HANDLED_EVENTS = {
    "checkout.session.completed",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.payment_succeeded",
    "invoice.payment_failed",
}


@router.post("/stripe", status_code=status.HTTP_200_OK)
async def handle_stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> dict:
    """Validate the Stripe signature and dispatch the event."""
    if not stripe_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe-Signature header",
        )

    payload = await request.body()

    if settings.STRIPE_WEBHOOK_SECRET:
        try:
            event = stripe.Webhook.construct_event(
                payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
            )
        except stripe.error.SignatureVerificationError as exc:
            logger.warning("Stripe signature verification failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Stripe signature",
            ) from exc
    else:
        # No secret configured — accept unsigned (dev/test only)
        import json
        try:
            event = json.loads(payload)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload",
            ) from exc

    event_type = event.get("type", "")
    logger.info("Received Stripe event: %s (id=%s)", event_type, event.get("id"))

    if event_type in HANDLED_EVENTS:
        await _dispatch_event(event)

    return {"received": True, "event_type": event_type}


async def _dispatch_event(event: dict) -> None:
    event_type: str = event["type"]
    data_object: dict = event["data"]["object"]

    async with AsyncSessionLocal() as db:
        try:
            if event_type == "checkout.session.completed":
                await _handle_checkout_completed(data_object, db)
            elif event_type in {
                "customer.subscription.updated",
                "customer.subscription.deleted",
            }:
                await _handle_subscription_change(data_object, db)
            elif event_type == "invoice.payment_succeeded":
                await _handle_payment_succeeded(data_object, db)
            elif event_type == "invoice.payment_failed":
                await _handle_payment_failed(data_object, db)
        except Exception as exc:
            logger.exception(
                "Error processing Stripe event %s: %s", event_type, exc
            )


async def _get_user_by_stripe_customer(
    customer_id: str, db: AsyncSession
) -> User | None:
    result = await db.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    return result.scalar_one_or_none()


async def _get_user_by_id(user_id: str, db: AsyncSession) -> User | None:
    try:
        from uuid import UUID
        result = await db.execute(select(User).where(User.id == UUID(user_id)))
        return result.scalar_one_or_none()
    except Exception:
        return None


async def _handle_checkout_completed(session: dict, db: AsyncSession) -> None:
    customer_id = session.get("customer")
    subscription_id = session.get("subscription")
    user_id = session.get("metadata", {}).get("user_id")
    if not all([customer_id, subscription_id, user_id]):
        logger.warning(
            "checkout.session.completed missing fields — "
            "customer=%s sub=%s user=%s",
            customer_id, subscription_id, user_id,
        )
        return
    user = await _get_user_by_id(user_id, db)
    if not user:
        logger.error(
            "checkout.session.completed: no user for user_id=%s", user_id
        )
        return
    await sync_subscription_from_stripe(user, subscription_id, db)
    logger.info(
        "Subscription provisioned for user %s (sub=%s)", user_id, subscription_id
    )


async def _handle_subscription_change(
    subscription: dict, db: AsyncSession
) -> None:
    subscription_id = subscription["id"]
    customer_id = subscription.get("customer")
    user = (
        await _get_user_by_stripe_customer(customer_id, db) if customer_id else None
    )
    if not user:
        logger.warning(
            "subscription change: no user for customer=%s", customer_id
        )
        return
    await sync_subscription_from_stripe(user, subscription_id, db)
    logger.info(
        "Subscription synced for customer %s (sub=%s)",
        customer_id, subscription_id,
    )


async def _handle_payment_succeeded(invoice: dict, db: AsyncSession) -> None:
    customer_id = invoice.get("customer")
    subscription_id = invoice.get("subscription")
    if not (customer_id and subscription_id):
        return
    user = await _get_user_by_stripe_customer(customer_id, db)
    if not user:
        return
    await sync_subscription_from_stripe(user, subscription_id, db)
    logger.info("Payment succeeded for customer %s", customer_id)


async def _handle_payment_failed(invoice: dict, db: AsyncSession) -> None:
    customer_id = invoice.get("customer")
    amount_due = invoice.get("amount_due", 0)
    logger.warning(
        "Payment FAILED for customer %s — amount_due=%d cents",
        customer_id, amount_due,
    )
    # TODO: trigger a payment-failed email via email_service