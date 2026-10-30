"""Shared helper for the MCP server tests.

run_mcp_test(check) does the repeated part once for every test:
start mcp_server.py over stdio, open an MCP client session, run the
initialize handshake, then hand the session to the test's own check.
The connection closes after each test, so every test starts fresh.
"""

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# mcp_server.py sits in the project root, one folder above tests/
SERVER_FILE = Path(__file__).resolve().parent.parent / "mcp_server.py"


def run_mcp_test(check):
    """Open an MCP connection, initialize it, then run a test check."""

    async def runner():
        assert SERVER_FILE.exists(), f"Missing MCP server: {SERVER_FILE}"
        params = StdioServerParameters(
            command=sys.executable,
            args=[str(SERVER_FILE)],
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                initialization = await session.initialize()
                await check(session, initialization)

    asyncio.run(runner())
