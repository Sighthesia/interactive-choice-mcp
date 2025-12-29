"""Centralized path management for MCP data storage.

All persistent data (config, sessions, logs) is stored under a single
directory to simplify deployment and maintenance.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

__all__ = [
    "get_data_dir",
    "get_config_path",
    "get_sessions_dir",
    "get_logs_dir",
]

# Default data directory name (stored in project root or CWD)
_DATA_DIR_NAME = ".mcp-data"

# Cached data directory path
_data_dir: Optional[Path] = None


def _find_project_root() -> Path:
    """Find the project root directory.
    
    Looks for common project markers (pyproject.toml, .git) starting from CWD.
    Falls back to CWD if no markers are found.
    """
    cwd = Path.cwd()
    markers = ["pyproject.toml", ".git", "setup.py", "package.json"]
    
    # Check CWD and up to 3 parent directories
    for path in [cwd] + list(cwd.parents)[:3]:
        for marker in markers:
            if (path / marker).exists():
                return path
    
    return cwd


def get_data_dir() -> Path:
    """Get the unified data directory for MCP storage.
    
    Priority:
    1. MCP_DATA_DIR environment variable (if set)
    2. .mcp-data/ in project root
    
    The directory is created if it doesn't exist.
    """
    global _data_dir
    
    if _data_dir is not None:
        return _data_dir
    
    # Check environment variable first
    env_dir = os.environ.get("MCP_DATA_DIR")
    if env_dir:
        _data_dir = Path(env_dir)
    else:
        # Use project root
        project_root = _find_project_root()
        _data_dir = project_root / _DATA_DIR_NAME
    
    # Ensure directory exists
    _data_dir.mkdir(parents=True, exist_ok=True)
    return _data_dir


def get_config_path() -> Path:
    """Get the path to the config file."""
    return get_data_dir() / "config.json"


def get_sessions_dir() -> Path:
    """Get the directory for session storage."""
    sessions_dir = get_data_dir() / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    return sessions_dir


def get_logs_dir() -> Path:
    """Get the directory for log files."""
    logs_dir = get_data_dir() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir
