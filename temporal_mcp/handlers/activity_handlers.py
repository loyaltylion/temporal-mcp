"""Handlers for standalone activity operations.

LoyaltyLion read-only fork: only get_activity_result, describe_activity,
list_activities and count_activities are exposed. The write handlers
(start_activity, execute_activity, cancel_activity, terminate_activity) and
the batch activity handlers have been removed.
"""

import asyncio
import json
from typing import Any, cast

from mcp.types import TextContent
from temporalio.api.enums.v1 import ActivityExecutionStatus
from temporalio.client import Client


def _status_name(status: object) -> str:
    if status is None:
        return "UNKNOWN"

    if isinstance(status, int):
        return ActivityExecutionStatus.Name(cast(Any, status))

    try:
        return ActivityExecutionStatus.Name(cast(Any, int(str(status))))
    except Exception:
        return str(status)


async def get_activity_result(client: Client, args: dict) -> list[TextContent]:
    """Fetch result for an existing standalone activity."""
    activity_id = args["activity_id"]
    run_id = args.get("run_id")
    timeout = args.get("timeout")

    handle = client.get_activity_handle(activity_id=activity_id, run_id=run_id)

    try:
        if timeout:
            result = await asyncio.wait_for(handle.result(), timeout=timeout)
        else:
            result = await handle.result()
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "activity_id": activity_id,
                        "run_id": run_id,
                        "result": result,
                    },
                    indent=2,
                    default=str,
                ),
            )
        ]
    except asyncio.TimeoutError:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": f"Timeout waiting for activity result after {timeout} seconds",
                        "type": "timeout",
                        "activity_id": activity_id,
                    },
                    indent=2,
                ),
            )
        ]


async def describe_activity(client: Client, args: dict) -> list[TextContent]:
    """Describe an existing standalone activity."""
    activity_id = args["activity_id"]
    run_id = args.get("run_id")

    handle = client.get_activity_handle(activity_id=activity_id, run_id=run_id)
    description = await handle.describe()

    result = {
        "activity_id": getattr(description, "activity_id", activity_id),
        "run_id": getattr(description, "run_id", run_id),
        "activity_type": getattr(description, "activity_type", None),
        "task_queue": getattr(description, "task_queue", None),
        "status": _status_name(getattr(description, "status", None)),
        "status_code": getattr(description, "status", None),
        "attempt": getattr(description, "attempt", None),
        "start_time": str(getattr(description, "start_time", None)),
        "close_time": str(getattr(description, "close_time", None)) if getattr(description, "close_time", None) else None,
    }
    return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]


async def list_activities(client: Client, args: dict) -> list[TextContent]:
    """List standalone activity executions with skip-based pagination."""
    query = args.get("query", "")
    limit = args.get("limit", 100)
    skip = args.get("skip", 0)

    activities = []
    count = 0
    total_fetched = 0

    async for activity in client.list_activities(query=query):
        if count < skip:
            count += 1
            continue

        activities.append(
            {
                "activity_id": getattr(activity, "activity_id", None),
                "run_id": getattr(activity, "run_id", None),
                "activity_type": getattr(activity, "activity_type", None),
                "task_queue": getattr(activity, "task_queue", None),
                "status": _status_name(getattr(activity, "status", None)),
                "status_code": getattr(activity, "status", None),
                "start_time": str(getattr(activity, "start_time", None)),
            }
        )
        count += 1
        total_fetched += 1

        if total_fetched >= limit:
            break

    has_more = False
    async for _ in client.list_activities(query=query):
        if count < skip + limit:
            count += 1
            continue
        has_more = True
        break

    result = {
        "activities": activities,
        "count": len(activities),
        "skip": skip,
        "limit": limit,
        "has_more": has_more,
    }
    if has_more:
        result["next_skip"] = skip + limit
        result["message"] = f"Showing {len(activities)} activities (skipped {skip}). More results available. Use skip={skip + limit} to get the next page."
    else:
        result["message"] = f"Showing all {len(activities)} activities (skipped {skip}). No more results."

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def count_activities(client: Client, args: dict) -> list[TextContent]:
    """Count standalone activities matching a query."""
    query = args.get("query", "")
    response = await client.count_activities(query=query)

    groups = []
    for group in getattr(response, "groups", []):
        groups.append(
            {
                "group_values": list(getattr(group, "group_values", [])),
                "count": getattr(group, "count", 0),
            }
        )

    result = {
        "query": query,
        "count": getattr(response, "count", 0),
        "groups": groups,
    }
    return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
