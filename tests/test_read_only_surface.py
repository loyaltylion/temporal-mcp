"""LoyaltyLion read-only fork: pin the exposed tool surface.

This fork exists so that MCP clients can only read from Temporal, and it
enforces that by not having the write tools at all. These tests fail if a
merge from upstream re-adds a tool or a dispatcher branch, so the surface can
only grow by editing ALLOWED_TOOLS deliberately.
"""

import inspect
import json
import re
from unittest.mock import AsyncMock

import pytest

from temporal_mcp import server as server_module
from temporal_mcp.server import TemporalMCPServer
from temporal_mcp.tools.tool_definitions import get_all_tools

ALLOWED_TOOLS = {
    "count_activities",
    "describe_activity",
    "describe_schedule",
    "describe_workflow",
    "get_activity_result",
    "get_workflow_event",
    "get_workflow_history",
    "get_workflow_result",
    "list_activities",
    "list_schedules",
    "list_workflows",
    "query_workflow",
}

REMOVED_TOOLS = [
    "start_workflow",
    "signal_workflow",
    "cancel_workflow",
    "terminate_workflow",
    "continue_as_new",
    "start_activity",
    "execute_activity",
    "cancel_activity",
    "terminate_activity",
    "batch_signal",
    "batch_cancel",
    "batch_terminate",
    "batch_cancel_activities",
    "batch_terminate_activities",
    "create_schedule",
    "pause_schedule",
    "unpause_schedule",
    "delete_schedule",
    "trigger_schedule",
]


def test_tool_definitions_are_exactly_the_allowed_set():
    assert {tool.name for tool in get_all_tools()} == ALLOWED_TOOLS


def test_dispatcher_branches_are_exactly_the_allowed_set():
    source = inspect.getsource(TemporalMCPServer._execute_tool)
    assert set(re.findall(r'name == "([a-z_]+)"', source)) == ALLOWED_TOOLS


@pytest.mark.asyncio
async def test_listed_tools_are_exactly_the_allowed_set():
    server = TemporalMCPServer(namespace="production")
    result = await server._list_tools(None, None)
    assert {tool.name for tool in result.tools} == ALLOWED_TOOLS


@pytest.mark.asyncio
@pytest.mark.parametrize("name", REMOVED_TOOLS)
async def test_removed_tools_are_unknown(name):
    server = TemporalMCPServer(namespace="production")
    server.client_manager.get_client = AsyncMock(return_value=object())

    result = await server._execute_tool(name, {})

    assert json.loads(result[0].text)["type"] == "unknown_tool"


def test_no_batch_handler_module():
    assert "batch_handlers" not in vars(server_module)


def test_activity_handlers_have_no_write_functions():
    from temporal_mcp.handlers import activity_handlers

    for name in ["start_activity", "execute_activity", "cancel_activity", "terminate_activity"]:
        assert not hasattr(activity_handlers, name)
