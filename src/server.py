"""MCP server entry point for Interactive Choice.

Initializes the FastMCP server and registers interactive choice tools.
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .core.orchestrator import ChoiceOrchestrator
from .mcp.tools import register_tools

__all__ = ["mcp"]

# Initialize server components
mcp = FastMCP("Interactive Choice")
orchestrator = ChoiceOrchestrator()

# Register tools so the MCP server exposes them to clients
register_tools(mcp, orchestrator)

if __name__ == "__main__":
    mcp.run()
