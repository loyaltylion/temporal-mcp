"""Main MCP Server for Temporal workflow orchestration.

LoyaltyLion read-only fork: only inspection tools are dispatched. Write
tools have been removed from the source — this dispatcher only references
the read handlers.
"""

import json
from typing import Any, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .client import TemporalClientManager
from .tools.tool_definitions import get_all_tools
from .utils.exceptions import format_connection_error, format_error_response

from .handlers import workflow_handlers
from .handlers import query_handlers
from .handlers import schedule_handlers


class TemporalMCPServer:
    """MCP Server that provides tools for interacting with Temporal."""

    def __init__(
        self,
        temporal_host: str = "localhost:7233",
        namespace: str = "default",
        tls_enabled: Optional[bool] = None,
        tls_client_cert_path: Optional[str] = None,
        tls_client_key_path: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """Initialize the Temporal MCP server.

        Args:
            temporal_host: The Temporal server host and port
            namespace: The Temporal namespace to use
            tls_enabled: Whether to use TLS for connection (None = auto-detect, True = force enable, False = force disable)
            tls_client_cert_path: Path to the TLS client certificate file (for mTLS / Temporal Cloud)
            tls_client_key_path: Path to the TLS client private key file (for mTLS / Temporal Cloud)
            api_key: API key for Temporal Cloud authentication
        """
        self.client_manager = TemporalClientManager(
            temporal_host=temporal_host,
            namespace=namespace,
            tls_enabled=tls_enabled,
            tls_client_cert_path=tls_client_cert_path,
            tls_client_key_path=tls_client_key_path,
            api_key=api_key,
        )
        self.server = Server("temporal-mcp-server")
        self._setup_handlers()

    def _setup_handlers(self):
        """Set up MCP request handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available Temporal tools."""
            return get_all_tools()

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent]:
            """Handle tool execution requests."""
            try:
                await self.client_manager.connect()
            except Exception as e:
                return format_connection_error(e)

            try:
                client = self.client_manager.ensure_connected()

                if name == "describe_workflow":
                    return await workflow_handlers.describe_workflow(client, arguments)
                elif name == "get_workflow_history":
                    return await workflow_handlers.get_workflow_history(client, arguments)
                elif name == "get_workflow_result":
                    return await workflow_handlers.get_workflow_result(client, arguments)
                elif name == "list_workflows":
                    return await workflow_handlers.list_workflows(client, arguments)
                elif name == "query_workflow":
                    return await query_handlers.query_workflow(client, arguments)
                elif name == "list_schedules":
                    return await schedule_handlers.list_schedules(client, arguments)

                else:
                    return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}", "type": "unknown_tool"}, indent=2))]

            except Exception as e:
                return format_error_response(e, name)

    async def run(self):
        """Run the MCP server."""
        try:
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(read_stream, write_stream, self.server.create_initialization_options())
        finally:
            await self.client_manager.disconnect()
