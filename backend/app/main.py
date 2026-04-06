"""
FastAPI Application
Main entry point for the Biotech Lead Generator API
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
from app.core.cache import close_redis, get_async_redis
from app.core.config import settings
from app.core.database import check_db_connection, close_db, init_db
from app.schemas.base import ErrorResponse, HealthCheckResponse

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ── Paths that should NOT count as API calls ──────────────────────────────────
# Exact path matches and prefixes are both supported.
_SKIP_API_CALL_PATHS = frozenset({
    "/",
    "/health",
    "/docs",
    "/redoc",
    f"{settings.API_V1_PREFIX}/openapi.json",
})
_SKIP_API_CALL_PREFIXES = (
    "/docs",
    "/redoc",
    "/openapi",
)


# ============================================================================
# LIFESPAN EVENTS
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events — startup and shutdown."""
    logger.info("Starting Biotech Lead Generator API...")
    logger.info(f"Environment: {settings.SENTRY_ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    try:
        await init_db()
        is_connected = await check_db_connection()
        if is_connected:
            logger.info("✅ Database connection established")
        else:
            logger.error("❌ Database connection failed")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")

    try:
        redis = await get_async_redis()
        await redis.ping()
        logger.info("✅ Redis connection established")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")

    if settings.SENTRY_DSN:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.SENTRY_ENVIRONMENT,
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        )
        logger.info("✅ Sentry monitoring initialized")

    logger.info("🚀 API is ready!")
    yield

    logger.info("Shutting down API...")
    try:
        await close_db()
        logger.info("✅ Database connections closed")
    except Exception as e:
        logger.error(f"❌ Error closing database: {e}")

    try:
        await close_redis()
        logger.info("✅ Redis connections closed")
    except Exception as e:
        logger.error(f"❌ Error closing Redis: {e}")

    logger.info("👋 API shutdown complete")


# ============================================================================
# CREATE FASTAPI APP
# ============================================================================

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    lifespan=lifespan,
)


# ============================================================================
# MIDDLEWARE
# ============================================================================

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Trusted host (security)
if not settings.DEBUG:
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["*"]
    )


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add X-Process-Time header to every response."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))
    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with method, path, and status code."""
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"{request.method} {request.url.path} - {response.status_code}")
    return response


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add OWASP-recommended security headers to every response."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if not settings.DEBUG:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    return response


@app.middleware("http")
async def record_api_call(request: Request, call_next):
    """
    Record one API_CALL UsageEvent for every authenticated request to /api/v1/*.

    Strategy
    --------
    • Only fires for paths under API_V1_PREFIX — skips health, docs, root.
    • Extracts user_id from JWT via a lightweight decode (no DB hit).
    • Writes the UsageEvent AFTER call_next() so only successful calls count.
      (If auth middleware already rejected the request, we never write a row.)
    • Uses fire-and-forget (asyncio.create_task) so recording never adds
      latency to the response.
    • Errors in recording are caught and logged — they never surface to the client.

    Why middleware instead of per-endpoint?
    • 11 endpoints × future endpoints = maintenance burden.
    • Middleware guarantees 100% coverage including routes added in Phase 2.5+.
    """
    path = request.url.path

    # Only track /api/v1/* paths
    if not path.startswith(settings.API_V1_PREFIX):
        return await call_next(request)

    # Skip non-user-facing paths
    if path in _SKIP_API_CALL_PATHS or path.startswith(_SKIP_API_CALL_PREFIXES):
        return await call_next(request)

    # Extract JWT without hitting the DB
    user_id = _extract_user_id_from_request(request)

    # Execute the actual endpoint
    response = await call_next(request)

    # Only record if the request was authenticated (user found) and succeeded
    # (2xx or 4xx business errors — exclude 401/403 which mean no valid session)
    if user_id and response.status_code not in (401, 403):
        import asyncio
        asyncio.create_task(_write_api_call_event(user_id, path, request.method))

    return response


def _extract_user_id_from_request(request: Request):
    """
    Decode JWT from Authorization header to extract user_id.
    Returns None if header is absent or token is malformed.
    Does NOT verify expiry or signature — auth middleware already did that.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header[len("Bearer "):]
    try:
        from jose import jwt as jose_jwt
        # Decode without verification — we only need the payload user_id
        payload = jose_jwt.get_unverified_claims(token)
        return payload.get("sub")
    except Exception:
        return None


async def _write_api_call_event(user_id: str, path: str, method: str) -> None:
    """
    Write a single API_CALL UsageEvent row.
    Runs as a background task — any exception is caught and logged.
    """
    try:
        from uuid import UUID
        from app.core.database import AsyncSessionLocal
        from app.models.usage import UsageEventType
        from app.services.usage_service import UsageService

        async with AsyncSessionLocal() as db:
            await UsageService.record(
                db=db,
                user_id=UUID(user_id),
                event_type=UsageEventType.API_CALL,
                quantity=1,
                metadata={"path": path, "method": method},
            )
            await db.commit()
    except Exception as exc:
        logger.warning("record_api_call background task failed: %s", exc)


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    errors = [
        {
            "field": " -> ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            message="Validation error", error_code="VALIDATION_ERROR", details=errors
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors."""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    if settings.DEBUG:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                message="Internal server error",
                error_code="INTERNAL_ERROR",
                details=str(exc),
            ).model_dump(),
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            message="An unexpected error occurred", error_code="INTERNAL_ERROR"
        ).model_dump(),
    )


# ============================================================================
# ROOT ENDPOINTS
# ============================================================================


@app.get("/", tags=["Root"], summary="API Root")
async def root():
    return {
        "message": "Welcome to Biotech Lead Generator API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
    }


@app.get(
    "/health",
    response_model=HealthCheckResponse,
    tags=["Root"],
    summary="Health Check",
)
async def health_check():
    from datetime import datetime

    try:
        db_status = "connected" if await check_db_connection() else "disconnected"
    except Exception:
        db_status = "error"

    try:
        redis = await get_async_redis()
        await redis.ping()
        cache_status = "connected"
    except Exception:
        cache_status = "disconnected"

    overall_status = (
        "healthy"
        if (db_status == "connected" and cache_status == "connected")
        else "degraded"
    )

    return HealthCheckResponse(
        status=overall_status,
        version=settings.APP_VERSION,
        database=db_status,
        cache=cache_status,
        timestamp=datetime.utcnow(),
    )


# ============================================================================
# API ROUTES
# ============================================================================

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# ============================================================================
# RUN APPLICATION
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else settings.WORKERS,
        log_level=settings.LOG_LEVEL.lower(),
    )