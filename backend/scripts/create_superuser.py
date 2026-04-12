"""
create_superuser.py

Creates the initial admin user. Called automatically from main.py lifespan
on first startup when FIRST_SUPERUSER_EMAIL is set.

Can also be run manually in environments with shell access:
    uv run python scripts/create_superuser.py
"""

import asyncio

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.user import User


async def create_superuser_if_missing() -> bool:
    """
    Create the superuser account if it does not already exist.
    Returns True if created, False if already exists.
    """
    async with AsyncSessionLocal() as db:
        existing = (
            await db.execute(
                select(User).where(User.email == settings.FIRST_SUPERUSER_EMAIL)
            )
        ).scalar_one_or_none()

        if existing:
            print(f"Superuser already exists: {existing.email}")
            return False

        user = User(
            email=settings.FIRST_SUPERUSER_EMAIL,
            password_hash=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
            full_name="Platform Admin",
            is_superuser=True,
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        await db.commit()
        print(f"✅ Superuser created: {user.email}")
        return True


if __name__ == "__main__":
    asyncio.run(create_superuser_if_missing())