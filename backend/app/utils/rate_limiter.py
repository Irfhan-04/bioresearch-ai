"""Redis sliding-window rate limiter utilities for Phase 2.6B."""

from __future__ import annotations

import time
from typing import Optional

from fastapi import HTTPException, Request


class RateLimiter:
    """Sliding-window rate limiter backed by Redis."""

    def __init__(self, requests: int, window_seconds: int):
        self.requests = requests
        self.window_seconds = window_seconds

    async def check(self, request: Request) -> None:
        """Check the current request against the configured limit."""

        try:
            from app.core.cache import get_async_redis

            redis = await get_async_redis()
            user_id = self._get_user_id(request)
            key = f"rate:{user_id or self._get_ip(request)}:{request.url.path}"
            now = int(time.time() * 1000)
            window_ms = self.window_seconds * 1000

            pipeline = redis.pipeline()
            pipeline.zremrangebyscore(key, 0, now - window_ms)
            pipeline.zadd(key, {str(now): now})
            pipeline.zcard(key)
            pipeline.expire(key, self.window_seconds * 2)
            results = await pipeline.execute()

            if results[2] > self.requests:
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "rate_limit_exceeded",
                        "limit": self.requests,
                        "window_secs": self.window_seconds,
                    },
                    headers={"Retry-After": str(self.window_seconds)},
                )
        except HTTPException:
            raise
        except Exception:
            return

    @staticmethod
    def _get_user_id(request: Request) -> Optional[str]:
        """Extract an unverified JWT subject from the request if present."""

        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None
        try:
            from jose import jwt as jose_jwt

            return jose_jwt.get_unverified_claims(auth[7:]).get("sub")
        except Exception:
            return None

    @staticmethod
    def _get_ip(request: Request) -> str:
        """Determine the client IP, preferring X-Forwarded-For."""

        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return getattr(request.client, "host", "unknown")


search_limiter = RateLimiter(requests=60, window_seconds=60)
enrich_limiter = RateLimiter(requests=30, window_seconds=60)
leads_limiter = RateLimiter(requests=120, window_seconds=60)
export_limiter = RateLimiter(requests=10, window_seconds=60)
