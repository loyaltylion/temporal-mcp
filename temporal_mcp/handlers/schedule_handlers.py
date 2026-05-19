"""Handlers for schedule operations.

LoyaltyLion read-only fork: only list_schedules is exposed. The schedule
mutation handlers (create/pause/unpause/delete/trigger) have been removed.
"""

import json
import sys

from mcp.types import TextContent
from temporalio.client import Client


async def list_schedules(client: Client, args: dict) -> list[TextContent]:
    """List all schedules with skip-based pagination.

    Args:
        client: Connected Temporal client
        args: Arguments containing optional limit and skip

    Returns:
        List of schedules with pagination info
    """
    limit = args.get("limit", 100)
    skip = args.get("skip", 0)

    schedules = []
    count = 0
    total_fetched = 0

    async for schedule in await client.list_schedules():
        if count < skip:
            count += 1
            continue

        schedules.append(
            {
                "schedule_id": schedule.id,
                "paused": schedule.schedule.state.paused if schedule.schedule else False,
            }
        )
        count += 1
        total_fetched += 1

        if total_fetched >= limit:
            break

    has_more = False
    try:
        async for _ in await client.list_schedules():
            if count < skip + limit:
                count += 1
                continue
            has_more = True
            break
    except Exception as e:
        print(f"Warning: Error checking for more schedules: {e}", file=sys.stderr)

    result = {"schedules": schedules, "count": len(schedules), "skip": skip, "limit": limit}

    if has_more:
        result["has_more"] = True
        result["next_skip"] = skip + limit
        result["message"] = f"Showing {len(schedules)} schedules (skipped {skip}). More results available. Use skip={skip + limit} to get the next page."
    else:
        result["has_more"] = False
        result["message"] = f"Showing all {len(schedules)} schedules (skipped {skip}). No more results."

    return [TextContent(type="text", text=json.dumps(result, indent=2))]
