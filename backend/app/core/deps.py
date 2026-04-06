"""
FastAPI Dependencies
Authentication, authorization, and database session management
"""

from typing import AsyncGenerator, Generator, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import (APIKeyHeader, HTTPAuthorizationCredentials,
                              HTTPBearer)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import Cache, CacheKey
from app.core.database import get_async_db
from app.core.security import verify_api_key, verify_token
from app.models.user import SubscriptionTier, User
from app.schemas.token import TokenData

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


# ============================================================================
# SUBSCRIPTION TIER DEPENDENCIES
# ============================================================================


def require_subscription_tier(required_tier: SubscriptionTier):
    """
    Dependency factory to require specific subscription tier

    Usage:
        require_pro = require_subscription_tier(SubscriptionTier.PRO)

        @app.post("/advanced-feature")
        async def advanced_feature(
            user: User = Depends(require_pro)
        ):
            return {"message": "Pro users only"}
    """

    async def check_tier(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        tier_hierarchy = {
            SubscriptionTier.FREE: 0,
            SubscriptionTier.PRO: 1,
            SubscriptionTier.TEAM: 2,
            SubscriptionTier.ENTERPRISE: 3,
        }

        user_tier_level = tier_hierarchy.get(current_user.subscription_tier, 0)
        required_tier_level = tier_hierarchy.get(required_tier, 0)

        if user_tier_level < required_tier_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This feature requires {required_tier.value} subscription or higher",
            )

        return current_user

    return check_tier


# Create common tier requirements
require_pro = require_subscription_tier(SubscriptionTier.PRO)
require_team = require_subscription_tier(SubscriptionTier.TEAM)
require_enterprise = require_subscription_tier(SubscriptionTier.ENTERPRISE)


# ============================================================================
# RATE LIMITING DEPENDENCIES
# ============================================================================

from app.core.cache import RateLimiter


async def check_rate_limit(
    endpoint: str = "default", max_requests: int = 60, window: int = 60
):
    """
    Dependency factory for rate limiting

    Usage:
        rate_limit = check_rate_limit(endpoint="search", max_requests=10)

        @app.post("/search")
        async def search(
            query: str,
            user: User = Depends(get_current_user),
            _: None = Depends(rate_limit)
        ):
            # Limited to 10 requests per minute
    """

    async def _check(
        current_user: User = Depends(get_current_user),
    ):
        allowed, remaining = await RateLimiter.check_rate_limit(
            user_id=str(current_user.id),
            endpoint=endpoint,
            max_requests=max_requests,
            window=window,
        )

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {window} seconds.",
                headers={"Retry-After": str(window)},
            )

    return _check


# ============================================================================
# USAGE QUOTA DEPENDENCIES
# ============================================================================


async def check_lead_quota(
    current_user: User = Depends(get_current_active_user),
):
    """
    Check if user has reached their monthly lead limit

    Usage:
        @app.post("/leads")
        async def create_lead(
            lead_data: LeadCreate,
            user: User = Depends(get_current_user),
            _: None = Depends(check_lead_quota)
        ):
            # Can only create if under quota
    """
    if current_user.has_reached_lead_limit():
        limit = current_user.get_monthly_lead_limit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Monthly lead limit reached ({limit}). Upgrade your plan for more leads.",
            headers={"X-Quota-Limit": str(limit)},
        )


# ============================================================================
# OPTIONAL AUTHENTICATION
# ============================================================================


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    api_key: Optional[str] = Security(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise None
    Useful for endpoints that work for both authenticated and anonymous users

    Usage:
        @app.get("/items")
        async def get_items(
            user: Optional[User] = Depends(get_current_user_optional)
        ):
            if user:
                # Show personalized results
            else:
                # Show public results
    """
    if credentials:
        try:
            return await get_current_user_from_token(credentials, db)
        except HTTPException:
            pass

    if api_key:
        try:
            return await get_current_user_from_api_key(api_key, db)
        except HTTPException:
            pass

    return None


# Export all
__all__ = [
    "get_db",
    "get_current_user",
    "get_current_user_from_token",
    "get_current_user_from_api_key",
    "get_current_active_user",
    "get_current_verified_user",
    "get_current_superuser",
    "get_current_user_optional",
    "require_subscription_tier",
    "require_pro",
    "require_team",
    "require_enterprise",
    "check_rate_limit",
    "check_lead_quota",
]
