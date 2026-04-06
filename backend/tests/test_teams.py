"""
Phase 2.4 — Team, quota, and admin endpoint tests.
Focuses on:
- Team creation and invitation flow
- Usage stats endpoint
- Quota enforcement for free tier
- Access control for admin endpoints
All tests use the AsyncClient with mocked authentication — no real HTTP requests in CI.              
"""

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.usage import UsageEvent, UsageEventType
from app.models.user import SubscriptionTier, User


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
async def auth_client(client: AsyncClient, test_user: User) -> AsyncClient:
    """Primary test user — reuses the shared `client` fixture (safe)."""
    token = create_access_token(data={"sub": str(test_user.id)})
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture
async def regular_client(auth_client: AsyncClient) -> AsyncClient:
    """Alias for auth_client — non-superuser."""
    return auth_client


@pytest_asyncio.fixture
async def alt_client(db_session: AsyncSession):
    """
    Second user with its own independent AsyncClient.

    Does NOT reuse the `client` fixture — that would overwrite auth_client's
    Authorization header because pytest gives both fixtures the same object
    when client is function-scoped.
    """
    alt_user = User(
        email="alt@example.com",
        password_hash=get_password_hash("AltPass123!"),
        full_name="Alt User",
        is_verified=True,
        is_active=True,
    )
    db_session.add(alt_user)
    await db_session.commit()
    await db_session.refresh(alt_user)

    token = create_access_token(data={"sub": str(alt_user.id)})

    async def override_db():
        yield db_session

    app.dependency_overrides[get_async_db] = override_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        ac.headers.update({"Authorization": f"Bearer {token}"})
        yield ac

    # Do NOT call app.dependency_overrides.clear() here —
    # conftest.client's teardown owns that responsibility.


@pytest_asyncio.fixture
async def superuser_client(db_session: AsyncSession):
    """
    Superuser with its own independent AsyncClient.

    Same isolation rationale as alt_client — must not reuse the `client` fixture.
    """
    su = User(
        email=f"super-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=get_password_hash("SuperPass123!"),
        full_name="Super Admin",
        is_superuser=True,
        is_verified=True,
        is_active=True,
        subscription_tier=SubscriptionTier.ENTERPRISE,
    )
    db_session.add(su)
    await db_session.commit()
    await db_session.refresh(su)

    token = create_access_token(data={"sub": str(su.id)})

    async def override_db():
        yield db_session

    app.dependency_overrides[get_async_db] = override_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        ac.headers.update({"Authorization": f"Bearer {token}"})
        yield ac


# ============================================================================
# TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_create_team(auth_client: AsyncClient):
    response = await auth_client.post("/api/v1/teams/", json={"name": "Test Team"})
    assert response.status_code == 201
    data = response.json()
    assert data["slug"] == "test-team"
    assert data["member_count"] == 1


@pytest.mark.asyncio
async def test_usage_stats(auth_client: AsyncClient):
    response = await auth_client.get("/api/v1/users/me/usage")
    assert response.status_code == 200
    payload = response.json()
    assert "leads_created" in payload
    assert "quota_pct_used" in payload


@pytest.mark.asyncio
async def test_invite_and_accept(auth_client: AsyncClient, alt_client: AsyncClient):
    # 1. Primary user creates a team
    team_resp = await auth_client.post("/api/v1/teams/", json={"name": "Invite Test Team"})
    assert team_resp.status_code == 201
    team_id = team_resp.json()["id"]

    # 2. Primary user invites alt user by email
    invite_resp = await auth_client.post(
        f"/api/v1/teams/{team_id}/invitations",
        json={"email": "alt@example.com", "role": "member"},
    )
    assert invite_resp.status_code == 201
    token = invite_resp.json()["token"]
    assert token

    # 3. Alt user accepts the invite
    accept_resp = await alt_client.get(f"/api/v1/teams/invitations/accept/{token}")
    assert accept_resp.status_code == 200
    assert "joined" in accept_resp.json()["message"].lower()

    # 4. Alt user should now appear in the member list
    members_resp = await auth_client.get(f"/api/v1/teams/{team_id}/members")
    assert members_resp.status_code == 200
    emails = [member["email"] for member in members_resp.json()]
    assert "alt@example.com" in emails


@pytest.mark.asyncio
async def test_quota_enforcement(auth_client: AsyncClient, db_session: AsyncSession):
    """Free tier: 100 leads succeed; the 101st must return 429 with quota_exceeded."""
    me_resp = await auth_client.get("/api/v1/users/me")
    assert me_resp.status_code == 200
    user_id = uuid.UUID(me_resp.json()["id"])

    # Seed 100 LEAD_CREATED events directly — faster than 100 API calls
    for _ in range(100):
        db_session.add(
            UsageEvent(
                user_id=user_id,
                event_type=UsageEventType.LEAD_CREATED,
                quantity=1,
            )
        )
    await db_session.commit()

    # 101st lead must be rejected
    response = await auth_client.post(
        "/api/v1/leads/",
        json={"name": "Lead 101", "title": "Scientist", "company": "AcmeBio"},
    )
    assert response.status_code == 429

    detail = response.json()["detail"]
    assert detail["error"] == "quota_exceeded"
    assert detail["metric"] == "leads"
    assert detail["limit"] == 100
    assert "upgrade" in detail
    assert detail["tier"] == "free"


@pytest.mark.asyncio
async def test_admin_only_endpoints_return_403_for_regular_user(
    regular_client: AsyncClient,
):
    """Non-superuser must receive 403 on every admin and analytics-admin endpoint."""
    restricted_paths = [
        "/api/v1/admin/users",
        "/api/v1/admin/flags",
        "/api/v1/admin/tickets",
        "/api/v1/admin/health/system",
        "/api/v1/analytics/admin/overview",
    ]
    for path in restricted_paths:
        response = await regular_client.get(path)
        assert response.status_code == 403, (
            f"Expected 403 on {path}, got {response.status_code}"
        )


@pytest.mark.asyncio
async def test_admin_endpoints_accessible_to_superuser(
    superuser_client: AsyncClient,
):
    """Superuser must reach all admin endpoints with 200."""
    paths = [
        "/api/v1/admin/users",
        "/api/v1/admin/flags",
        "/api/v1/admin/tickets",
        "/api/v1/admin/health/system",
        "/api/v1/analytics/admin/overview",
    ]
    for path in paths:
        response = await superuser_client.get(path)
        assert response.status_code == 200, (
            f"Expected 200 on {path} for superuser, got {response.status_code}"
        )