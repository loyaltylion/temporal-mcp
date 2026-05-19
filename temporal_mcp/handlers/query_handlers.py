"""Handlers for workflow query operations.

LoyaltyLion read-only fork: signal_workflow and continue_as_new have been
removed. Only query_workflow remains; queries are read-only by Temporal
contract.
"""

import json

from mcp.types import TextContent
from temporalio.client import Client


async def query_workflow(client: Client, args: dict) -> list[TextContent]:
    """Query a workflow execution.

    Args:
        client: Connected Temporal client
        args: Arguments containing workflow_id, query_name, and optional args

    Returns:
        Query result
    """
    workflow_id = args["workflow_id"]
    query_name = args["query_name"]
    query_args = args.get("args")

    handle = client.get_workflow_handle(workflow_id)
    result = await handle.query(query_name, query_args)

    return [TextContent(type="text", text=json.dumps({"query_result": result}, indent=2, default=str))]
