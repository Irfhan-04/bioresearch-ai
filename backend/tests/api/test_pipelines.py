"""
Pipeline API Tests
Test pipeline creation, execution, and management
"""

import pytest
from httpx import AsyncClient

from app.models.pipeline import Pipeline
from app.models.user import User


@pytest.mark.asyncio
@pytest.mark.api
class TestPipelineAPI:
    """Test pipeline endpoints"""

    async def test_create_pipeline(self, client: AsyncClient, auth_headers: dict):
        """Test creating pipeline"""
        pipeline_data = {
            "name": "Test Pipeline",
            "description": "Test pipeline description",
            "schedule": "manual",
            "config": {
                "search_queries": [{"source": "pubmed", "query": "test query"}],
                "filters": {"min_score": 70},
            },
        }

        response = await client.post(
            "/api/v1/pipelines", json=pipeline_data, headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Pipeline"
        assert data["status"] == "active"

    async def test_list_pipelines(self, client: AsyncClient, auth_headers: dict):
        """Test listing pipelines"""
        response = await client.get("/api/v1/pipelines", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "pagination" in data

    async def test_get_pipeline(
        self, client: AsyncClient, auth_headers: dict, test_pipeline: Pipeline
    ):
        """Test getting pipeline details"""
        response = await client.get(
            f"/api/v1/pipelines/{test_pipeline.id}", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_pipeline.id)

    async def test_update_pipeline(
        self, client: AsyncClient, auth_headers: dict, test_pipeline: Pipeline
    ):
        """Test updating pipeline"""
        response = await client.put(
            f"/api/v1/pipelines/{test_pipeline.id}",
            json={"name": "Updated Pipeline"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Pipeline"

    async def test_run_pipeline(
        self, client: AsyncClient, auth_headers: dict, test_pipeline: Pipeline
    ):
        """Test manually running pipeline"""
        response = await client.post(
            f"/api/v1/pipelines/{test_pipeline.id}/run", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data["data"]

    async def test_activate_pipeline(
        self, client: AsyncClient, auth_headers: dict, test_pipeline: Pipeline
    ):
        """Test activating pipeline"""
        response = await client.post(
            f"/api/v1/pipelines/{test_pipeline.id}/activate", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"

    async def test_pause_pipeline(
        self, client: AsyncClient, auth_headers: dict, test_pipeline: Pipeline
    ):
        """Test pausing pipeline"""
        response = await client.post(
            f"/api/v1/pipelines/{test_pipeline.id}/pause", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "paused"

    async def test_delete_pipeline(
        self, client: AsyncClient, auth_headers: dict, test_pipeline: Pipeline
    ):
        """Test deleting pipeline"""
        response = await client.delete(
            f"/api/v1/pipelines/{test_pipeline.id}", headers=auth_headers
        )

        assert response.status_code == 200

    async def test_get_pipeline_stats(self, client: AsyncClient, auth_headers: dict):
        """Test getting pipeline statistics"""
        response = await client.get(
            "/api/v1/pipelines/stats/summary", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_pipelines" in data