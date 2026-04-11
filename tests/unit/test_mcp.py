"""Unit tests for MCP client."""

from __future__ import annotations

import pytest

from vaultbot.mcp.client import (
    MCPClient,
    MCPResource,
    MCPServerConfig,
    MCPTool,
    MCPTransport,
)


class TestMCPTypes:
    def test_transport_enum(self) -> None:
        assert MCPTransport.STDIO.value == "stdio"
        assert MCPTransport.HTTP.value == "http"

    def test_tool_dataclass(self) -> None:
        tool = MCPTool(name="read_file", description="Read a file", server_name="fs")
        assert tool.name == "read_file"
        assert tool.input_schema == {}

    def test_resource_dataclass(self) -> None:
        res = MCPResource(uri="file:///test.txt", name="test.txt")
        assert res.uri == "file:///test.txt"
        assert res.mime_type == ""

    def test_server_config(self) -> None:
        config = MCPServerConfig(
            name="test_server",
            transport=MCPTransport.STDIO,
            command="python",
            args=["-m", "my_mcp_server"],
        )
        assert config.name == "test_server"
        assert config.transport == MCPTransport.STDIO


class TestMCPClient:
    def test_add_and_list_servers(self) -> None:
        client = MCPClient()
        config = MCPServerConfig(name="server1", transport=MCPTransport.STDIO, command="echo")
        client.add_server(config)
        assert "server1" in client.list_servers()

    def test_list_tools_empty(self) -> None:
        client = MCPClient()
        assert client.list_tools() == []

    def test_list_resources_empty(self) -> None:
        client = MCPClient()
        assert client.list_resources() == []

    def test_connected_count_initially_zero(self) -> None:
        client = MCPClient()
        assert client.connected_count == 0

    @pytest.mark.asyncio
    async def test_connect_unknown_server_raises(self) -> None:
        client = MCPClient()
        with pytest.raises(ValueError, match="Unknown MCP server"):
            await client.connect("nonexistent")

    @pytest.mark.asyncio
    async def test_call_tool_unknown_raises(self) -> None:
        client = MCPClient()
        with pytest.raises(ValueError, match="Unknown MCP tool"):
            await client.call_tool("nonexistent_tool", {})

    @pytest.mark.asyncio
    async def test_disconnect_all_empty(self) -> None:
        client = MCPClient()
        await client.disconnect_all()
        assert client.connected_count == 0

    @pytest.mark.asyncio
    async def test_disconnect_unknown_server(self) -> None:
        client = MCPClient()
        # Should not raise
        await client.disconnect("nonexistent")

    def test_tools_registered_with_server_name(self) -> None:
        client = MCPClient()
        tool = MCPTool(name="test_tool", description="test", server_name="server1")
        client._tools["test_tool"] = tool
        tools = client.list_tools()
        assert len(tools) == 1
        assert tools[0].server_name == "server1"

    @pytest.mark.asyncio
    async def test_disconnect_removes_server_tools(self) -> None:
        client = MCPClient()
        config = MCPServerConfig(name="s1", transport=MCPTransport.STDIO, command="echo")
        client.add_server(config)

        # Manually add tools as if connected
        client._tools["tool1"] = MCPTool(name="tool1", description="t1", server_name="s1")
        client._tools["tool2"] = MCPTool(name="tool2", description="t2", server_name="s2")
        client._connected_servers.add("s1")

        await client.disconnect("s1")

        assert "tool1" not in client._tools
        assert "tool2" in client._tools  # From different server
        assert client.connected_count == 0

    def test_multiple_servers(self) -> None:
        client = MCPClient()
        client.add_server(MCPServerConfig(name="a", transport=MCPTransport.STDIO, command="a"))
        client.add_server(MCPServerConfig(name="b", transport=MCPTransport.HTTP, url="http://b"))
        assert len(client.list_servers()) == 2
