#!/usr/bin/env python3
"""Quick Redis connection test - run this before anything else."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


async def test_redis() -> bool:
    from app.core.cache import get_async_redis
    from app.core.config import settings

    print(f"Connecting to Redis at: {settings.REDIS_URL[:40]}...")

    try:
        redis = await get_async_redis()

        await redis.set("health_check", "ok", ex=30)
        value = await redis.get("health_check")
        assert value == "ok", f"Expected 'ok', got '{value}'"
        await redis.delete("health_check")

        print("[PASS] Redis connection working")
        print(f"[INFO] Server info: {await redis.info('server')}")
        return True
    except Exception as exc:
        print(f"[FAIL] Redis connection failed: {exc}")
        print("\nCheck your REDIS_URL in .env:")
        print("  Format: redis://default:PASSWORD@host:6379")
        return False


if __name__ == "__main__":
    result = asyncio.run(test_redis())
    sys.exit(0 if result else 1)
