"""Five MCP integration tests for the ShopEasy mcp_server.py.

Run from the project root:
    python -m pytest -v tests

The connection work is in mcp_helper.py; each test here only holds its own check.
No OpenAI API key is required.
"""

from mcp_helper import run_mcp_test


def test_tc01_connection():
    """The server launches and completes the MCP initialization handshake."""

    async def check(session, initialization):
        assert initialization.serverInfo.name == "ShopEasy Shipping"

    run_mcp_test(check)


def test_tc02_tool_discovery():
    """The MCP tools/list operation advertises our shipping function."""

    async def check(session, initialization):
        tools = (await session.list_tools()).tools
        assert "get_shipping_options" in {t.name for t in tools}

    run_mcp_test(check)


def test_tc03_tool_schema():
    """The advertised shipping tool takes zero required arguments."""

    async def check(session, initialization):
        tools = (await session.list_tools()).tools
        shipping = next(t for t in tools if t.name == "get_shipping_options")
        assert shipping.inputSchema["type"] == "object"
        assert shipping.inputSchema.get("required", []) == []

    run_mcp_test(check)


def test_tc04_valid_tool_call():
    """A real tools/call returns the shipping options and correct prices."""

    async def check(session, initialization):
        result = await session.call_tool("get_shipping_options", {})
        assert not result.isError, "Shipping tool reported an error"
        response_text = "\n".join(
            getattr(block, "text", "") for block in result.content
        )
        for expected in (
            "Standard", "3-5 days", "Express", "$12.99",
            "Overnight", "$24.99",
        ):
            assert expected in response_text, f"Missing: {expected}"

    run_mcp_test(check)


def test_tc05_unknown_tool_is_rejected():
    """An unknown tool must fail, not return a successful tool response.

    Depending on the MCP Python SDK release, the rejection can be
    a protocol-level exception or a tool result with isError=True.
    """

    async def check(session, initialization):
        try:
            result = await session.call_tool("not_a_real_tool", {})
        except Exception as exc:
            message = str(exc).lower()
            assert "tool" in message or "invalid request" in message, message
        else:
            assert result.isError is True, "Unknown tool unexpectedly succeeded"

    run_mcp_test(check)
