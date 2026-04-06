"""
Leads API Tests
Test lead creation, retrieval, update, deletion, and bulk operations
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead
from app.models.user import User

# ============================================================================
# CREATE LEAD TESTS
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.api
class TestCreateLead:
    """Test lead creation endpoint"""

    async def test_create_valid_lead(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test creating a valid lead"""
        lead_data = {
            "name": "Dr. Jane Smith",
            "title": "Research Scientist",
            "company": "BioTech Corp",
            "location": "San Francisco, CA",
            "email": "jane.smith@biotech.com",
            "recent_publication": True,
            "publication_year": 2024,
            "tags": ["high-priority", "researcher"],
        }

        response = await client.post(
            "/api/v1/leads", json=lead_data, headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == lead_data["name"]
        assert data["email"] == lead_data["email"]
        assert "id" in data
        assert "created_at" in data

    async def test_create_lead_unauthenticated(self, client: AsyncClient):
        """Test creating lead without authentication"""
        lead_data = {"name": "Test Lead", "title": "Scientist"}

        response = await client.post("/api/v1/leads", json=lead_data)

        assert response.status_code == 401

    async def test_create_duplicate_email(
        self, client: AsyncClient, auth_headers: dict, test_lead: Lead
    ):
        """Test creating lead with duplicate email"""
        lead_data = {
            "name": "Different Name",
            "title": "Scientist",
            "email": test_lead.email,
        }

        response = await client.post(
            "/api/v1/leads", json=lead_data, headers=auth_headers
        )

        assert response.status_code == 400
        data = response.json()
        assert "already exists" in data["detail"].lower()

    async def test_create_lead_missing_required_fields(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test creating lead without required fields"""
        lead_data = {
            "title": "Scientist"
            # Missing 'name' field
        }

        response = await client.post(
            "/api/v1/leads", json=lead_data, headers=auth_headers
        )

        assert response.status_code == 422


# ============================================================================
# LIST LEADS TESTS
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.api
class TestListLeads:
    """Test lead listing endpoint"""

    async def test_list_leads(
        self, client: AsyncClient, auth_headers: dict, test_leads: list[Lead]
    ):
        """Test listing leads with pagination"""
        response = await client.get("/api/v1/leads?page=1&size=5", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "pagination" in data
        assert len(data["items"]) == 5
        assert data["pagination"]["total"] == 10

    async def test_list_leads_with_filters(
        self, client: AsyncClient, auth_headers: dict, test_leads: list[Lead]
    ):
        """Test filtering leads"""
        response = await client.get(
            "/api/v1/leads?min_score=75&priority_tier=HIGH", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all returned leads meet filter criteria
        for item in data["items"]:
            assert item["propensity_score"] >= 75
            assert item["priority_tier"] == "HIGH"

    async def test_list_leads_with_search(
        self, client: AsyncClient, auth_headers: dict, test_leads: list[Lead]
    ):
        """Test searching leads by name/company"""
        response = await client.get("/api/v1/leads?search=Test", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) > 0

    async def test_list_leads_sorted(
        self, client: AsyncClient, auth_headers: dict, test_leads: list[Lead]
    ):
        """Test sorting leads"""
        response = await client.get(
            "/api/v1/leads?sort_by=propensity_score&sort_order=desc",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify descending order
        scores = [item["propensity_score"] for item in data["items"]]
        assert scores == sorted(scores, reverse=True)


# ============================================================================
# GET LEAD TESTS
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.api
class TestGetLead:
    """Test get single lead endpoint"""

    async def test_get_existing_lead(
        self, client: AsyncClient, auth_headers: dict, test_lead: Lead
    ):
        """Test retrieving existing lead"""
        response = await client.get(
            f"/api/v1/leads/{test_lead.id}", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_lead.id)
        assert data["name"] == test_lead.name
        assert data["email"] == test_lead.email

    async def test_get_nonexistent_lead(self, client: AsyncClient, auth_headers: dict):
        """Test retrieving non-existent lead"""
        import uuid

        response = await client.get(
            f"/api/v1/leads/{uuid.uuid4()}", headers=auth_headers
        )

        assert response.status_code == 404

    async def test_get_other_users_lead(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_lead: Lead,
        pro_user: User,
        db_session: AsyncSession,
    ):
        """Test accessing another user's lead"""
        # Create lead for different user
        other_lead = Lead(
            user_id=pro_user.id, name="Other User Lead", title="Scientist", status="NEW"
        )
        db_session.add(other_lead)
        await db_session.commit()
        await db_session.refresh(other_lead)

        response = await client.get(
            f"/api/v1/leads/{other_lead.id}", headers=auth_headers
        )

        assert response.status_code == 404  # Should not find


# ============================================================================
# UPDATE LEAD TESTS
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.api
class TestUpdateLead:
    """Test lead update endpoint"""

    async def test_update_lead(
        self, client: AsyncClient, auth_headers: dict, test_lead: Lead
    ):
        """Test updating lead"""
        update_data = {
            "title": "Senior Research Scientist",
            "tags": ["updated", "high-priority"],
        }

        response = await client.put(
            f"/api/v1/leads/{test_lead.id}", json=update_data, headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == update_data["title"]
        assert set(data["tags"]) == set(update_data["tags"])

    async def test_update_nonexistent_lead(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test updating non-existent lead"""
        import uuid

        response = await client.put(
            f"/api/v1/leads/{uuid.uuid4()}",
            json={"title": "New Title"},
            headers=auth_headers,
        )

        assert response.status_code == 404


# ============================================================================
# DELETE LEAD TESTS
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.api
class TestDeleteLead:
    """Test lead deletion endpoint"""

    async def test_delete_lead(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_lead: Lead,
        db_session: AsyncSession,
    ):
        """Test deleting lead"""
        lead_id = test_lead.id

        response = await client.delete(f"/api/v1/leads/{lead_id}", headers=auth_headers)

        assert response.status_code == 200

        # Verify lead deleted from database
        from sqlalchemy import select

        result = await db_session.execute(select(Lead).where(Lead.id == lead_id))
        assert result.scalar_one_or_none() is None

    async def test_delete_nonexistent_lead(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test deleting non-existent lead"""
        import uuid

        response = await client.delete(
            f"/api/v1/leads/{uuid.uuid4()}", headers=auth_headers
        )

        assert response.status_code == 404


# ============================================================================
# BULK OPERATIONS TESTS
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.api
class TestBulkLeadOperations:
    """Test bulk lead operations"""

    async def test_bulk_create_leads(self, client: AsyncClient, auth_headers: dict):
        """Test creating multiple leads at once"""
        leads_data = {
            "leads": [
                {
                    "name": f"Bulk Lead {i}",
                    "title": "Researcher",
                    "company": f"Company {i}",
                    "email": f"bulk{i}@example.com",
                }
                for i in range(5)
            ],
            "skip_duplicates": True,
        }

        response = await client.post(
            "/api/v1/leads/bulk/create", json=leads_data, headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 5
        assert data["failure_count"] == 0

    async def test_bulk_delete_leads(
        self, client: AsyncClient, auth_headers: dict, test_leads: list[Lead]
    ):
        """Test deleting multiple leads"""
        lead_ids = [str(lead.id) for lead in test_leads[:3]]

        response = await client.post(
            "/api/v1/leads/bulk/delete", json={"ids": lead_ids}, headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 3
