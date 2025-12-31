"""MCP server package for Interactive Choice.

This package provides tool registration and response formatting
for the interactive choice MCP tools (provide_choice, poll_selection).

The main MCP server instance is created in the root server.py file.
"""

from .response_formatter import format_mcp_response
from .tools import register_tools

__all__ = ["format_mcp_response", "register_tools"]
