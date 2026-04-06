"""
Database configuration with IPv4 enforcement and proper connection handling
"""

from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import get_async_database_url, get_database_url, settings

# Create base class for models
Base = declarative_base()


# ============================================================================
# CONNECTION ARGS (Force IPv4 and optimize connections)
# ============================================================================

SYNC_CONNECT_ARGS = {
    "connect_timeout": 10,
    "keepalives": 1,
    "keepalives_idle": 30,
    "keepalives_interval": 10,
    "keepalives_count": 5,
    "options": "-c timezone=utc -c statement_timeout=30000",
}

ASYNC_CONNECT_ARGS = {
    "timeout": 10,
    "command_timeout": 30,
    "server_settings": {
        "application_name": "biotech_lead_generator",
        "timezone": "UTC",
    },
}


# ============================================================================
# SYNC DATABASE (for Alembic migrations)
# ============================================================================

# Get database URL with IPv4 enforcement
sync_db_url = get_database_url(force_ipv4=True)

# Create sync engine
sync_engine = create_engine(
    sync_db_url,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.DEBUG,
    connect_args=SYNC_CONNECT_ARGS,
)


# Add connection event listeners
@event.listens_for(sync_engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Set connection parameters on connect"""
    pass  # Connection args handle this


@event.listens_for(sync_engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Verify connection is alive on checkout"""
    pass  # pool_pre_ping handles this


# Create sync session factory
SyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine,
)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for getting sync database session

    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            items = db.query(Item).all()
            return items
    """
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# ASYNC DATABASE (for FastAPI async endpoints)
# ============================================================================

# Get async database URL
async_db_url = get_async_database_url()

# Create async engine
async_engine_kwargs = {
    "pool_pre_ping": True,
    "pool_recycle": 3600,
    "echo": settings.DEBUG,
    "connect_args": ASYNC_CONNECT_ARGS,
}

# Use NullPool in debug mode, QueuePool in production
if settings.DEBUG:
    async_engine_kwargs["poolclass"] = NullPool
else:
    async_engine_kwargs.update(
        {
            "pool_size": 10,
            "max_overflow": 20,
            "pool_timeout": 30,
        }
    )

async_engine = create_async_engine(async_db_url, **async_engine_kwargs)

# Session factory for use outside request context (e.g. webhooks, background tasks)
async_session_factory = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Backward-compatible alias used by startup hooks and webhook handlers.
AsyncSessionLocal = async_session_factory


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database session

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_async_db)):
            result = await db.execute(select(Item))
            items = result.scalars().all()
            return items
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================


async def init_db() -> None:
    """
    Initialize database
    Creates all tables defined in models

    NOTE: In production, use Alembic migrations instead
    """
    async with async_engine.begin() as conn:
        # Import all models here
        from app.models import export, lead, pipeline, search, user

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """
    Close database connections
    Call this on application shutdown
    """
    await async_engine.dispose()


def init_db_sync() -> None:
    """
    Synchronous database initialization
    Used by Alembic and scripts
    """
    # Import all models
    from app.models import export, lead, pipeline, search, user

    # Create all tables
    Base.metadata.create_all(bind=sync_engine)


# ============================================================================
# DATABASE UTILITIES
# ============================================================================


async def check_db_connection() -> bool:
    """
    Check if database is accessible
    Returns True if connection successful
    """
    try:
        from sqlalchemy import text

        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"❌ Async database connection failed: {e}")
        return False


def check_db_connection_sync() -> bool:
    """
    Sync version of database connection check
    """
    try:
        from sqlalchemy import text

        with SyncSessionLocal() as session:
            result = session.execute(text("SELECT 1"))
            result.fetchone()
        return True
    except Exception as e:
        print(f"❌ Sync database connection failed: {e}")
        return False


# ============================================================================
# TRANSACTION HELPERS
# ============================================================================


class DatabaseTransaction:
    """
    Context manager for database transactions

    Usage:
        async with DatabaseTransaction() as db:
            user = User(email="test@example.com")
            db.add(user)
    """

    def __init__(self):
        self.session: AsyncSession = None

    async def __aenter__(self) -> AsyncSession:
        self.session = async_session_factory()
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self.session.rollback()
        else:
            await self.session.commit()
        await self.session.close()


# ============================================================================
# PAGINATION HELPER
# ============================================================================

from typing import Generic, List, Tuple, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """
    Generic pagination response
    """

    items: List[T]
    total: int
    page: int
    size: int
    pages: int

    class Config:
        from_attributes = True


async def paginate(
    query, page: int = 1, size: int = 50, max_size: int = 100
) -> Tuple[List, int]:
    """
    Paginate a SQLAlchemy query

    Returns:
        Tuple of (items, total_count)
    """
    from sqlalchemy import func, select

    # Limit size
    size = min(size, max_size)

    # Calculate offset
    offset = (page - 1) * size

    # Get total count
    total = await query.session.scalar(
        select(func.count()).select_from(query.statement.subquery())
    )

    # Get paginated items
    query = query.offset(offset).limit(size)
    items = (await query.session.execute(query.statement)).scalars().all()

    return items, total


# Export all
__all__ = [
    "Base",
    "sync_engine",
    "async_engine",
    "SyncSessionLocal",
    "AsyncSessionLocal",
    "async_session_factory",
    "get_db",
    "get_async_db",
    "init_db",
    "close_db",
    "init_db_sync",
    "check_db_connection",
    "check_db_connection_sync",
    "DatabaseTransaction",
    "Page",
    "paginate",
]
