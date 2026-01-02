"""Thin wrapper for launching the MCP server during local development."""

from src.server import mcp


if __name__ == "__main__":
    mcp.run()
