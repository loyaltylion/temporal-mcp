"""LoyaltyLion fork: tests for the HTTP transports in temporal_mcp/http_app.py.

These run a real uvicorn server on a free local port with no Temporal behind
it. Tool calls that reach the dispatcher get a stub client, so nothing tries to
connect.
"""

import json
import signal
import socket
import sys
import threading
import time
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import httpx2 as httpx
import pytest
import uvicorn
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamable_http_client
from sse_starlette.sse import AppStatus

from temporal_mcp.http_app import create_app
from temporal_mcp.server import TemporalMCPServer
from tests.test_read_only_surface import ALLOWED_TOOLS


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@contextmanager
def _serving(mcp_server: TemporalMCPServer, graceful_shutdown_seconds: int | None = None):
    port = _free_port()
    # log_config=None leaves uvicorn's loggers propagating, so caplog sees them.
    config = uvicorn.Config(create_app(mcp_server), host="127.0.0.1", port=port, log_config=None, timeout_graceful_shutdown=graceful_shutdown_seconds)
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started:
        if time.monotonic() > deadline:
            raise RuntimeError("uvicorn did not start")
        time.sleep(0.05)
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        # Stop the way SIGTERM does. sse-starlette patches handle_exit to close
        # open SSE streams; setting should_exit directly would skip that.
        server.handle_exit(signal.SIGTERM, None)
        thread.join(timeout=15)
        # The flag sse-starlette sets is process-global; clear it so streams
        # opened by later tests aren't closed at once.
        AppStatus.should_exit = False


@pytest.fixture
def mcp_server():
    server = TemporalMCPServer(temporal_host="127.0.0.1:1", namespace="main")
    server.client_manager.get_client = AsyncMock(return_value=object())
    server.client_manager.disconnect = AsyncMock()
    return server


async def _exercise(session: ClientSession) -> None:
    await session.initialize()
    tools = (await session.list_tools()).tools
    assert {tool.name for tool in tools} == ALLOWED_TOOLS

    result = await session.call_tool("terminate_workflow", {"workflow_id": "order-1"})
    assert json.loads(result.content[0].text)["type"] == "unknown_tool"


@pytest.mark.asyncio
async def test_streamable_http_lists_only_allowed_tools(mcp_server):
    with _serving(mcp_server) as base_url:
        async with streamable_http_client(f"{base_url}/mcp") as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await _exercise(session)


@pytest.mark.asyncio
async def test_sse_lists_only_allowed_tools(mcp_server):
    with _serving(mcp_server) as base_url:
        async with sse_client(f"{base_url}/sse") as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await _exercise(session)


@pytest.mark.asyncio
async def test_streamable_http_answers_without_a_session(mcp_server):
    # Stateless: a client holding no session (or a stale one) still gets an
    # answer instead of having its request dropped.
    with _serving(mcp_server) as base_url:
        response = httpx.post(
            f"{base_url}/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            headers={"Accept": "application/json, text/event-stream", "Mcp-Session-Id": "stale-session"},
        )

    assert response.status_code == 200
    assert "mcp-session-id" not in response.headers
    payload = next(line.removeprefix("data:").strip() for line in response.text.splitlines() if line.startswith("data:"))
    assert {tool["name"] for tool in json.loads(payload)["result"]["tools"]} == ALLOWED_TOOLS


def test_any_host_header_is_accepted_and_root_is_404(mcp_server):
    # A load balancer probes the root with the task's IP as the Host header.
    with _serving(mcp_server) as base_url:
        response = httpx.get(f"{base_url}/", headers={"Host": "10.0.0.1:3000"})

    assert response.status_code == 404


def test_shutdown_disconnects_the_temporal_client(mcp_server):
    with _serving(mcp_server):
        pass

    mcp_server.client_manager.disconnect.assert_awaited_once()


@pytest.mark.parametrize(
    "argv, env, expected",
    [
        ([], {}, None),
        (["--transport", "http"], {}, ("127.0.0.1", 3000)),
        (["--transport", "http", "--http-host", "0.0.0.0", "--http-port", "8080"], {}, ("0.0.0.0", 8080)),
        ([], {"MCP_TRANSPORT": "http", "MCP_HTTP_HOST": "0.0.0.0", "MCP_HTTP_PORT": "3001"}, ("0.0.0.0", 3001)),
        (["--transport", "stdio"], {"MCP_TRANSPORT": "http"}, None),
    ],
)
def test_main_selects_transport(argv, env, expected):
    with (
        patch.object(sys, "argv", ["temporal-mcp-server"] + argv),
        patch.dict("os.environ", env, clear=True),
        patch("temporal_mcp.__main__.TemporalMCPServer") as server_class,
        patch("temporal_mcp.__main__.asyncio.run") as run_stdio,
        patch("temporal_mcp.http_app.run_http") as run_http,
    ):
        from temporal_mcp.__main__ import main

        main()

    if expected is None:
        run_stdio.assert_called_once()
        run_http.assert_not_called()
    else:
        run_stdio.assert_not_called()
        run_http.assert_called_once_with(server_class.return_value, *expected)


def test_main_rejects_unknown_transport_from_env():
    with (
        patch.object(sys, "argv", ["temporal-mcp-server"]),
        patch.dict("os.environ", {"MCP_TRANSPORT": "websocket"}, clear=True),
        patch("temporal_mcp.__main__.TemporalMCPServer"),
        pytest.raises(SystemExit),
    ):
        from temporal_mcp.__main__ import main

        main()


def test_sse_rejects_post(mcp_server):
    with _serving(mcp_server) as base_url:
        response = httpx.post(f"{base_url}/sse")

    assert response.status_code == 405


def test_shutdown_with_an_open_sse_stream_logs_no_error(mcp_server, caplog):
    # The SSE transport sends the whole response itself; anything sent after it
    # makes uvicorn log "Exception in ASGI application" when shutdown cuts the
    # stream.
    opened = threading.Event()

    def hold_stream(base_url):
        try:
            with httpx.stream("GET", f"{base_url}/sse", timeout=30) as response:
                for _ in response.iter_lines():
                    opened.set()
        except httpx.HTTPError:
            pass

    with caplog.at_level("ERROR"):
        with _serving(mcp_server, graceful_shutdown_seconds=1) as base_url:
            threading.Thread(target=hold_stream, args=(base_url,), daemon=True).start()
            assert opened.wait(timeout=10)

    assert not [record for record in caplog.records if record.levelname == "ERROR"]


def test_client_closing_an_sse_stream_logs_no_error(mcp_server, caplog):
    with caplog.at_level("ERROR"):
        with _serving(mcp_server) as base_url:
            with httpx.stream("GET", f"{base_url}/sse", timeout=10) as response:
                assert next(response.iter_lines()).startswith("event: endpoint")
            time.sleep(0.5)

    assert not [record for record in caplog.records if record.levelname == "ERROR"]
