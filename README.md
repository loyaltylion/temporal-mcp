# Temporal MCP Server — LoyaltyLion read-only fork

> **This is a fork.** Upstream is [GethosTheWalrus/temporal-mcp](https://github.com/GethosTheWalrus/temporal-mcp), merged here at `v1.10.1`. This fork removes every mutating tool (workflow start / signal / cancel / terminate / continue_as_new, standalone-activity start / execute / cancel / terminate, every `batch_*` tool, and the schedule mutations) so AI clients can only inspect Temporal — they can't change anything. Only twelve read-only tools remain: `count_activities`, `describe_activity`, `describe_schedule`, `describe_workflow`, `get_activity_result`, `get_workflow_event`, `get_workflow_history`, `get_workflow_result`, `list_activities`, `list_schedules`, `list_workflows`, `query_workflow`. See `temporal_mcp/tools/tool_definitions.py` and `temporal_mcp/server.py` for the trimmed surface, and `tests/test_read_only_surface.py`, which fails if a merge from upstream re-adds a tool.
>
> The PyPI / Docker Hub distributions linked below are upstream and have the full tool set — do not use them. Install from this fork (`pip install git+https://github.com/loyaltylion/temporal-mcp@<sha>`).

## Overview

This is a Model Context Protocol (MCP) server that provides tools for interacting with Temporal workflow orchestration. It enables AI assistants and other MCP clients to inspect Temporal workflows, schedules, and workflow executions through a standardized interface. The server supports both local and remote Temporal instances.

Read more on the [Temporal Code Exchange](https://temporal.io/code-exchange/temporal-mcp-server)

## Distributions
- PyPI   - https://pypi.org/project/temporal-mcp-server/
- Docker - https://hub.docker.com/r/mcp/temporal

## Tools

This fork exposes twelve read-only tools. Every other tool from upstream has been removed at the source level.

### Workflow Inspection

- **`describe_workflow`** - Get detailed information about a workflow execution including status, timing, and metadata
- **`get_workflow_result`** - Retrieve the result of a completed workflow execution
- **`get_workflow_history`** - Retrieve the event history of a workflow execution (optionally a specific `run_id`)
- **`get_workflow_event`** - Retrieve a single workflow history event with decoded payload fields when present
- **`list_workflows`** - List workflow executions based on a query filter with pagination support (limit/skip)
- **`query_workflow`** - Query a running workflow for its current state. Read-only by Temporal contract — queries don't append history events or fire activities, though a buggy workflow-side query handler could mutate in-memory state.

### Standalone Activity Inspection

These see only *standalone* activities (started directly by a client), not activities run by a workflow.

- **`describe_activity`** - Get detailed information about a standalone activity execution
- **`get_activity_result`** - Retrieve the result of a standalone activity execution
- **`list_activities`** - List standalone activity executions based on a query filter with pagination support (limit/skip)
- **`count_activities`** - Count standalone activity executions matching a query

### Schedule Inspection

- **`list_schedules`** - List all schedules with pagination support (limit/skip)
- **`describe_schedule`** - Get detailed configuration and runtime information about a schedule, including its spec, action, state, recent executions, and upcoming action times

## Temporal Documentation

For more information about Temporal, refer to the official Temporal documentation:

- **Temporal Documentation**: https://docs.temporal.io/
- **Workflows**: https://docs.temporal.io/workflows
- **Activities**: https://docs.temporal.io/activities
- **Python SDK**: https://docs.temporal.io/dev-guide/python

## VS Code MCP Config

Add a `.vscode/mcp.json` file to your workspace. Choose the approach that fits your setup.

### Docker (environment variables)

Recommended when running via Docker. Configuration is passed through environment variables.

```json
{
  "servers": {
    "temporal": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "TEMPORAL_HOST",
        "-e", "TEMPORAL_NAMESPACE",
        "-e", "TEMPORAL_TLS_ENABLED",
        "-e", "TEMPORAL_TLS_CLIENT_CERT_PATH",
        "-e", "TEMPORAL_TLS_CLIENT_KEY_PATH",
        "-e", "TEMPORAL_API_KEY",
        "mcp/temporal"
      ],
      "env": {
        "TEMPORAL_HOST": "localhost:7233",
        "TEMPORAL_NAMESPACE": "default",
        "TEMPORAL_TLS_ENABLED": "false",
        "TEMPORAL_TLS_CLIENT_CERT_PATH": "/path/to/client.pem",
        "TEMPORAL_TLS_CLIENT_KEY_PATH": "/path/to/client.key",
        "TEMPORAL_API_KEY": "your-api-key"
      }
    }
  }
}
```

### Python via uvx (CLI arguments)

Recommended when running from PyPI via [`uvx`](https://docs.astral.sh/uv/guides/tools/). No local install required — `uvx` fetches and runs the package automatically. Configuration is passed as CLI arguments.

```json
{
  "servers": {
    "temporal": {
      "command": "uvx",
      "args": [
        "temporal-mcp-server",
        "--host", "localhost:7233",
        "--namespace", "default",
        "--tls-enabled", "false",
        "--tls-cert", "/path/to/client.pem",
        "--tls-key", "/path/to/client.key",
        "--api-key", "your-api-key"
      ]
    }
  }
}
```

### Configuration Options

| Option | CLI Argument | Environment Variable | Default |
|--------|-------------|----------------------|---------|
| Temporal host | `--host` | `TEMPORAL_HOST` | `localhost:7233` |
| Namespace | `--namespace` | `TEMPORAL_NAMESPACE` | `default` |
| Allowed namespaces | — | `TEMPORAL_ALLOWED_NAMESPACES` | configured namespace only |
| TLS | `--tls-enabled` | `TEMPORAL_TLS_ENABLED` | auto-detect |
| mTLS cert path | `--tls-cert` | `TEMPORAL_TLS_CLIENT_CERT_PATH` | — |
| mTLS key path | `--tls-key` | `TEMPORAL_TLS_CLIENT_KEY_PATH` | — |
| API key | `--api-key` | `TEMPORAL_API_KEY` | — |

CLI arguments take precedence over environment variables. When `TEMPORAL_API_KEY` is set, TLS is enabled automatically. When mTLS cert/key paths are provided, TLS is also enabled automatically.

Every tool accepts an optional `namespace` argument. If omitted, the server uses `--namespace`, then `TEMPORAL_NAMESPACE`, then `default`. Runtime overrides are disabled by default: set `TEMPORAL_ALLOWED_NAMESPACES` to a comma-separated allowlist such as `default,payments`, or set it to `*` to permit any namespace reachable through the configured Temporal host and credentials. A finite allowlist must include the configured default namespace.

## Development

### Running Tests

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

Run the test suite:

```bash
pytest test.py -v
```

### Building the Docker Image

```bash
docker build -t mcp/temporal:latest .
```
