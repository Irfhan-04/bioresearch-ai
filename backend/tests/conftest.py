"""
Test Fixtures and Configuration
Shared test utilities for all test modules
"""

import os
os.environ.setdefault("ENV_FILE", ".env.test")

import asyncio
from datetime import datetime, timedelta
from typing import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import Base, get_async_db
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.export import Export, ExportFormat, ExportStatus
from app.models.lead import Lead
from app.models.pipeline import Pipeline, PipelineSchedule, PipelineStatus
from app.models.search import Search
from app.models.user import SubscriptionTier, User

# ============================================================================
# DATABASE FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine"""
    # Use test database URL from environment-driven settings
    test_db_url = settings.DATABASE_URL.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(test_db_url, poolclass=NullPool, echo=False)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session"""
    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database override"""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_async_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ============================================================================
# USER FIXTURES
# ============================================================================


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create test user"""
    user = User(
        email="test@example.com",
        password_hash=get_password_hash("TestPass123!"),
        full_name="Test User",
        subscription_tier=SubscriptionTier.FREE,
        is_active=True,
        is_verified=True,
        is_superuser=False,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest.fixture
async def pro_user(db_session: AsyncSession) -> User:
    """Create pro tier user"""
    user = User(
        email="pro@example.com",
        password_hash=get_password_hash("ProPass123!"),
        full_name="Pro User",
        subscription_tier=SubscriptionTier.PRO,
        is_active=True,
        is_verified=True,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create admin user"""
    user = User(
        email="admin@example.com",
        password_hash=get_password_hash("AdminPass123!"),
        full_name="Admin User",
        subscription_tier=SubscriptionTier.ENTERPRISE,
        is_active=True,
        is_verified=True,
        is_superuser=True,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest.fixture
def test_token(test_user: User) -> str:
    """Create JWT token for test user"""
    return create_access_token(data={"sub": str(test_user.id)})


@pytest.fixture
def auth_headers(test_token: str) -> dict:
    """Create authorization headers"""
    return {"Authorization": f"Bearer {test_token}"}


# ============================================================================
# LEAD FIXTURES
# ============================================================================


@pytest.fixture
async def test_lead(db_session: AsyncSession, test_user: User) -> Lead:
    """Create test lead"""
    lead = Lead(
        user_id=test_user.id,
        name="Dr. John Smith",
        title="Principal Scientist",
        company="BioTech Inc",
        location="Cambridge, MA",
        email="john.smith@biotech.com",
        propensity_score=85,
        priority_tier="HIGH",
        recent_publication=True,
        publication_year=2024,
        publication_title="Novel DILI Models",
        status="NEW",
    )

    db_session.add(lead)
    await db_session.commit()
    await db_session.refresh(lead)

    return lead


@pytest.fixture
async def test_leads(db_session: AsyncSession, test_user: User) -> list[Lead]:
    """Create multiple test leads"""
    leads = []

    for i in range(10):
        lead = Lead(
            user_id=test_user.id,
            name=f"Dr. Test {i}",
            title="Researcher",
            company=f"Company {i}",
            location="Boston, MA",
            propensity_score=70 + i,
            priority_tier="MEDIUM" if i < 5 else "HIGH",
            status="NEW",
        )
        leads.append(lead)
        db_session.add(lead)

    await db_session.commit()

    for lead in leads:
        await db_session.refresh(lead)

    return leads


# ============================================================================
# SEARCH FIXTURES
# ============================================================================


@pytest.fixture
async def test_search(db_session: AsyncSession, test_user: User) -> Search:
    """Create test search"""
    search = Search(
        user_id=test_user.id,
        query="DILI 3D models",
        search_type="pubmed",
        results_count=10,
        is_saved=False,
        execution_time_ms=1500,
    )

    db_session.add(search)
    await db_session.commit()
    await db_session.refresh(search)

    return search


# ============================================================================
# EXPORT FIXTURES
# ============================================================================


@pytest.fixture
async def test_export(db_session: AsyncSession, test_user: User) -> Export:
    """Create test export"""
    export = Export(
        user_id=test_user.id,
        file_name="test_export.csv",
        format=ExportFormat.CSV,
        status=ExportStatus.PENDING,
        records_count=0,
    )

    db_session.add(export)
    await db_session.commit()
    await db_session.refresh(export)

    return export


# ============================================================================
# PIPELINE FIXTURES
# ============================================================================


@pytest.fixture
async def test_pipeline(db_session: AsyncSession, test_user: User) -> Pipeline:
    """Create test pipeline"""
    pipeline = Pipeline(
        user_id=test_user.id,
        name="Test Pipeline",
        description="Test pipeline for unit tests",
        schedule=PipelineSchedule.MANUAL,
        config={"search_queries": [{"source": "pubmed", "query": "test query"}]},
        status=PipelineStatus.ACTIVE,
    )

    db_session.add(pipeline)
    await db_session.commit()
    await db_session.refresh(pipeline)

    return pipeline


# ============================================================================
# MOCK DATA FIXTURES
# ============================================================================


@pytest.fixture
def mock_pubmed_results():
    """Mock PubMed search results"""
    return [
        {
            "name": "Dr. Sarah Johnson",
            "title": "Principal Investigator",
            "company": "Harvard Medical School",
            "location": "Boston, MA",
            "recent_publication": True,
            "publication_year": 2024,
            "publication_title": "Advanced DILI Models",
        },
        {
            "name": "Dr. Michael Chen",
            "title": "Research Scientist",
            "company": "MIT",
            "location": "Cambridge, MA",
            "recent_publication": True,
            "publication_year": 2023,
            "publication_title": "3D Hepatic Organoids",
        },
    ]


@pytest.fixture
def mock_enrichment_data():
    """Mock enrichment data"""
    return {
        "email": {"email": "test@example.com", "confidence": 0.9, "source": "hunter"},
        "company": {
            "name": "BioTech Inc",
            "domain": "biotech.com",
            "size": "51-200",
            "funding": "Series B",
        },
    }


# ============================================================================
# UTILITY FIXTURES
# ============================================================================


@pytest.fixture
def faker():
    """Faker instance for generating test data"""
    from faker import Faker

    return Faker()


@pytest.fixture
def freeze_time():
    """Freeze time for consistent testing"""
    return datetime(2024, 1, 15, 12, 0, 0)


# ============================================================================
# STRIPE MOCK FIXTURES (Week 2 - Fix 1.3)
# ============================================================================


@pytest.fixture(autouse=True)
def mock_stripe(monkeypatch):
    """Mock all Stripe API calls in tests — never hit real Stripe."""
    import unittest.mock as mock

    monkeypatch.setattr("stripe.Customer.create", mock.MagicMock(return_value={"id": "cus_test"}))
    monkeypatch.setattr("stripe.checkout.Session.create", mock.MagicMock(return_value={"id": "cs_test", "url": "https://checkout.stripe.com/test"}))
    monkeypatch.setattr("stripe.billing_portal.Session.create", mock.MagicMock(return_value={"url": "https://billing.stripe.com/test"}))
    monkeypatch.setattr("stripe.Subscription.retrieve", mock.MagicMock(return_value={
        "id": "sub_test",
        "status": "active",
        "customer": "cus_test",
        "current_period_end": 9999999999,
        "items": {"data": [{"price": {"id": "price_pro_placeholder"}}]},
    }))
    monkeypatch.setattr("stripe.Webhook.construct_event", mock.MagicMock(return_value={
        "type": "checkout.session.completed",
        "id": "evt_test",
        "data": {"object": {"customer": "cus_test", "subscription": "sub_test", "metadata": {"user_id": "00000000-0000-0000-0000-000000000000"}}},
    }))
