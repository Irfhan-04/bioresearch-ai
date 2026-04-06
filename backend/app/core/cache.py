"""
Redis cache configuration and utilities
Supports both regular Redis and Upstash Redis
"""

import json
import pickle
from functools import wraps
from typing import Any, Callable, Optional

import redis.asyncio as aioredis
from redis import Redis

from app.core.config import get_redis_url, settings

# ============================================================================
# REDIS CLIENT SETUP
# ============================================================================

# Sync Redis client (for Celery and simple operations)
sync_redis_client: Optional[Redis] = None

# Async Redis client (for FastAPI endpoints)
async_redis_client: Optional[aioredis.Redis] = None


def get_sync_redis() -> Redis:
    """
    Get synchronous Redis client

    Usage:
        redis = get_sync_redis()
        redis.set("key", "value")
        value = redis.get("key")
    """
    global sync_redis_client

    if sync_redis_client is None:
        sync_redis_client = Redis.from_url(
            get_redis_url(),
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )

    return sync_redis_client


async def get_async_redis() -> aioredis.Redis:
    """
    Get asynchronous Redis client

    Usage:
        redis = await get_async_redis()
        await redis.set("key", "value")
        value = await redis.get("key")
    """
    global async_redis_client

    if async_redis_client is None:
        async_redis_client = await aioredis.from_url(
            get_redis_url(),
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )

    return async_redis_client


async def close_redis() -> None:
    """
    Close Redis connections
    Call this on application shutdown
    """
    global async_redis_client, sync_redis_client

    if async_redis_client:
        await async_redis_client.close()
        async_redis_client = None

    if sync_redis_client:
        sync_redis_client.close()
        sync_redis_client = None


# ============================================================================
# CACHE UTILITIES
# ============================================================================


class CacheKey:
    """
    Cache key builder with consistent formatting
    """

    @staticmethod
    def user_session(user_id: str) -> str:
        return f"session:user:{user_id}"

    @staticmethod
    def lead_search(query_hash: str) -> str:
        return f"search:leads:{query_hash}"

    @staticmethod
    def lead_data(lead_id: str) -> str:
        return f"lead:data:{lead_id}"

    @staticmethod
    def enrichment(lead_id: str, enrichment_type: str) -> str:
        return f"enrichment:{lead_id}:{enrichment_type}"

    @staticmethod
    def pubmed_results(query: str) -> str:
        return f"pubmed:results:{query}"

    @staticmethod
    def rate_limit(user_id: str, endpoint: str) -> str:
        return f"ratelimit:{user_id}:{endpoint}"

    @staticmethod
    def api_key(key: str) -> str:
        return f"apikey:{key}"

    @staticmethod
    def user_quota(user_id: str, period: str) -> str:
        """period: 'daily', 'monthly', 'yearly'"""
        return f"quota:{user_id}:{period}"

    @staticmethod
    def pubmed_author_profile(author_name_or_hash: str) -> str:
        """
        Cache key for a full author citation profile.
        TTL: 7 days
        Input should be the SHA-256 hash — use PubMedService._build_cache_key()
        to generate the full key, not this helper directly.
        Kept here for visibility and documentation of the key namespace.
        """
        return f"pubmed:profile:{author_name_or_hash}"

    @staticmethod
    def pubmed_citation_batch(pmids_hash: str) -> str:
        """
        Cache key for a batch of citation counts.
        TTL: 3 days
        """
        return f"pubmed:citations:{pmids_hash}"

    @staticmethod
    def linkedin_profile(lead_id_and_name_hash: str) -> str:
        """
        Cache key for a LinkedIn profile lookup result.
        TTL: 7 days — preserves Google CSE daily quota.
        Use LinkedInService._build_cache_key(lead) to generate the hash.
        """
        return f"linkedin:profile:{lead_id_and_name_hash}"

    @staticmethod
    def conference_speakers(conference_key: str, year: int) -> str:
        """
        Cache key for a conference's full speaker list.
        TTL: 365 days — annual events, scraped once per year.
        Format: conference:speakers:{key}:{year}
        Example: conference:speakers:sot:2025
        """
        return f"conference:speakers:{conference_key.lower()}:{year}"

    @staticmethod
    def nih_keyword_search(query_hash: str) -> str:
        """
        Cache key for a NIH RePORTER keyword search result.
        TTL: 24 hours.
        Use FundingService._build_cache_key() to generate the hash.
        """
        return f"nih:keywords:{query_hash}"

    @staticmethod
    def nih_pi_grants(name_hash: str) -> str:
        """
        Cache key for a specific PI's grant portfolio.
        TTL: 7 days.
        """
        return f"nih:pi:{name_hash}"

    @staticmethod
    def email_finder(lead_id_name_hash: str) -> str:
        """
        Cache key for an email finder result.
        TTL: 30 days — email addresses are stable.
        Use EmailFinder._email_cache_key(lead) to build the hash.
        """
        return f"email:finder:{lead_id_name_hash}"

    @staticmethod
    def hunter_domain(domain_hash: str) -> str:
        """
        Cache key for a Hunter.io domain search result.
        TTL: 7 days — domain emails list is fairly stable.
        Shared across all leads at the same company domain.
        """
        return f"hunter:domain:{domain_hash}"

    @staticmethod
    def clearbit_company(domain_hash: str) -> str:
        """
        Cache key for a Clearbit company lookup.
        TTL: 30 days — company data is stable.
        Shared across all leads from the same company.
        """
        return f"clearbit:company:{domain_hash}"



