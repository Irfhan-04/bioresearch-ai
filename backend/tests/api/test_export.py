"""
Export API Tests
Test export creation, download, and management
"""

import pytest
from httpx import AsyncClient

from app.models.export import Export, ExportFormat
from app.models.user import User


@pytest.mark.asyncio
@pytest.mark.api
class TestExportAPI:
    """Test export endpoints"""

    async def test_create_export_csv(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test creating CSV export"""
        response = await client.post(
            "/api/v1/export",
            json={"format": "csv", "filters": {"min_score": 70}},
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["format"] == "csv"
        assert data["status"] == "pending"

    async def test_create_export_excel(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test creating Excel export"""
        response = await client.post(
            "/api/v1/export",
            json={"format": "excel", "columns": ["name", "email", "company"]},
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["format"] == "excel"

    async def test_list_exports(self, client: AsyncClient, auth_headers: dict):
        """Test listing exports"""
        response = await client.get("/api/v1/export", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "pagination" in data

    async def test_get_export(
        self, client: AsyncClient, auth_headers: dict, test_export: Export
    ):
        """Test getting export details"""
        response = await client.get(
            f"/api/v1/export/{test_export.id}", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_export.id)

    async def test_delete_export(
        self, client: AsyncClient, auth_headers: dict, test_export: Export
    ):
        """Test deleting export"""
        response = await client.delete(
            f"/api/v1/export/{test_export.id}", headers=auth_headers
        )

        assert response.status_code == 200

    async def test_get_export_stats(self, client: AsyncClient, auth_headers: dict):
        """Test getting export statistics"""
        response = await client.get("/api/v1/export/stats/summary", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "total_exports" in data