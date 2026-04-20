"""
FastAPI Application
BioResearch AI — Main API entry point
"""

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
from app.api.v1.health import router as health_router
from app.core.cache import close_redis, get_async_redis
from app.core.config import settings
from app.core.database import check_db_connection, close_db, init_db
from app.schemas.base import ErrorResponse

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================================
# LIFESPAN EVENTS
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan — startup and shutdown.

    On every deploy:
      1. Runs Alembic migrations (idempotent — safe to run on every boot)
      2. Creates the superuser account if missing
      3. Seeds demo researchers if SEED_ON_STARTUP=true

    This replaces the need for manual shell commands on platforms without
    shell access (Render free tier, Railway free tier).
    """
    logger.info("Starting BioResearch AI...")

    # ── Step 1: Run Alembic migrations ────────────────────────────────────────
    # NOTE: This subprocess block uses Render's /app path.
    # In local dev, run: cd backend && alembic upgrade head (once manually).
    # Keep this enabled only for Render deploys.
    if os.environ.get("RENDER"):
        try:
            import subprocess
            result = subprocess.run(
                ["python", "-m", "alembic", "upgrade", "head"],
                capture_output=True,
                text=True,
                cwd="/app",
            )
            if result.returncode != 0:
                logger.error(f"❌ Alembic migration failed:\n{result.stderr}")
                raise RuntimeError("Alembic migration failed")
            logger.info("✅ Alembic migrations applied")
        except Exception as e:
            logger.error(f"❌ Could not run migrations: {e}")
            raise
    else:
        logger.info("⏭️  Skipping auto-migration (not on Render)")

    # ── Step 2: Database connection check ─────────────────────────────────────
    try:
        await init_db()
        is_connected = await check_db_connection()
        if not is_connected:
            logger.error("❌ Database connection failed")
            raise RuntimeError("Database connection failed")
        logger.info("✅ Database connection established")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise

    # ── Step 3: Redis connection check ────────────────────────────────────────
    # Redis is optional for boot. If unavailable, the API still starts and
    # serves core endpoints, while cache/rate-limit features run degraded.
    try:
        redis = await get_async_redis()
        await redis.ping()
        logger.info("✅ Redis connection established")
    except Exception as e:
        logger.warning(
            f"⚠️ Redis connection failed (non-fatal): {e}. "
            "Continuing startup in degraded mode."
        )

    # ── Step 4: Auto-create superuser ─────────────────────────────────────────
    try:
        from scripts.create_superuser import create_superuser_if_missing
        await create_superuser_if_missing()
    except Exception as e:
        logger.error(f"❌ Superuser creation failed: {e}")
        # Not critical, log and continue

    # ── Step 5: Seed demo data (fire-and-forget background task) ──────────────
    # NOTE: Seed runs after startup so the app can become ready quickly on Render.
    seed_on_startup = settings.SEED_ON_STARTUP

    # ── Step 6: Check ML Model ────────────────────────────────────────────────
    try:
        from app.services.scoring_service import get_scoring_service

        service = get_scoring_service()
        if not service._model_loaded:
            logger.error(
                "❌ ML model not loaded — scorer_v1.joblib missing. "
                "Check Dockerfile RUN python ml/train_scorer.py completed."
            )
            # Non-fatal: server starts but scoring will be degraded.
        else:
            logger.info(f"✅ ML model loaded ({service._model_type})")
    except Exception as e:
        logger.error(f"❌ ML model check failed: {e}")
        # Non-fatal — do not raise, server starts degraded

    # ── Step 7: Check ChromaDB ────────────────────────────────────────────────
    try:
        from app.services.embedding_service import get_embedding_service

        service = get_embedding_service()
        count = service.get_index_count()
        if count == 0:
            logger.warning(
                "⚠️ ChromaDB is empty — researchers not yet indexed. "
                "Run seed or enrich researchers to populate the vector index."
            )
        else:
            logger.info(f"✅ ChromaDB OK ({count} researchers indexed)")
    except Exception as e:
        logger.warning(f"⚠️ ChromaDB check failed (non-fatal): {e}")
        # ChromaDB initialises lazily — not fatal on cold start

    logger.info("🚀 BioResearch AI is ready!")

    # ── Background seed (non-blocking startup) ────────────────────────────────
    if seed_on_startup:

        async def _run_seed():
            logger.info("🌱 Background seed starting...")
            try:
                import subprocess

                result = await asyncio.to_thread(
                    subprocess.run,
                    ["python", "scripts/seed_demo_data.py"],
                    capture_output=True,
                    text=True,
                    cwd="/app",
                    timeout=900,
                )
                if result.returncode != 0:
                    logger.error(f"❌ Seed failed:\n{result.stderr}")
                else:
                    logger.info("✅ Background seed complete")
                    if result.stdout:
                        tail = result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout
                        logger.info(tail)
            except Exception as e:
                logger.error(f"❌ Background seed error: {e}")

        asyncio.create_task(_run_seed())
        logger.info("🌱 Seed task scheduled (runs in background)")
    else:
        logger.info("⏭️  SEED_ON_STARTUP=false — skipping seed")

    yield

    # ── Shutdown ───────────────────────────────────────────────────────────────
    logger.info("Shutting down...")
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
        "message": "BioResearch AI — Biotech Research Intelligence API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", include_in_schema=False)
async def health():
    """Redirect to health check endpoint."""
    return {"message": "Use /health/ for detailed health checks"}


# ============================================================================
# API ROUTES
# ============================================================================

app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(health_router, prefix="/health")


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
