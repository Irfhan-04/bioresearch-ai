from __future__ import annotations

"""
FastAPI Dependencies
Authentication, authorization, and database session management
"""

from typing import AsyncGenerator, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import (APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import Cache, CacheKey
from app.core.database import get_async_db
from app.core.security import verify_api_key, verify_token
from app.schemas.token import TokenData
from fastapi import Depends, HTTPException, Request, Security, status

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


# ============================================================================
# DATABASE DEPENDENCIES
# ============================================================================


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get async database session
    This is a dependency that provides database access to endpoints

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            items = await db.execute(select(Item))
            return items.scalars().all()
    """
    async for session in get_async_db():
        yield session


# ============================================================================
# AUTHENTICATION DEPENDENCIES
# ============================================================================


async def get_current_user_from_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Get current user from JWT Bearer token

    Args:
        credentials: Bearer token from Authorization header
        db: Database session

    Returns:
        User object if authenticated, None otherwise
    """
    if not credentials:
        return None

    # Verify token
    token_data = verify_token(credentials.credentials, token_type="access")

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user_id from token
    user_id = token_data.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check cache first
    cache_key = CacheKey.user_session(user_id)
    cached_user_data = await Cache.get(cache_key)

    if cached_user_data:
        # Return user from cache
        # Note: In production, you might want to periodically refresh from DB
        user_id_uuid = UUID(user_id)
        result = await db.execute(select(User).where(User.id == user_id_uuid))
        user = result.scalar_one_or_none()
    else:
        # Get user from database
        try:
            user_id_uuid = UUID(user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user ID in token",
            )

        result = await db.execute(select(User).where(User.id == user_id_uuid))
        user = result.scalar_one_or_none()

        if user:
            # Cache user data
            await Cache.set(
                cache_key, {"id": str(user.id), "email": user.email}, ttl=3600  # 1 hour
            )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_user_from_api_key(
    api_key: Optional[str] = Security(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Get current user from API key

    Args:
        api_key: API key from X-API-Key header
        db: Database session

    Returns:
        User object if authenticated, None otherwise
    """
    if not api_key:
        return None

    # Check cache for API key
    cache_key = CacheKey.api_key(api_key)
    cached_user_id = await Cache.get(cache_key)

    if cached_user_id:
        user_id_uuid = UUID(cached_user_id)
        result = await db.execute(select(User).where(User.id == user_id_uuid))
        user = result.scalar_one_or_none()
    else:
        # Query all users and check API keys
        # Note: In production, store API keys in separate table with index
        result = await db.execute(select(User))
        users = result.scalars().all()

        user = None
        for potential_user in users:
            if potential_user.api_keys:
                for key_data in potential_user.api_keys:
                    if verify_api_key(api_key, key_data.get("hash", "")):
                        user = potential_user
                        # Cache the user_id for this API key
                        await Cache.set(cache_key, str(user.id), ttl=86400)  # 24 hours
                        break
                if user:
                    break

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return user


async def get_current_user(
    user_from_token: Optional[User] = Depends(get_current_user_from_token),
    user_from_api_key: Optional[User] = Depends(get_current_user_from_api_key),
) -> User:
    """
    Get current user from either JWT token or API key
    Tries token first, then API key

    Usage:
        @app.get("/me")
        async def get_me(current_user: User = Depends(get_current_user)):
            return current_user
    """
    user = user_from_token or user_from_api_key

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current active user (not disabled)

    Usage:
        @app.get("/protected")
        async def protected_route(user: User = Depends(get_current_active_user)):
            return {"message": "You have access"}
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive"
        )

    return current_user


async def get_current_verified_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Get current verified user (email verified)

    Usage:
        @app.post("/premium-feature")
        async def premium_feature(user: User = Depends(get_current_verified_user)):
            return {"message": "Verified users only"}
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Email verification required"
        )

    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Get current superuser (admin)

    Usage:
        @app.delete("/admin/users/{user_id}")
        async def delete_user(
            user_id: UUID,
            admin: User = Depends(get_current_superuser)
        ):
            # Only admins can delete users
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser privileges required",
        )

    return current_user

async def check_researcher_quota(current_user: User = Depends(get_current_active_user)) -> None:
    """Compatibility quota dependency (currently no-op)."""
    _ = current_user
    return None

async def get_redis():
    """Return redis cache backend."""
    return Cache

async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional["User"]:
    """
    Returns the authenticated User if a valid Bearer token is present,
    or None for unauthenticated (guest) requests.

    Used by endpoints that allow guest access with reduced limits.
    """
    if not credentials:
        return None
    token_data = verify_token(credentials.credentials, token_type="access")
    if not token_data:
        return None
    user_id = token_data.get("sub")
    if not user_id:
        return None
    from app.models.user import User
    result = await db.execute(
        select(User).where(User.id == user_id, User.is_active == True)
    )
    return result.scalar_one_or_none()


async def check_search_quota(
    request: Request,
    current_user: Optional["User"] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Enforces daily search limits for both guests and registered users.

    Guest (no token):      3 searches/day, keyed by IP address in Redis
    Registered (free):    20 searches/day, keyed by user_id in Redis

    Returns a dict with quota information so the endpoint can include it
    in the response:
        {"is_guest": bool, "searches_used": int, "searches_limit": int}

    Raises HTTP 429 when the limit is exceeded.
    """
    from app.core.config import settings
    from app.core.cache import get_async_redis
    from datetime import datetime, timezone
    import time

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if current_user is None:
        # Guest: key by IP
        ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        if not ip:
            ip = getattr(request.client, "host", "unknown")
        redis_key = f"guest_searches:{ip}:{today}"
        limit = settings.GUEST_DAILY_SEARCHES
    else:
        # Registered user: key by user_id
        redis_key = f"user_searches:{current_user.id}:{today}"
        limit = settings.REGISTERED_DAILY_SEARCHES

    try:
        redis = await get_async_redis()
        current_count = await redis.get(redis_key)
        count = int(current_count) if current_count else 0

        if count >= limit:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "daily_limit_exceeded",
                    "message": (
                        f"You've used all {limit} daily searches."
                        + (" Sign up free for 20 searches/day."
                           if current_user is None
                           else " Your limit resets at midnight UTC.")
                    ),
                    "searches_used": count,
                    "searches_limit": limit,
                    "is_guest": current_user is None,
                    "resets_at": f"{today}T23:59:59Z",
                },
                headers={"Retry-After": str(
                    int(time.mktime(datetime.strptime(
                        f"{today} 23:59:59", "%Y-%m-%d %H:%M:%S"
                    ).timetuple())) - int(time.time())
                )},
            )

        # Increment counter, expire at end of day
        pipe = redis.pipeline()
        pipe.incr(redis_key)
        pipe.expireat(redis_key, int(time.mktime(
            datetime.strptime(f"{today} 23:59:59", "%Y-%m-%d %H:%M:%S").timetuple()
        )))
        await pipe.execute()

        return {
            "is_guest": current_user is None,
            "searches_used": count + 1,
            "searches_limit": limit,
        }
    except HTTPException:
        raise
    except Exception:
        # Redis failure — fail open (don't block users if Redis is down)
        return {
            "is_guest": current_user is None,
            "searches_used": 0,
            "searches_limit": limit,
        }
