"""Tests for audit gap fixes across analytics, usage tracking, and teams."""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.team import TeamMembership
from app.models.usage import UsageEvent, UsageEventType
from app.models.user import SubscriptionTier, User


@pytest.fixture
async def auth_client(client: AsyncClient, test_user: User) -> AsyncClient:
    """Authenticated client for the shared non-superuser fixture."""
    token = create_access_token(data={"sub": str(test_user.id)})
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest_asyncio.fixture
async def second_user_client(db_session: AsyncSession):
    """Independent client for a second active user."""
    user = User(
        email=f"second-{uuid.uuid4().hex[:6]}@test.com",
        password_hash=get_password_hash("Second123!"),
        full_name="Second User",
        is_verified=True,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token(data={"sub": str(user.id)})

    async def override_db():
        yield db_session

    app.dependency_overrides[get_async_db] = override_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        ac.headers.update({"Authorization": f"Bearer {token}"})
        yield ac, user


@pytest_asyncio.fixture
async def superuser_client(db_session: AsyncSession):
    """Independent client for a superuser."""
    su = User(
        email=f"admin-fix-{uuid.uuid4().hex[:6]}@test.com",
        password_hash=get_password_hash("Admin123!"),
        full_name="Fix Admin",
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


class TestApiCallMiddleware:
    @pytest.mark.asyncio
    async def test_api_call_event_recorded_after_authenticated_request(
        self, auth_client: AsyncClient, db_session: AsyncSession, test_user: User
    ):
        response = await auth_client.get("/api/v1/users/me")
        assert response.status_code == 200

        await asyncio.sleep(0.1)

        result = await db_session.execute(
            select(UsageEvent).where(
                UsageEvent.user_id == test_user.id,
                UsageEvent.event_type == UsageEventType.API_CALL,
            )
        )
        events = result.scalars().all()
        assert events
        assert events[0].event_metadata["path"] == "/api/v1/users/me"
        assert events[0].event_metadata["method"] == "GET"

    @pytest.mark.asyncio
    async def test_health_check_not_recorded(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        before = (
            await db_session.execute(
                select(func.count(UsageEvent.id)).where(
                    UsageEvent.event_type == UsageEventType.API_CALL
                )
            )
        ).scalar_one()

        response = await client.get("/health")
        assert response.status_code == 200

        after = (
            await db_session.execute(
                select(func.count(UsageEvent.id)).where(
                    UsageEvent.event_type == UsageEventType.API_CALL
                )
            )
        ).scalar_one()
        assert after == before

    @pytest.mark.asyncio
    async def test_unauthenticated_request_not_recorded(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        before = (
            await db_session.execute(
                select(func.count(UsageEvent.id)).where(
                    UsageEvent.event_type == UsageEventType.API_CALL
                )
            )
        ).scalar_one()

        response = await client.get("/api/v1/users/me")
        assert response.status_code == 401

        await asyncio.sleep(0.05)

        after = (
            await db_session.execute(
                select(func.count(UsageEvent.id)).where(
                    UsageEvent.event_type == UsageEventType.API_CALL
                )
            )
        ).scalar_one()
        assert after == before

    @pytest.mark.asyncio
    async def test_api_call_appears_in_usage_stats(self, auth_client: AsyncClient):
        await auth_client.get("/api/v1/users/me")
        await auth_client.get("/api/v1/users/me")
        await asyncio.sleep(0.15)

        response = await auth_client.get("/api/v1/users/me/usage")
        assert response.status_code == 200
        assert response.json()["api_calls_total"] >= 2


class TestOwnerRole:
    @pytest.mark.asyncio
    async def test_team_creator_gets_owner_role(self, auth_client: AsyncClient):
        response = await auth_client.post("/api/v1/teams/", json={"name": "Owner Role Test"})
        assert response.status_code == 201
        team_id = response.json()["id"]

        members_response = await auth_client.get(f"/api/v1/teams/{team_id}/members")
        assert members_response.status_code == 200
        members = members_response.json()
        assert len(members) == 1
        assert members[0]["role"] == "owner"

    @pytest.mark.asyncio
    async def test_transfer_ownership_success(
        self,
        auth_client: AsyncClient,
        second_user_client,
        db_session: AsyncSession,
        test_user: User,
    ):
        second_ac, second_user = second_user_client

        team_response = await auth_client.post("/api/v1/teams/", json={"name": "Transfer Test"})
        assert team_response.status_code == 201
        team_id = team_response.json()["id"]

        invite_response = await auth_client.post(
            f"/api/v1/teams/{team_id}/invitations",
            json={"email": second_user.email, "role": "member"},
        )
        assert invite_response.status_code == 201
        token = invite_response.json()["token"]

        accept_response = await second_ac.get(f"/api/v1/teams/invitations/accept/{token}")
        assert accept_response.status_code == 200

        transfer_response = await auth_client.post(
            f"/api/v1/teams/{team_id}/transfer-ownership",
            json={"new_owner_user_id": str(second_user.id)},
        )
        assert transfer_response.status_code == 200

        memberships = (
            await db_session.execute(
                select(TeamMembership).where(TeamMembership.team_id == uuid.UUID(team_id))
            )
        ).scalars()
        roles = {str(membership.user_id): membership.role.value for membership in memberships}
        assert roles[str(second_user.id)] == "owner"
        assert roles[str(test_user.id)] == "admin"

    @pytest.mark.asyncio
    async def test_non_owner_cannot_transfer(
        self,
        auth_client: AsyncClient,
        second_user_client,
    ):
        second_ac, second_user = second_user_client

        team_response = await auth_client.post("/api/v1/teams/", json={"name": "No Transfer Test"})
        team_id = team_response.json()["id"]

        invite_response = await auth_client.post(
            f"/api/v1/teams/{team_id}/invitations",
            json={"email": second_user.email, "role": "member"},
        )
        token = invite_response.json()["token"]
        await second_ac.get(f"/api/v1/teams/invitations/accept/{token}")

        response = await second_ac.post(
            f"/api/v1/teams/{team_id}/transfer-ownership",
            json={"new_owner_user_id": str(second_user.id)},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_transfer_to_non_member_fails(self, auth_client: AsyncClient):
        team_response = await auth_client.post("/api/v1/teams/", json={"name": "Bad Transfer"})
        team_id = team_response.json()["id"]

        response = await auth_client.post(
            f"/api/v1/teams/{team_id}/transfer-ownership",
            json={"new_owner_user_id": str(uuid.uuid4())},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_owner_role_not_assignable_via_role_update(
        self, auth_client: AsyncClient, second_user_client
    ):
        second_ac, second_user = second_user_client

        team_response = await auth_client.post("/api/v1/teams/", json={"name": "Role Block Test"})
        team_id = team_response.json()["id"]

        invite_response = await auth_client.post(
            f"/api/v1/teams/{team_id}/invitations",
            json={"email": second_user.email, "role": "member"},
        )
        token = invite_response.json()["token"]
        await second_ac.get(f"/api/v1/teams/invitations/accept/{token}")

        response = await auth_client.patch(
            f"/api/v1/teams/{team_id}/members/{second_user.id}/role",
            json={"role": "owner"},
        )
        assert response.status_code == 422


class TestExportFrequencyAnalytics:
    @pytest_asyncio.fixture(autouse=True)
    async def seed_export_events(self, db_session: AsyncSession, test_user: User):
        now = datetime.now(timezone.utc)
        for days_ago in [1, 3, 5]:
            db_session.add(
                UsageEvent(
                    user_id=test_user.id,
                    event_type=UsageEventType.EXPORT_GENERATED,
                    quantity=50,
                    occurred_at=now - timedelta(days=days_ago),
                )
            )
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_export_frequency_endpoint_exists(self, auth_client: AsyncClient):
        response = await auth_client.get("/api/v1/analytics/me/exports")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_export_frequency_returns_correct_totals(self, auth_client: AsyncClient):
        response = await auth_client.get("/api/v1/analytics/me/exports?days=30")
        data = response.json()
        assert data["total_exports"] == 3
        assert data["total_records_exported"] == 150
        assert len(data["daily"]) == 3


class TestEngagementAnalytics:
    @pytest_asyncio.fixture(autouse=True)
    async def seed_activity(self, db_session: AsyncSession, test_user: User):
        now = datetime.now(timezone.utc)
        for days_ago in [0, 1, 2, 4, 6]:
            db_session.add(
                UsageEvent(
                    user_id=test_user.id,
                    event_type=UsageEventType.SEARCH_EXECUTED,
                    quantity=1,
                    occurred_at=now - timedelta(days=days_ago),
                )
            )
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_engagement_endpoint_exists(self, auth_client: AsyncClient):
        response = await auth_client.get("/api/v1/analytics/me/engagement")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_engagement_returns_expected_metrics(self, auth_client: AsyncClient):
        response = await auth_client.get("/api/v1/analytics/me/engagement")
        data = response.json()
        assert data["active_days_last_7"] == 5
        assert data["current_streak_days"] == 3
        assert data["longest_streak_days"] == 3
        assert data["total_events_30d"] == 5


class TestAdminDetailedUsage:
    @pytest.mark.asyncio
    async def test_admin_detailed_endpoint_exists(self, superuser_client: AsyncClient):
        response = await superuser_client.get("/api/v1/analytics/admin/detailed")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_detailed_returns_all_sections(self, superuser_client: AsyncClient):
        response = await superuser_client.get("/api/v1/analytics/admin/detailed?days=30")
        data = response.json()
        assert "event_totals" in data
        assert "daily_series" in data
        assert "source_breakdown" in data
        assert data["period_days"] == 30

    @pytest.mark.asyncio
    async def test_regular_user_gets_403_on_admin_detailed(self, auth_client: AsyncClient):
        response = await auth_client.get("/api/v1/analytics/admin/detailed")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_overview_includes_wau(self, superuser_client: AsyncClient):
        response = await superuser_client.get("/api/v1/analytics/admin/overview")
        assert response.status_code == 200
        payload = response.json()
        assert "active_week" in payload
        assert "active_today" in payload
