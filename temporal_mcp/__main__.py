"""Entry point for Temporal MCP Server.

Supports:
  - `python -m temporal_mcp`
  - `temporal-mcp-server` CLI (installed via pip)

Serves stdio by default. `--transport http` (LoyaltyLion fork) serves
Streamable HTTP and SSE instead; see temporal_mcp/http_app.py.

Configuration priority (highest → lowest):
  1. CLI arguments
  2. Environment variables
  3. Built-in defaults
"""

import argparse
import asyncio
import os
import sys

from temporal_mcp.server import TemporalMCPServer

DEFAULT_HTTP_HOST = "127.0.0.1"
DEFAULT_HTTP_PORT = 3000


def _parse_args() -> argparse.Namespace:
    """Parse optional CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="temporal-mcp-server",
        description="MCP server for Temporal workflow orchestration.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--host",
        metavar="HOST:PORT",
        default=None,
        help="Temporal server host and port (env: TEMPORAL_HOST, default: localhost:7233)",
    )
    parser.add_argument(
        "--namespace",
        metavar="NAMESPACE",
        default=None,
        help="Temporal namespace (env: TEMPORAL_NAMESPACE, default: default)",
    )
    parser.add_argument(
        "--tls-enabled",
        metavar="BOOL",
        default=None,
        choices=["true", "false"],
        type=str.lower,
        help="Force-enable or force-disable TLS; omit to auto-detect (env: TEMPORAL_TLS_ENABLED)",
    )
    parser.add_argument(
        "--tls-cert",
        metavar="PATH",
        default=None,
        help="Path to mTLS client certificate file (env: TEMPORAL_TLS_CLIENT_CERT_PATH)",
    )
    parser.add_argument(
        "--tls-key",
        metavar="PATH",
        default=None,
        help="Path to mTLS client private key file (env: TEMPORAL_TLS_CLIENT_KEY_PATH)",
    )
    parser.add_argument(
        "--api-key",
        metavar="KEY",
        default=None,
        help="API key for Temporal Cloud authentication (env: TEMPORAL_API_KEY)",
    )
    parser.add_argument(
        "--transport",
        default=None,
        choices=["stdio", "http"],
        type=str.lower,
        help="MCP transport to serve (env: MCP_TRANSPORT, default: stdio)",
    )
    parser.add_argument(
        "--http-host",
        metavar="HOST",
        default=None,
        help=f"Address to listen on with --transport http (env: MCP_HTTP_HOST, default: {DEFAULT_HTTP_HOST})",
    )
    parser.add_argument(
        "--http-port",
        metavar="PORT",
        default=None,
        type=int,
        help=f"Port to listen on with --transport http (env: MCP_HTTP_PORT, default: {DEFAULT_HTTP_PORT})",
    )
    return parser.parse_args()


def main():
    """Main entry point for the MCP server."""
    args = _parse_args()

    # CLI arg → env var → built-in default
    temporal_host = args.host or os.environ.get("TEMPORAL_HOST", "localhost:7233")
    namespace = args.namespace or os.environ.get("TEMPORAL_NAMESPACE", "default")

    # Parse TLS setting: None (auto-detect), True (force enable), False (force disable)
    tls_raw = args.tls_enabled or os.environ.get("TEMPORAL_TLS_ENABLED", "").lower()
    if tls_raw == "true":
        tls_enabled = True
    elif tls_raw == "false":
        tls_enabled = False
    else:
        tls_enabled = None  # Auto-detect

    # mTLS client certificate paths (for Temporal Cloud)
    tls_client_cert_path = args.tls_cert or os.environ.get("TEMPORAL_TLS_CLIENT_CERT_PATH")
    tls_client_key_path = args.tls_key or os.environ.get("TEMPORAL_TLS_CLIENT_KEY_PATH")

    # API key authentication (for Temporal Cloud)
    api_key = args.api_key or os.environ.get("TEMPORAL_API_KEY")
    allowed_namespaces_raw = os.environ.get("TEMPORAL_ALLOWED_NAMESPACES")
    allowed_namespaces = allowed_namespaces_raw.split(",") if allowed_namespaces_raw is not None else None

    transport = args.transport or os.environ.get("MCP_TRANSPORT", "stdio").lower()
    if transport not in ("stdio", "http"):
        sys.exit(f"MCP_TRANSPORT must be 'stdio' or 'http', got {transport!r}")
    http_host = args.http_host or os.environ.get("MCP_HTTP_HOST", DEFAULT_HTTP_HOST)
    http_port = args.http_port if args.http_port is not None else int(os.environ.get("MCP_HTTP_PORT", DEFAULT_HTTP_PORT))

    print(
        f"Starting MCP server with TEMPORAL_HOST={temporal_host}, TLS={tls_enabled}",
        file=sys.stderr,
    )
    if tls_client_cert_path:
        print(f"mTLS client cert: {tls_client_cert_path}", file=sys.stderr)
    if tls_client_key_path:
        print(f"mTLS client key:  {tls_client_key_path}", file=sys.stderr)
    if api_key:
        print("API key authentication: enabled", file=sys.stderr)

    server = TemporalMCPServer(
        temporal_host=temporal_host,
        namespace=namespace,
        tls_enabled=tls_enabled,
        tls_client_cert_path=tls_client_cert_path,
        tls_client_key_path=tls_client_key_path,
        api_key=api_key,
        allowed_namespaces=allowed_namespaces,
    )
    if transport == "http":
        from temporal_mcp.http_app import run_http

        run_http(server, http_host, http_port)
    else:
        asyncio.run(server.run())


if __name__ == "__main__":
    main()
