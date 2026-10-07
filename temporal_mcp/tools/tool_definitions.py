"""Tool definitions for the Temporal MCP server."""

from typing import Iterable, Optional

from mcp.types import Tool


def get_all_tools(allowed_namespaces: Optional[Iterable[str]] = None) -> list[Tool]:
    """Get all available Temporal tools.

    LoyaltyLion read-only fork: only inspection tools are defined. Every tool
    that starts, signals, cancels, terminates, or mutates a schedule has been
    removed from the source, not filtered at runtime.

    Returns:
        List of Tool definitions
    """
    tools = [
        Tool(
            name="query_workflow",
            description="Query a running workflow for its current state",
            input_schema={
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string", "description": "The workflow execution ID to query"},
                    "query_name": {"type": "string", "description": "The name of the query to execute"},
                    "args": {"type": "object", "description": "Arguments for the query (as JSON object)"},
                },
                "required": ["workflow_id", "query_name"],
            },
        ),
        Tool(
            name="get_workflow_result",
            description="Get the result of a completed workflow",
            input_schema={"type": "object", "properties": {"workflow_id": {"type": "string", "description": "The workflow execution ID"}}, "required": ["workflow_id"]},
        ),
        Tool(
            name="describe_workflow",
            description="Get detailed information about a workflow execution",
            input_schema={"type": "object", "properties": {"workflow_id": {"type": "string", "description": "The workflow execution ID to describe"}}, "required": ["workflow_id"]},
        ),
        Tool(
            name="list_workflows",
            description="List workflow executions based on a query. Specify 'limit' to control the number of results (default: 100, max recommended: 1000). Use 'skip' to paginate through results.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "List filter query (e.g., 'WorkflowType=\"MyWorkflow\"')"},
                    "limit": {"type": "number", "description": "Maximum number of results to return (default: 100, increase for more results)"},
                    "skip": {"type": "number", "description": "Number of results to skip for pagination (default: 0)"},
                },
            },
        ),
        Tool(
            name="get_workflow_history",
            description="Get the complete event history of a workflow execution. Specify 'limit' to control the number of events (default: 1000).",
            input_schema={
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string", "description": "The workflow execution ID"},
                    "run_id": {"type": "string", "description": "Optional run ID for the workflow execution; omit to target the latest run"},
                    "limit": {"type": "number", "description": "Maximum number of history events to return (default: 1000)"},
                },
                "required": ["workflow_id"],
            },
        ),
        Tool(
            name="get_workflow_event",
            description="Get a single workflow history event with decoded payload fields when present",
            input_schema={
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string", "description": "The workflow execution ID"},
                    "event_id": {"type": "number", "description": "The history event ID to fetch"},
                    "run_id": {"type": "string", "description": "Optional run ID for the workflow execution"},
                },
                "required": ["workflow_id", "event_id"],
            },
        ),
        Tool(
            name="get_activity_result",
            description="Get the result of a standalone activity",
            input_schema={
                "type": "object",
                "properties": {
                    "activity_id": {"type": "string", "description": "Standalone activity execution ID"},
                    "run_id": {"type": "string", "description": "Run ID for the standalone activity execution"},
                    "timeout": {"type": "number", "description": "Optional timeout in seconds while waiting for result"},
                },
                "required": ["activity_id"],
            },
        ),
        Tool(
            name="describe_activity",
            description="Get detailed information about a standalone activity execution",
            input_schema={
                "type": "object",
                "properties": {
                    "activity_id": {"type": "string", "description": "Standalone activity execution ID"},
                    "run_id": {"type": "string", "description": "Run ID for the standalone activity execution"},
                },
                "required": ["activity_id"],
            },
        ),
        Tool(
            name="list_activities",
            description="List standalone activity executions based on a query. Specify 'limit' to control results and 'skip' for pagination.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "List filter query (e.g., 'TaskQueue = \"my-task-queue\"')"},
                    "limit": {"type": "number", "description": "Maximum number of results to return (default: 100)"},
                    "skip": {"type": "number", "description": "Number of results to skip for pagination (default: 0)"},
                },
            },
        ),
        Tool(
            name="count_activities",
            description="Count standalone activity executions matching a query",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "List filter query (e.g., 'TaskQueue = \"my-task-queue\"')"},
                },
            },
        ),
        Tool(
            name="list_schedules",
            description="List all schedules. Specify 'limit' to control the number of results (default: 100). Use 'skip' to paginate through results.",
            input_schema={
                "type": "object",
                "properties": {
                    "limit": {"type": "number", "description": "Maximum number of schedules to return (default: 100)"},
                    "skip": {"type": "number", "description": "Number of results to skip for pagination (default: 0)"},
                },
            },
        ),
        Tool(
            name="describe_schedule",
            description="Get detailed configuration and runtime information about a schedule, including its spec, action, state, recent executions, and upcoming action times",
            input_schema={"type": "object", "properties": {"schedule_id": {"type": "string", "description": "The schedule ID to describe"}}, "required": ["schedule_id"]},
        ),
    ]

    namespace_schema = {
        "type": "string",
        "minLength": 1,
        "description": "Temporal namespace for this operation; omit to use the server default",
    }
    if allowed_namespaces is not None:
        namespace_schema["enum"] = sorted(allowed_namespaces)
    for tool in tools:
        input_schema = tool.input_schema
        input_schema["properties"]["namespace"] = namespace_schema.copy()

    return tools
