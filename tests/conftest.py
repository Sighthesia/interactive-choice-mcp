"""Pytest configuration and shared fixtures.

This module provides common fixtures and configuration for all tests.
The test directory is organized as follows:

    tests/
    ├── conftest.py          # Shared fixtures and configuration
    ├── unit/                 # Unit tests (isolated, fast)
    │   ├── core/            # Core models, validation, response
    │   ├── infra/           # Infrastructure (i18n, logging, storage)
    │   ├── store/           # Session persistence
    │   ├── terminal/        # Terminal client
    │   └── web/             # Web server components
    └── integration/         # Integration tests (full flow)
"""
import sys
from pathlib import Path

# Ensure repository root is on sys.path so tests can import local packages
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