class Cache:
    """
    High-level cache interface
    """

    @staticmethod
    async def get(key: str) -> Optional[Any]:
        """
        Get value from cache
        Automatically deserializes JSON
        """
        redis = await get_async_redis()
        value = await redis.get(key)

        if value is None:
            return None

        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    @staticmethod
    async def set(
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to store (auto-serializes to JSON)
            ttl: Time to live in seconds
            nx: Only set if key doesn't exist
            xx: Only set if key exists

        Returns:
            True if successful
        """
        redis = await get_async_redis()

        # Serialize value
        if not isinstance(value, (str, bytes)):
            value = json.dumps(value)

        # Set with options
        if ttl:
            return await redis.set(key, value, ex=ttl, nx=nx, xx=xx)
        else:
            return await redis.set(key, value, nx=nx, xx=xx)

    @staticmethod
    async def delete(key: str) -> int:
        """
        Delete key from cache
        Returns number of keys deleted
        """
        redis = await get_async_redis()
        return await redis.delete(key)

    @staticmethod
    async def exists(key: str) -> bool:
        """
        Check if key exists
        """
        redis = await get_async_redis()
        return await redis.exists(key) > 0

    @staticmethod
    async def expire(key: str, ttl: int) -> bool:
        """
        Set expiration on existing key
        """
        redis = await get_async_redis()
        return await redis.expire(key, ttl)

    @staticmethod
    async def increment(key: str, amount: int = 1) -> int:
        """
        Increment numeric value
        Returns new value
        """
        redis = await get_async_redis()
        return await redis.incrby(key, amount)

    @staticmethod
    async def decrement(key: str, amount: int = 1) -> int:
        """
        Decrement numeric value
        Returns new value
        """
        redis = await get_async_redis()
        return await redis.decrby(key, amount)

    @staticmethod
    async def get_many(keys: list[str]) -> list[Optional[Any]]:
        """
        Get multiple values at once
        """
        redis = await get_async_redis()
        values = await redis.mget(keys)

        result = []
        for value in values:
            if value is None:
                result.append(None)
            else:
                try:
                    result.append(json.loads(value))
                except json.JSONDecodeError:
                    result.append(value)

        return result

    @staticmethod
    async def set_many(mapping: dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        Set multiple key-value pairs at once
        """
        redis = await get_async_redis()

        # Serialize all values
        serialized = {}
        for key, value in mapping.items():
            if not isinstance(value, (str, bytes)):
                serialized[key] = json.dumps(value)
            else:
                serialized[key] = value

        # Set all at once
        await redis.mset(serialized)

        # Set expiration if provided
        if ttl:
            pipeline = redis.pipeline()
            for key in serialized.keys():
                pipeline.expire(key, ttl)
            await pipeline.execute()

        return True

    @staticmethod
    async def clear_pattern(pattern: str) -> int:
        """
        Delete all keys matching pattern
        Example: clear_pattern("session:*")

        Returns number of keys deleted
        """
        redis = await get_async_redis()
        keys = []

        async for key in redis.scan_iter(match=pattern):
            keys.append(key)

        if keys:
            return await redis.delete(*keys)
        return 0


# ============================================================================
# CACHE DECORATORS
# ============================================================================


def cached(key_prefix: str, ttl: int = 3600, key_builder: Optional[Callable] = None):
    """
    Decorator to cache function results

    Usage:
        @cached(key_prefix="user", ttl=300)
        async def get_user(user_id: str):
            # This will be cached for 5 minutes
            return await db.query(User).filter_by(id=user_id).first()
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Simple key from arguments
                key_parts = [str(arg) for arg in args]
                key_parts.extend([f"{k}={v}" for k, v in kwargs.items()])
                cache_key = f"{key_prefix}:{':'.join(key_parts)}"

            # Try to get from cache
            cached_value = await Cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Execute function
            result = await func(*args, **kwargs)

            # Store in cache
            await Cache.set(cache_key, result, ttl=ttl)

            return result

        return wrapper

    return decorator


def invalidate_cache(key_pattern: str):
    """
    Decorator to invalidate cache after function execution

    Usage:
        @invalidate_cache("user:*")
        async def update_user(user_id: str, data: dict):
            # This will clear all user:* cache entries
            return await db.update(User, user_id, data)
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            await Cache.clear_pattern(key_pattern)
            return result

        return wrapper

    return decorator


# ============================================================================
# SESSION MANAGEMENT
# ============================================================================


class SessionManager:
    """
    Manage user sessions in Redis
    """

    @staticmethod
    async def create_session(
        user_id: str, session_data: dict, ttl: int = settings.REDIS_SESSION_TTL
    ) -> str:
        """
        Create new session
        Returns session_id
        """
        import uuid

        session_id = str(uuid.uuid4())

        key = CacheKey.user_session(session_id)
        data = {"user_id": user_id, "created_at": str(datetime.now()), **session_data}

        await Cache.set(key, data, ttl=ttl)
        return session_id

    @staticmethod
    async def get_session(session_id: str) -> Optional[dict]:
        """
        Get session data
        """
        key = CacheKey.user_session(session_id)
        return await Cache.get(key)

    @staticmethod
    async def update_session(session_id: str, data: dict) -> bool:
        """
        Update session data
        """
        key = CacheKey.user_session(session_id)
        existing = await Cache.get(key)

        if existing:
            existing.update(data)
            return await Cache.set(key, existing, ttl=settings.REDIS_SESSION_TTL)

        return False

    @staticmethod
    async def delete_session(session_id: str) -> int:
        """
        Delete session
        """
        key = CacheKey.user_session(session_id)
        return await Cache.delete(key)


# ============================================================================
# RATE LIMITING
# ============================================================================


class RateLimiter:
    """
    Token bucket rate limiter using Redis
    """

    @staticmethod
    async def check_rate_limit(
        user_id: str,
        endpoint: str,
        max_requests: int = settings.RATE_LIMIT_PER_MINUTE,
        window: int = 60,
    ) -> tuple[bool, int]:
        """
        Check if request is within rate limit

        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        key = CacheKey.rate_limit(user_id, endpoint)
        redis = await get_async_redis()

        # Get current count
        current = await redis.get(key)

        if current is None:
            # First request in window
            await redis.setex(key, window, 1)
            return True, max_requests - 1

        current = int(current)

        if current >= max_requests:
            # Rate limit exceeded
            ttl = await redis.ttl(key)
            return False, 0

        # Increment counter
        await redis.incr(key)
        return True, max_requests - current - 1


# Import datetime
from datetime import datetime

# Export all
__all__ = [
    "get_sync_redis",
    "get_async_redis",
    "close_redis",
    "CacheKey",
    "Cache",
    "cached",
    "invalidate_cache",
    "SessionManager",
    "RateLimiter",
]
