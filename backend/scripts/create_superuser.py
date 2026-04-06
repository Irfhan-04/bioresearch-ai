"""Run once: python scripts/create_superuser.py."""

import asyncio

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.user import SubscriptionTier, User


async def main():
    async with AsyncSessionLocal() as db:
        existing = (
            await db.execute(
                select(User).where(User.email == settings.FIRST_SUPERUSER_EMAIL)
            )
        ).scalar_one_or_none()

        if existing:
            print(f"Superuser already exists: {existing.email}")
            return

        user = User(
            email=settings.FIRST_SUPERUSER_EMAIL,
            password_hash=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
            full_name="Platform Admin",
            is_superuser=True,
            is_verified=True,
            subscription_tier=SubscriptionTier.ENTERPRISE,
        )
        db.add(user)
        await db.commit()
        print(f"✅ Superuser created: {user.email}")


asyncio.run(main())
