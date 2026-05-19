"""Tool definitions for the Temporal MCP server.

LoyaltyLion read-only fork: only inspection tools are exposed.
Write tools (start/signal/cancel/terminate/continue_as_new, the batch_*
trio, and the schedule mutations) have been removed from this fork. See
fork README for rationale.
"""

from mcp.types import Tool


def get_all_tools() -> list[Tool]:
    """Get all available Temporal tools.

    Returns:
        List of Tool definitions
    """
    return [
        Tool(
            name="describe_workflow",
            description="Get detailed information about a workflow execution",
            inputSchema={"type": "object", "properties": {"workflow_id": {"type": "string", "description": "The workflow execution ID to describe"}}, "required": ["workflow_id"]},
        ),
        Tool(
            name="get_workflow_history",
            description="Get the complete event history of a workflow execution. Specify 'limit' to control the number of events (default: 1000).",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string", "description": "The workflow execution ID"},
                    "limit": {"type": "number", "description": "Maximum number of history events to return (default: 1000)"},
                },
                "required": ["workflow_id"],
            },
        ),
        Tool(
            name="get_workflow_result",
            description="Get the result of a completed workflow",
            inputSchema={"type": "object", "properties": {"workflow_id": {"type": "string", "description": "The workflow execution ID"}}, "required": ["workflow_id"]},
        ),
        Tool(
            name="list_schedules",
            description="List all schedules. Specify 'limit' to control the number of results (default: 100). Use 'skip' to paginate through results.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "number", "description": "Maximum number of schedules to return (default: 100)"},
                    "skip": {"type": "number", "description": "Number of results to skip for pagination (default: 0)"},
                },
            },
        ),
        Tool(
            name="list_workflows",
            description="List workflow executions based on a query. Specify 'limit' to control the number of results (default: 100, max recommended: 1000). Use 'skip' to paginate through results.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "List filter query (e.g., 'WorkflowType=\"MyWorkflow\"')"},
                    "limit": {"type": "number", "description": "Maximum number of results to return (default: 100, increase for more results)"},
                    "skip": {"type": "number", "description": "Number of results to skip for pagination (default: 0)"},
                },
            },
        ),
        Tool(
            name="query_workflow",
            description="Query a running workflow for its current state",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string", "description": "The workflow execution ID to query"},
                    "query_name": {"type": "string", "description": "The name of the query to execute"},
                    "args": {"type": "object", "description": "Arguments for the query (as JSON object)"},
                },
                "required": ["workflow_id", "query_name"],
            },
        ),
    ]
