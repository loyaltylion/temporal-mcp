"""HTTP transports for the MCP server.

LoyaltyLion fork: upstream speaks stdio only. This module serves the same
server over HTTP from a single process, so it can sit behind a load balancer
without a stdio bridge in front of it:

- ``/mcp``: Streamable HTTP, stateless. Each request is answered on its own,
  so there is no server-side session for a client to hold after it goes stale.
- ``/sse`` with ``/messages/``: the legacy SSE transport, for clients
  configured with ``type: sse``.

Every connection shares the one ``TemporalMCPServer`` and therefore its one
lazily-created Temporal client, which is closed when the app shuts down.

No transport security settings are passed, so the MCP SDK does not check the
Host or Origin header. That check guards against DNS rebinding, and a
deployment behind a load balancer that routes on the host header gets the same
protection from the routing rule. Bind to 127.0.0.1 (the default) anywhere
that isn't true.
"""

import contextlib
import sys
from collections.abc import AsyncIterator

import uvicorn
from mcp.server.sse import SseServerTransport
from mcp.server.streamable_http_manager import StreamableHTTPASGIApp, StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.types import Message, Receive, Scope, Send

from .server import TemporalMCPServer

STREAMABLE_HTTP_PATH = "/mcp"
SSE_PATH = "/sse"
SSE_MESSAGES_PATH = "/messages/"

# Long-lived SSE streams would otherwise hold shutdown open until the
# orchestrator kills the process; close them after this many seconds.
GRACEFUL_SHUTDOWN_SECONDS = 10


class _SseEndpoint:
    """Raw ASGI endpoint for the SSE stream.

    The SSE transport sends the HTTP response itself, but when the server shuts
    down with a stream still open, sse-starlette ends the stream without the
    final empty body chunk and uvicorn logs an error. This endpoint finishes
    that response and nothing else. A Starlette request/response endpoint
    (the MCP SDK's documented pattern) would start a second response instead,
    which uvicorn rejects with a traceback.
    """

    def __init__(self, mcp_server: TemporalMCPServer, sse: SseServerTransport):
        self._server = mcp_server.server
        self._sse = sse

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        started = False
        completed = False

        async def tracking_send(message: Message) -> None:
            nonlocal started, completed
            if message["type"] == "http.response.start":
                started = True
            elif message["type"] == "http.response.body" and not message.get("more_body", False):
                completed = True
            await send(message)

        async with self._sse.connect_sse(scope, receive, tracking_send) as (read_stream, write_stream):
            await self._server.run(read_stream, write_stream, self._server.create_initialization_options())

        if started and not completed:
            await send({"type": "http.response.body", "body": b"", "more_body": False})


def create_app(mcp_server: TemporalMCPServer) -> Starlette:
    """Build the ASGI app that serves ``mcp_server`` over Streamable HTTP and SSE."""
    session_manager = StreamableHTTPSessionManager(app=mcp_server.server, stateless=True)
    sse = SseServerTransport(SSE_MESSAGES_PATH)

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        async with session_manager.run():
            try:
                yield
            finally:
                await mcp_server.client_manager.disconnect()

    return Starlette(
        routes=[
            Route(STREAMABLE_HTTP_PATH, endpoint=StreamableHTTPASGIApp(session_manager)),
            Route(SSE_PATH, endpoint=_SseEndpoint(mcp_server, sse), methods=["GET"]),
            Mount(SSE_MESSAGES_PATH, app=sse.handle_post_message),
        ],
        lifespan=lifespan,
    )


def run_http(mcp_server: TemporalMCPServer, host: str, port: int) -> None:
    """Serve ``mcp_server`` over HTTP until interrupted."""
    print(
        f"Serving MCP over HTTP on {host}:{port}: Streamable HTTP at {STREAMABLE_HTTP_PATH}, SSE at {SSE_PATH}",
        file=sys.stderr,
    )
    uvicorn.run(create_app(mcp_server), host=host, port=port, timeout_graceful_shutdown=GRACEFUL_SHUTDOWN_SECONDS)
