"""
Centralized Logging Configuration
Production-ready logging with structured output and integrations
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from pythonjsonlogger import jsonlogger

from app.core.config import settings


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter with additional context
    """

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any],
    ) -> None:
        """Add custom fields to log record"""
        super().add_fields(log_record, record, message_dict)

        # Add timestamp
        log_record["timestamp"] = datetime.utcnow().isoformat()

        # Add service info
        log_record["service"] = settings.APP_NAME
        log_record["version"] = settings.APP_VERSION
        log_record["environment"] = settings.SENTRY_ENVIRONMENT

        # Add log level
        log_record["level"] = record.levelname

        # Add logger name
        log_record["logger"] = record.name

        # Add file info
        log_record["file"] = record.pathname
        log_record["line"] = record.lineno
        log_record["function"] = record.funcName


class ContextFilter(logging.Filter):
    """
    Add contextual information to log records
    """

    def __init__(self, context: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.context = context or {}

    def filter(self, record: logging.LogRecord) -> bool:
        """Add context to record"""
        for key, value in self.context.items():
            setattr(record, key, value)
        return True


def setup_logging(
    level: Optional[str] = None,
    log_file: Optional[str] = None,
    json_format: bool = None,
) -> None:
    """
    Configure application logging

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (None for stdout only)
        json_format: Use JSON format (auto-detect from settings if None)
    """
    # Determine log level
    log_level = level or settings.LOG_LEVEL
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Determine format
    use_json = json_format if json_format is not None else settings.LOG_FORMAT == "json"

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    root_logger.handlers = []

    # Create formatters
    if use_json:
        formatter = CustomJsonFormatter(
            "%(timestamp)s %(level)s %(name)s %(message)s"
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler
    if log_file:
        file_path = Path(log_file)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(file_path)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Set third-party logger levels
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.WARNING)

    # Log startup message
    root_logger.info(
        f"Logging configured: level={log_level}, format={'JSON' if use_json else 'TEXT'}"
    )


def get_logger(name: str, context: Optional[Dict[str, Any]] = None) -> logging.Logger:
    """
    Get logger with optional context

    Args:
        name: Logger name (usually __name__)
        context: Additional context to include in logs

    Returns:
        Configured logger

    Usage:
        logger = get_logger(__name__, {"user_id": "123"})
        logger.info("User action", extra={"action": "login"})
    """
    logger = logging.getLogger(name)

    if context:
        logger.addFilter(ContextFilter(context))

    return logger


class LoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter for adding consistent context
    """

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        """Add extra context to log messages"""
        extra = kwargs.get("extra", {})
        extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs


def get_request_logger(request_id: str) -> LoggerAdapter:
    """
    Get logger with request context

    Args:
        request_id: Unique request identifier

    Returns:
        Logger with request context

    Usage:
        logger = get_request_logger(request_id)
        logger.info("Processing request")
    """
    logger = logging.getLogger("api")
    return LoggerAdapter(logger, {"request_id": request_id})


def log_function_call(func):
    """
    Decorator to log function calls

    Usage:
        @log_function_call
        def my_function(arg1, arg2):
            pass
    """
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        logger.debug(
            f"Calling {func.__name__}",
            extra={
                "function": func.__name__,
                "args": args,
                "kwargs": kwargs,
            },
        )

        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(
                f"{func.__name__} failed",
                extra={
                    "function": func.__name__,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    return wrapper


def log_async_function_call(func):
    """
    Decorator to log async function calls

    Usage:
        @log_async_function_call
        async def my_async_function(arg1, arg2):
            pass
    """
    from functools import wraps

    @wraps(func)
    async def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        logger.debug(
            f"Calling {func.__name__}",
            extra={
                "function": func.__name__,
                "args": args,
                "kwargs": kwargs,
            },
        )

        try:
            result = await func(*args, **kwargs)
            logger.debug(f"{func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(
                f"{func.__name__} failed",
                extra={
                    "function": func.__name__,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    return wrapper


# Convenience logging functions
def log_api_request(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    user_id: Optional[str] = None,
) -> None:
    """
    Log API request

    Args:
        method: HTTP method
        path: Request path
        status_code: Response status code
        duration_ms: Request duration in milliseconds
        user_id: Optional user ID
    """
    logger = logging.getLogger("api.access")

    extra = {
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": duration_ms,
    }

    if user_id:
        extra["user_id"] = user_id

    level = logging.INFO if status_code < 400 else logging.WARNING

    logger.log(
        level,
        f"{method} {path} - {status_code} ({duration_ms:.2f}ms)",
        extra=extra,
    )


def log_database_query(
    query: str, duration_ms: float, rows_affected: Optional[int] = None
) -> None:
    """
    Log database query

    Args:
        query: SQL query (truncated)
        duration_ms: Query duration
        rows_affected: Number of rows affected
    """
    logger = logging.getLogger("database")

    # Truncate query for logging
    truncated_query = query[:200] + "..." if len(query) > 200 else query

    extra = {
        "query": truncated_query,
        "duration_ms": duration_ms,
    }

    if rows_affected is not None:
        extra["rows_affected"] = rows_affected

    logger.debug(f"Query executed ({duration_ms:.2f}ms)", extra=extra)


def log_cache_operation(
    operation: str, key: str, hit: bool, duration_ms: Optional[float] = None
) -> None:
    """
    Log cache operation

    Args:
        operation: get, set, delete
        key: Cache key
        hit: Whether operation was successful
        duration_ms: Operation duration
    """
    logger = logging.getLogger("cache")

    extra = {
        "operation": operation,
        "key": key,
        "hit": hit,
    }

    if duration_ms is not None:
        extra["duration_ms"] = duration_ms

    logger.debug(
        f"Cache {operation}: {'HIT' if hit else 'MISS'} - {key}",
        extra=extra,
    )


def log_external_api_call(
    service: str, endpoint: str, status_code: int, duration_ms: float
) -> None:
    """
    Log external API call

    Args:
        service: Service name (pubmed, hunter, etc.)
        endpoint: API endpoint
        status_code: Response status
        duration_ms: Call duration
    """
    logger = logging.getLogger("external_api")

    extra = {
        "service": service,
        "endpoint": endpoint,
        "status_code": status_code,
        "duration_ms": duration_ms,
    }

    level = logging.INFO if status_code < 400 else logging.WARNING

    logger.log(
        level,
        f"{service} API call: {endpoint} - {status_code} ({duration_ms:.2f}ms)",
        extra=extra,
    )


def log_background_job(job_name: str, status: str, duration_ms: Optional[float] = None) -> None:
    """
    Log background job execution

    Args:
        job_name: Job name
        status: started, completed, failed
        duration_ms: Job duration
    """
    logger = logging.getLogger("jobs")

    extra = {
        "job_name": job_name,
        "status": status,
    }

    if duration_ms is not None:
        extra["duration_ms"] = duration_ms

    if status == "failed":
        level = logging.ERROR
    else:
        level = logging.INFO

    logger.log(level, f"Job {job_name}: {status}", extra=extra)


# Initialize logging on module import
if not logging.getLogger().handlers:
    setup_logging()


# Export all
__all__ = [
    "setup_logging",
    "get_logger",
    "get_request_logger",
    "log_function_call",
    "log_async_function_call",
    "log_api_request",
    "log_database_query",
    "log_cache_operation",
    "log_external_api_call",
    "log_background_job",
    "LoggerAdapter",
]