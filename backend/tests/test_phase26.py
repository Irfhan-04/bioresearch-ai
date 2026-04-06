"""Phase 2.6 tests for CRM, reports, collaboration, and hardening."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.lead import Lead
from app.models.user import User
from app.services.crm_service import decrypt_credentials, encrypt_credentials


@pytest.fixture
async def auth_client(client: AsyncClient, test_user: User) -> AsyncClient:
    token = create_access_token(data={"sub": str(test_user.id)})
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture
async def collab_lead(db_session: AsyncSession, test_user: User) -> Lead:
    lead = Lead(
        user_id=test_user.id,
        name="Collab Lead",
        company="BioX",
        propensity_score=80,
        priority_tier="HIGH",
        status="NEW",
    )
    db_session.add(lead)
    await db_session.commit()
    await db_session.refresh(lead)
    return lead


class TestCrmEncryption:
    def test_roundtrip(self):
        creds = {"api_key": "hsk_test_abc123"}
        assert decrypt_credentials(encrypt_credentials(creds)) == creds

    def test_tamper_raises(self):
        with pytest.raises(ValueError):
            decrypt_credentials("not_valid_ciphertext")

    def test_different_creds_differ(self):
        assert encrypt_credentials({"k": "a"}) != encrypt_credentials({"k": "b"})


class TestCrmApi:
    @pytest.mark.asyncio
    async def test_create_connection(self, auth_client: AsyncClient):
        response = await auth_client.post(
            "/api/v1/crm",
            json={
                "provider": "hubspot",
                "name": "HS Test",
                "credentials": {"api_key": "test_key"},
                "field_map": {},
            },
        )
        assert response.status_code == 201
        assert response.json()["provider"] == "hubspot"
        assert "credentials" not in response.json()
        assert "credentials_encrypted" not in response.json()

    @pytest.mark.asyncio
    async def test_list_connections(self, auth_client: AsyncClient):
        await auth_client.post(
            "/api/v1/crm",
            json={
                "provider": "pipedrive",
                "name": "PD Test",
                "credentials": {"api_token": "pd_token"},
            },
        )
        response = await auth_client.get("/api/v1/crm")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_update_connection(self, auth_client: AsyncClient):
        created = await auth_client.post(
            "/api/v1/crm",
            json={
                "provider": "hubspot",
                "name": "Old Name",
                "credentials": {"api_key": "k"},
            },
        )
        connection_id = created.json()["id"]
        response = await auth_client.patch(
            f"/api/v1/crm/{connection_id}", json={"name": "New Name"}
        )
        assert response.status_code == 200
        assert response.json()["name"] == "New Name"

    @pytest.mark.asyncio
    async def test_delete_connection(self, auth_client: AsyncClient):
        created = await auth_client.post(
            "/api/v1/crm",
            json={
                "provider": "custom",
                "name": "Del",
                "credentials": {"webhook_url": "https://x.com/wh"},
            },
        )
        connection_id = created.json()["id"]
        assert (await auth_client.delete(f"/api/v1/crm/{connection_id}")).status_code == 204
        assert (await auth_client.get(f"/api/v1/crm/{connection_id}")).status_code == 404

    @pytest.mark.asyncio
    async def test_sync_dry_run(self, auth_client: AsyncClient):
        created = await auth_client.post(
            "/api/v1/crm",
            json={
                "provider": "hubspot",
                "name": "Sync DR",
                "credentials": {"api_key": "dummy"},
                "sync_filter": {"min_score": 70},
            },
        )
        response = await auth_client.post(
            f"/api/v1/crm/{created.json()['id']}/sync",
            json={"dry_run": True},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "dry_run"


class TestCollaboration:
    @pytest.mark.asyncio
    async def test_add_note(self, auth_client: AsyncClient, collab_lead: Lead):
        response = await auth_client.post(
            f"/api/v1/collaboration/leads/{collab_lead.id}/activities",
            json={"activity_type": "note", "content": "Test note."},
        )
        assert response.status_code == 201
        assert response.json()["activity_type"] == "note"

    @pytest.mark.asyncio
    async def test_comment_with_mention(
        self, auth_client: AsyncClient, collab_lead: Lead, test_user: User
    ):
        response = await auth_client.post(
            f"/api/v1/collaboration/leads/{collab_lead.id}/activities",
            json={
                "activity_type": "comment",
                "content": f"@{test_user.id} please follow up.",
            },
        )
        assert response.status_code == 201
        mentions = response.json().get("mentioned_user_ids") or []
        assert str(test_user.id) in [str(item) for item in mentions]

    @pytest.mark.asyncio
    async def test_add_reminder(self, auth_client: AsyncClient, collab_lead: Lead):
        due = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        response = await auth_client.post(
            f"/api/v1/collaboration/leads/{collab_lead.id}/activities",
            json={
                "activity_type": "reminder",
                "content": "Check in",
                "reminder_due_at": due,
            },
        )
        assert response.status_code == 201
        assert response.json()["reminder_due_at"] is not None

    @pytest.mark.asyncio
    async def test_reminder_without_due_at_fails(
        self, auth_client: AsyncClient, collab_lead: Lead
    ):
        response = await auth_client.post(
            f"/api/v1/collaboration/leads/{collab_lead.id}/activities",
            json={"activity_type": "reminder", "content": "Missing due"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_activity_feed(self, auth_client: AsyncClient, collab_lead: Lead):
        await auth_client.post(
            f"/api/v1/collaboration/leads/{collab_lead.id}/activities",
            json={"activity_type": "note", "content": "Feed test"},
        )
        response = await auth_client.get(
            f"/api/v1/collaboration/leads/{collab_lead.id}/activities"
        )
        assert response.status_code == 200
        assert len(response.json()) >= 1

    @pytest.mark.asyncio
    async def test_status_change(self, auth_client: AsyncClient, collab_lead: Lead):
        response = await auth_client.post(
            f"/api/v1/collaboration/leads/{collab_lead.id}/status",
            json={"new_status": "CONTACTED"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_invalid_status_rejected(
        self, auth_client: AsyncClient, collab_lead: Lead
    ):
        response = await auth_client.post(
            f"/api/v1/collaboration/leads/{collab_lead.id}/status",
            json={"new_status": "INVALID"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_reminders(self, auth_client: AsyncClient, collab_lead: Lead):
        due = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        await auth_client.post(
            f"/api/v1/collaboration/leads/{collab_lead.id}/activities",
            json={
                "activity_type": "reminder",
                "content": "Check grant",
                "reminder_due_at": due,
            },
        )
        response = await auth_client.get(
            "/api/v1/collaboration/reminders?due_within_days=7"
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestReports:
    @pytest.mark.asyncio
    async def test_funnel(self, auth_client: AsyncClient):
        response = await auth_client.get("/api/v1/reports/funnel")
        assert response.status_code == 200
        assert len(response.json()["stages"]) == 7

    @pytest.mark.asyncio
    async def test_conversion(self, auth_client: AsyncClient):
        response = await auth_client.get("/api/v1/reports/conversion")
        assert response.status_code == 200
        assert "overall_win_rate" in response.json()

    @pytest.mark.asyncio
    async def test_roi(self, auth_client: AsyncClient):
        response = await auth_client.get(
            "/api/v1/reports/roi?avg_deal_value=75000&win_rate_pct=20"
        )
        assert response.status_code == 200
        assert "total_pipeline_value" in response.json()

    @pytest.mark.asyncio
    async def test_cohort(self, auth_client: AsyncClient):
        response = await auth_client.get("/api/v1/reports/cohort?weeks=4")
        assert response.status_code == 200
        assert len(response.json()["cohorts"]) == 4

    @pytest.mark.asyncio
    async def test_custom_lead_count(self, auth_client: AsyncClient):
        response = await auth_client.post(
            "/api/v1/reports/custom",
            json={"metric": "lead_count", "group_by": "week", "days": 30},
        )
        assert response.status_code == 200
        assert "data" in response.json()

    @pytest.mark.asyncio
    async def test_custom_invalid_metric(self, auth_client: AsyncClient):
        response = await auth_client.post(
            "/api/v1/reports/custom",
            json={"metric": "bad_metric", "group_by": "day", "days": 7},
        )
        assert response.status_code == 422


class TestSecurityHeaders:
    @pytest.mark.asyncio
    async def test_security_headers_present(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.headers.get("x-content-type-options") == "nosniff"
        assert response.headers.get("x-frame-options") == "DENY"

    @pytest.mark.asyncio
    async def test_process_time_header(self, client: AsyncClient):
        response = await client.get("/health")
        assert "x-process-time" in response.headers


class TestRateLimiter:
    def test_instantiates_correctly(self):
        from app.utils.rate_limiter import RateLimiter

        limiter = RateLimiter(requests=60, window_seconds=60)
        assert limiter.requests == 60

    def test_predefined_limiters(self):
        from app.utils.rate_limiter import (
            enrich_limiter,
            export_limiter,
            leads_limiter,
            search_limiter,
        )

        assert search_limiter.requests == 60
        assert enrich_limiter.requests == 30
        assert leads_limiter.requests == 120
        assert export_limiter.requests == 10
