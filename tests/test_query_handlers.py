"""Tests for query handler tools."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from temporal_mcp.handlers import query_handlers


class TestQueryWorkflow:
    @pytest.mark.asyncio
    async def test_query_workflow_success(self, mock_client):
        mock_handle = AsyncMock()
        mock_handle.query.return_value = {"status": "running", "progress": 50}
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)

        args = {
            "workflow_id": "test-workflow-123",
            "query_name": "get_status",
            "args": {},
        }

        result = await query_handlers.query_workflow(mock_client, args)

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["query_result"]["status"] == "running"
        assert response["query_result"]["progress"] == 50
