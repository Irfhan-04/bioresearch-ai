from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from app.services.scoring_service import get_scoring_service
from app.services.embedding_service import get_embedding_service
from app.core.database import check_db_connection
from app.core.cache import get_async_redis
from app.core.config import settings
import logging

router = APIRouter(prefix="/health", tags=["Health"])
logger = logging.getLogger(__name__)

@router.get("/", summary="Overall Health Check")
async def health_check():
    """
    Check all critical dependencies:
    - PostgreSQL
    - Redis
    - ChromaDB
    - ML Model
    """
    checks = {
        "postgresql": await _check_postgresql(),
        "redis": await _check_redis(),
        "chromadb": await _check_chromadb(),
        "ml_model": await _check_ml_model(),
    }
    all_ok = all(check["status"] == "ok" for check in checks.values())
    if all_ok:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "ok",
                "service": "bioresearch-ai-backend",
                "checks": checks,
            },
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "error",
                "service": "bioresearch-ai-backend",
                "checks": checks,
            },
        )

async def _check_postgresql():
    try:
        is_connected = await check_db_connection()
        return {
            "service": "postgresql",
            "status": "ok" if is_connected else "error",
            "message": "Database connection OK" if is_connected else "Database connection failed",
        }
    except Exception as e:
        return {
            "service": "postgresql",
            "status": "error",
            "message": f"Database error: {str(e)}",
        }

async def _check_redis():
    try:
        redis = await get_async_redis()
        await redis.ping()
        return {
            "service": "redis",
            "status": "ok",
            "message": "Redis connection OK",
        }
    except Exception as e:
        return {
            "service": "redis",
            "status": "error",
            "message": f"Redis error: {str(e)}",
        }

async def _check_chromadb():
    try:
        service = get_embedding_service()
        count = service.get_index_count()
        return {
            "service": "chromadb",
            "status": "ok",
            "message": f"ChromaDB OK ({count} researchers indexed)",
        }
    except Exception as e:
        return {
            "service": "chromadb",
            "status": "error",
            "message": f"ChromaDB error: {str(e)}",
        }

async def _check_ml_model():
    try:
        service = get_scoring_service()
        if service._model_loaded:
            return {
                "service": "ml_model",
                "status": "ok",
                "message": f"Model loaded ({service._model_type})",
            }
        else:
            return {
                "service": "ml_model",
                "status": "error",
                "message": "Model not loaded",
            }
    except Exception as e:
        return {
            "service": "ml_model",
            "status": "error",
            "message": f"Model error: {str(e)}",
        }

@router.get("/scoring", summary="ML Model Health Check")
async def scoring_health():
    """Check if the ML model is loaded and ready."""
    try:
        service = get_scoring_service()
        if service._model_loaded:
            return {
                "status": "ok",
                "model_type": service._model_type,
                "message": "ML model is ready",
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="ML model not loaded",
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"ML model error: {str(e)}",
        )

@router.get("/embeddings", summary="Embedding Service Health Check")
async def embeddings_health():
    """Check if ChromaDB and the embedding model are accessible."""
    try:
        service = get_embedding_service()
        count = service.get_index_count()
        return {
            "status": "ok",
            "chromadb_count": count,
            "message": "Embedding service is ready",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Embedding service error: {str(e)}",
        )