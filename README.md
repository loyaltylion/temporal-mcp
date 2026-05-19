# Temporal MCP Server — LoyaltyLion read-only fork

> **This is a fork.** Upstream is [GethosTheWalrus/temporal-mcp](https://github.com/GethosTheWalrus/temporal-mcp). This fork removes every mutating tool (start / signal / cancel / terminate / continue_as_new, the `batch_*` trio, and the schedule mutations) so AI clients can only inspect Temporal — they can't change anything. Only six tools remain: `describe_workflow`, `get_workflow_history`, `get_workflow_result`, `list_schedules`, `list_workflows`, `query_workflow`. See `temporal_mcp/tools/tool_definitions.py` and `temporal_mcp/server.py` for the trimmed surface.
>
> The PyPI / Docker Hub distributions linked below are upstream and have the full tool set — do not use them. Install from this fork (`pip install git+https://github.com/loyaltylion/temporal-mcp@<sha>`).

## Overview

This is a Model Context Protocol (MCP) server that provides tools for interacting with Temporal workflow orchestration. It enables AI assistants and other MCP clients to manage Temporal workflows, schedules, and workflow executions through a standardized interface. The server supports both local and remote Temporal instances.

Read more on the [Temporal Code Exchange](https://temporal.io/code-exchange/temporal-mcp-server)

## Distributions
- PyPI   - https://pypi.org/project/temporal-mcp-server/
- Docker - https://hub.docker.com/r/mcp/temporal

## Tools

This fork exposes six read-only tools. Every other tool from upstream has been removed at the source level.

### Workflow Inspection

- **`describe_workflow`** - Get detailed information about a workflow execution including status, timing, and metadata
- **`get_workflow_result`** - Retrieve the result of a completed workflow execution
- **`get_workflow_history`** - Retrieve the complete event history of a workflow execution
- **`list_workflows`** - List workflow executions based on a query filter with pagination support (limit/skip)
- **`query_workflow`** - Query a running workflow for its current state. Read-only by Temporal contract — queries don't append history events or fire activities, though a buggy workflow-side query handler could mutate in-memory state.

### Schedule Inspection

- **`list_schedules`** - List all schedules with pagination support (limit/skip)

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
| TLS | `--tls-enabled` | `TEMPORAL_TLS_ENABLED` | auto-detect |
| mTLS cert path | `--tls-cert` | `TEMPORAL_TLS_CLIENT_CERT_PATH` | — |
| mTLS key path | `--tls-key` | `TEMPORAL_TLS_CLIENT_KEY_PATH` | — |
| API key | `--api-key` | `TEMPORAL_API_KEY` | — |

CLI arguments take precedence over environment variables. When `TEMPORAL_API_KEY` is set, TLS is enabled automatically. When mTLS cert/key paths are provided, TLS is also enabled automatically.

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
