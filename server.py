"""MCP server entry point for Interactive Choice.

Initializes the FastMCP server and registers interactive choice tools.
"""

from mcp.server.fastmcp import FastMCP

from src.core.orchestrator import ChoiceOrchestrator
from src.mcp.tools import register_tools

# Initialize server components
mcp = FastMCP("Interactive Choice")
orchestrator = ChoiceOrchestrator()

# Register tools
register_tools(mcp, orchestrator)

if __name__ == "__main__":
    mcp.run()
