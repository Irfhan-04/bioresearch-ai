"""Billing Service — Stripe subscription management."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import stripe
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import SubscriptionTier, User

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


def _build_price_map() -> dict[str, SubscriptionTier]:
    """Build price-ID → tier mapping lazily (safe when env vars are unset)."""
    mapping: dict[str, SubscriptionTier] = {}
    if settings.STRIPE_PRO_PRICE_ID:
        mapping[settings.STRIPE_PRO_PRICE_ID] = SubscriptionTier.PRO
    if settings.STRIPE_TEAM_PRICE_ID:
        mapping[settings.STRIPE_TEAM_PRICE_ID] = SubscriptionTier.TEAM
    return mapping


def _price_to_tier() -> dict[str, SubscriptionTier]:
    """Return freshly built map — safe even when env vars are not set."""
    return _build_price_map()


TIER_LIMITS: dict[SubscriptionTier, int] = {
    SubscriptionTier.FREE: 100,
    SubscriptionTier.PRO: 1000,
    SubscriptionTier.TEAM: 5000,
    SubscriptionTier.ENTERPRISE: 999_999,
}


async def get_or_create_stripe_customer(user: User, db: AsyncSession) -> str:
    """Return the Stripe customer ID for user, creating one if needed."""
    if user.stripe_customer_id:
        return user.stripe_customer_id
    customer = stripe.Customer.create(
        email=user.email,
        name=user.full_name or user.email,
        metadata={"user_id": str(user.id)},
    )
    user.stripe_customer_id = customer["id"]
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info("Created Stripe customer %s for user %s", customer["id"], user.id)
    return customer["id"]


async def create_checkout_session(
    user: User, price_id: str, db: AsyncSession
) -> str:
    """Create a Stripe Checkout session and return its redirect URL.

    Raises:
        ValueError: if price_id is empty, Stripe is not configured,
            or price_id is not a known Pro/Team price.
    """
    if not price_id:
        raise ValueError("price_id must not be empty.")
    valid_prices = _price_to_tier()
    if not valid_prices:
        raise ValueError(
            "Stripe price IDs are not configured. "
            "Set STRIPE_PRO_PRICE_ID and STRIPE_TEAM_PRICE_ID."
        )
    if price_id not in valid_prices:
        raise ValueError(
            f"Invalid price_id '{price_id}'. "
            f"Must be one of: {list(valid_prices.keys())}"
        )
    customer_id = await get_or_create_stripe_customer(user, db)
    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        allow_promotion_codes=True,
        billing_address_collection="auto",
        success_url=settings.STRIPE_SUCCESS_URL,
        cancel_url=settings.STRIPE_CANCEL_URL,
        subscription_data={
            "metadata": {"user_id": str(user.id), "price_id": price_id}
        },
        metadata={"user_id": str(user.id), "price_id": price_id},
    )
    logger.info("Created checkout session %s for user %s", session["id"], user.id)
    return session["url"]


async def create_customer_portal_session(
    user: User, db: AsyncSession
) -> str:
    """Create a Stripe Billing Portal session and return its URL."""
    customer_id = await get_or_create_stripe_customer(user, db)
    portal = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=settings.STRIPE_CANCEL_URL.split("?")[0],
    )
    return portal["url"]


async def sync_subscription_from_stripe(
    user: User, subscription_id: str, db: AsyncSession
) -> None:
    """Pull subscription state from Stripe and persist it on the user row."""
    subscription = stripe.Subscription.retrieve(subscription_id)
    price_id = subscription["items"]["data"][0]["price"]["id"]
    status = subscription["status"]

    price_map = _price_to_tier()  # function call, not module-level constant
    effective_tier = (
        price_map.get(price_id, SubscriptionTier.FREE)
        if status in {"active", "trialing"}
        else SubscriptionTier.FREE
    )

    user.stripe_subscription_id = subscription_id
    user.stripe_customer_id = subscription.get("customer") or user.stripe_customer_id
    user.stripe_price_id = price_id
    user.stripe_subscription_status = status
    user.subscription_tier = effective_tier

    period_end = subscription.get("current_period_end")
    user.subscription_period_end = (
        datetime.fromtimestamp(period_end, tz=timezone.utc) if period_end else None
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info(
        "Synced subscription for user %s — tier=%s status=%s",
        user.id, effective_tier.value, status,
    )


async def get_billing_summary(user: User) -> dict:
    """Return a billing summary payload for the API response."""
    period_end = (
        user.subscription_period_end.isoformat()
        if user.subscription_period_end
        else None
    )
    days_remaining = None
    if user.subscription_period_end:
        delta = user.subscription_period_end - datetime.now(tz=timezone.utc)
        days_remaining = max(0, delta.days)
    return {
        "tier": user.subscription_tier.value,
        "status": user.stripe_subscription_status or "free",
        "monthly_limit": TIER_LIMITS.get(user.subscription_tier, 100),
        "has_active_subscription": (user.stripe_subscription_status or "")
        in {"active", "trialing"},
        "period_end": period_end,
        "days_remaining": days_remaining,
        "stripe_customer_id": user.stripe_customer_id,
        "publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
    }
