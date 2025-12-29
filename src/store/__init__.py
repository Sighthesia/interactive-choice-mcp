"""Session persistence store for interactive choice.

This package handles the persistence of completed interaction sessions,
enabling history viewing and analytics.

Modules:
    interaction_store: Manages session persistence to local filesystem

Example:
    from src.store import InteractionStore, PersistedSession

    store = InteractionStore()
    store.save(session)
    recent = store.list_recent(days=3)
"""
from .interaction_store import (
    InteractionStore,
    PersistedSession,
)

__all__ = [
    "InteractionStore",
    "PersistedSession",
]
