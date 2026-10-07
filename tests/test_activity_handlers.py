"""Tests for standalone activity handler tools."""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from temporal_mcp.handlers import activity_handlers


class TestGetActivityResult:
    @pytest.mark.asyncio
    async def test_get_activity_result_success(self, mock_client):
        mock_handle = AsyncMock()
        mock_handle.result.return_value = "done"
        mock_client.get_activity_handle = MagicMock(return_value=mock_handle)

        result = await activity_handlers.get_activity_result(mock_client, {"activity_id": "test-activity-123"})
        response = json.loads(result[0].text)
        assert response["result"] == "done"


class TestDescribeActivity:
    @pytest.mark.asyncio
    async def test_describe_activity_success(self, mock_client):
        mock_description = MagicMock()
        mock_description.activity_id = "test-activity-123"
        mock_description.run_id = "run-456"
        mock_description.activity_type = "compose_greeting"
        mock_description.task_queue = "activity-queue"
        mock_description.status = 2
        mock_description.attempt = 1
        mock_description.start_time = datetime(2026, 1, 1, 0, 0, 0)
        mock_description.close_time = datetime(2026, 1, 1, 0, 0, 1)

        mock_handle = AsyncMock()
        mock_handle.describe.return_value = mock_description
        mock_client.get_activity_handle = MagicMock(return_value=mock_handle)

        result = await activity_handlers.describe_activity(mock_client, {"activity_id": "test-activity-123"})

        response = json.loads(result[0].text)
        assert response["activity_id"] == "test-activity-123"
        assert response["activity_type"] == "compose_greeting"
        assert response["status"] == "ACTIVITY_EXECUTION_STATUS_COMPLETED"


class TestListActivities:
    @pytest.mark.asyncio
    async def test_list_activities_success(self, mock_client):
        mock_a1 = MagicMock()
        mock_a1.activity_id = "a1"
        mock_a1.run_id = "r1"
        mock_a1.activity_type = "compose_greeting"
        mock_a1.task_queue = "activity-queue"
        mock_a1.status = 1
        mock_a1.start_time = datetime(2026, 1, 1, 0, 0, 0)

        async def mock_list_activities(*, query):
            assert query == ""
            yield mock_a1

        mock_client.list_activities = mock_list_activities

        result = await activity_handlers.list_activities(mock_client, {"limit": 10})
        response = json.loads(result[0].text)
        assert response["count"] == 1
        assert response["activities"][0]["activity_id"] == "a1"


class TestCountActivities:
    @pytest.mark.asyncio
    async def test_count_activities_success(self, mock_client):
        mock_response = MagicMock()
        mock_response.count = 3
        mock_group = MagicMock()
        mock_group.group_values = ["compose_greeting"]
        mock_group.count = 3
        mock_response.groups = [mock_group]
        mock_client.count_activities.return_value = mock_response

        result = await activity_handlers.count_activities(mock_client, {"query": "ActivityType = 'compose_greeting'"})
        response = json.loads(result[0].text)
        assert response["count"] == 3
        assert response["groups"][0]["count"] == 3
