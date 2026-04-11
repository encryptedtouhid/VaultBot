"""MCP client for connecting to Model Context Protocol servers.

Supports both stdio and HTTP/SSE transports.  Discovers tools and
resources from MCP servers and registers them as VaultBot tools.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class MCPTransport(str, Enum):
    """MCP transport types."""

    STDIO = "stdio"
    HTTP = "http"


@dataclass(frozen=True, slots=True)
class MCPTool:
    """A tool discovered from an MCP server."""

    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    server_name: str = ""


@dataclass(frozen=True, slots=True)
class MCPResource:
    """A resource available from an MCP server."""

    uri: str
    name: str
    description: str = ""
    mime_type: str = ""


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server connection."""

    name: str
    transport: MCPTransport
    command: str = ""  # For stdio: command to run
    args: list[str] = field(default_factory=list)
    url: str = ""  # For HTTP: server URL
    env: dict[str, str] = field(default_factory=dict)


class MCPClient:
    """Client for connecting to MCP servers.

    Manages connections to one or more MCP servers, discovers their
    tools and resources, and provides a unified interface for calling
    them.
    """

    def __init__(self) -> None:
        self._servers: dict[str, MCPServerConfig] = {}
        self._tools: dict[str, MCPTool] = {}
        self._resources: dict[str, MCPResource] = {}
        self._processes: dict[str, asyncio.subprocess.Process] = {}
        self._connected_servers: set[str] = set()

    def add_server(self, config: MCPServerConfig) -> None:
        """Register an MCP server configuration."""
        self._servers[config.name] = config
        logger.info("mcp_server_added", name=config.name, transport=config.transport.value)

    def list_servers(self) -> list[str]:
        """Return names of all configured MCP servers."""
        return list(self._servers.keys())

    def list_tools(self) -> list[MCPTool]:
        """Return all discovered tools across all servers."""
        return list(self._tools.values())

    def list_resources(self) -> list[MCPResource]:
        """Return all discovered resources."""
        return list(self._resources.values())

    async def connect(self, server_name: str) -> None:
        """Connect to an MCP server and discover its tools/resources."""
        config = self._servers.get(server_name)
        if not config:
            raise ValueError(f"Unknown MCP server: {server_name}")

        if config.transport == MCPTransport.STDIO:
            await self._connect_stdio(config)
        elif config.transport == MCPTransport.HTTP:
            await self._connect_http(config)

        self._connected_servers.add(server_name)
        logger.info(
            "mcp_server_connected",
            name=server_name,
            tools=len([t for t in self._tools.values() if t.server_name == server_name]),
        )

    async def disconnect(self, server_name: str) -> None:
        """Disconnect from an MCP server."""
        if server_name in self._processes:
            proc = self._processes.pop(server_name)
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except TimeoutError:
                proc.kill()

        # Remove tools from this server
        self._tools = {k: v for k, v in self._tools.items() if v.server_name != server_name}
        self._connected_servers.discard(server_name)
        logger.info("mcp_server_disconnected", name=server_name)

    async def disconnect_all(self) -> None:
        """Disconnect from all MCP servers."""
        for name in list(self._connected_servers):
            await self.disconnect(name)

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Call a tool on its MCP server."""
        tool = self._tools.get(tool_name)
        if not tool:
            available = ", ".join(self._tools.keys()) or "none"
            raise ValueError(f"Unknown MCP tool '{tool_name}'. Available: {available}")

        config = self._servers.get(tool.server_name)
        if not config:
            raise RuntimeError(f"Server '{tool.server_name}' not configured")

        logger.info("mcp_tool_call", tool=tool_name, server=tool.server_name)

        if config.transport == MCPTransport.STDIO:
            return await self._call_stdio_tool(tool.server_name, tool_name, arguments)

        return {"error": f"Tool call not implemented for {config.transport.value} transport"}

    @property
    def connected_count(self) -> int:
        """Number of connected MCP servers."""
        return len(self._connected_servers)

    # ------------------------------------------------------------------
    # Stdio transport — uses asyncio.create_subprocess_exec (not shell)
    # to prevent command injection.
    # ------------------------------------------------------------------

    async def _connect_stdio(self, config: MCPServerConfig) -> None:
        """Connect to an MCP server via stdio subprocess."""
        env = {**config.env} if config.env else None
        # Uses create_subprocess_exec (not shell) for safety
        proc = await asyncio.create_subprocess_exec(
            config.command,
            *config.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        self._processes[config.name] = proc

        # Send initialize request
        init_req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "vaultbot", "version": "0.1.0"},
            },
        }
        await self._send_jsonrpc(proc, init_req)

        # Send initialized notification
        await self._send_jsonrpc_notification(proc, "notifications/initialized", {})

        # Discover tools
        tools_req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        tools_resp = await self._send_jsonrpc(proc, tools_req)

        if tools_resp and "result" in tools_resp:
            for tool_data in tools_resp["result"].get("tools", []):
                tool = MCPTool(
                    name=tool_data.get("name", ""),
                    description=tool_data.get("description", ""),
                    input_schema=tool_data.get("inputSchema", {}),
                    server_name=config.name,
                )
                self._tools[tool.name] = tool

    async def _call_stdio_tool(
        self, server_name: str, tool_name: str, arguments: dict[str, Any]
    ) -> Any:
        """Call a tool via stdio transport."""
        proc = self._processes.get(server_name)
        if not proc or proc.returncode is not None:
            raise RuntimeError(f"MCP server '{server_name}' is not running")

        req = {
            "jsonrpc": "2.0",
            "id": 100,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        response = await self._send_jsonrpc(proc, req)
        if response and "result" in response:
            return response["result"]
        if response and "error" in response:
            raise RuntimeError(f"MCP tool error: {response['error']}")
        return None

    async def _connect_http(self, config: MCPServerConfig) -> None:
        """Connect to an MCP server via HTTP/SSE (placeholder)."""
        logger.info("mcp_http_connect", url=config.url)

    @staticmethod
    async def _send_jsonrpc(proc: asyncio.subprocess.Process, request: dict) -> dict | None:
        """Send a JSON-RPC request and read the response."""
        if not proc.stdin or not proc.stdout:
            return None

        data = json.dumps(request) + "\n"
        proc.stdin.write(data.encode("utf-8"))
        await proc.stdin.drain()

        try:
            line = await asyncio.wait_for(proc.stdout.readline(), timeout=10.0)
            if line:
                return json.loads(line.decode("utf-8"))
        except (TimeoutError, json.JSONDecodeError):
            pass
        return None

    @staticmethod
    async def _send_jsonrpc_notification(
        proc: asyncio.subprocess.Process, method: str, params: dict
    ) -> None:
        """Send a JSON-RPC notification (no response expected)."""
        if not proc.stdin:
            return
        data = json.dumps({"jsonrpc": "2.0", "method": method, "params": params}) + "\n"
        proc.stdin.write(data.encode("utf-8"))
        await proc.stdin.drain()
