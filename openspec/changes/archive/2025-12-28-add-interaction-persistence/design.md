# Design: Interaction Persistence

## Overview
This document describes the technical design for persisting completed interactions to local storage.

## Storage Architecture

### File Structure
```
~/.local/share/interactive-choice-mcp/
├── config.json                 # Existing config file (moved here)
└── sessions/
    ├── index.json              # Session index for quick lookup
    └── {session_id}.json       # Individual session files
```

### Session Index Format
```json
{
  "version": 1,
  "sessions": [
    {
      "session_id": "abc123",
      "title": "Choose option",
      "interface": "web",
      "status": "submitted",
      "started_at": "2025-01-01T12:00:00Z",
      "completed_at": "2025-01-01T12:05:00Z",
      "url": "http://localhost:17863/choice/abc123"
    }
  ]
}
```

### Individual Session Format
```json
{
  "version": 1,
  "session_id": "abc123",
  "title": "Choose option",
  "prompt": "Please select an option",
  "interface": "web",
  "selection_mode": "single",
  "options": [
    {"id": "opt1", "description": "Option 1", "recommended": true},
    {"id": "opt2", "description": "Option 2"}
  ],
  "result": {
    "action_status": "selected",
    "selected_indices": ["opt1"],
    "option_annotations": {"opt1": "Good choice"},
    "global_annotation": "Done"
  },
  "started_at": "2025-01-01T12:00:00Z",
  "completed_at": "2025-01-01T12:05:00Z",
  "url": "http://localhost:17863/choice/abc123"
}
```

## Components

### InteractionStore Class
```python
class InteractionStore:
    """Persistent storage for completed interactions."""
    
    def __init__(self, base_path: Path | None = None):
        self._base_path = base_path or Path.home() / ".local/share/interactive-choice-mcp"
        self._sessions_path = self._base_path / "sessions"
        self._index_path = self._sessions_path / "index.json"
        self._index: list[InteractionEntry] = []
        
    def load(self) -> None:
        """Load session index from disk."""
        
    def save_session(self, session: ChoiceSession | TerminalSession) -> None:
        """Persist a completed session."""
        
    def get_recent(self, limit: int = 5) -> list[InteractionEntry]:
        """Get most recent completed sessions for the sidebar."""
        
    def cleanup(self, retention_days: int = 3, max_sessions: int = 100) -> int:
        """Remove expired sessions. Returns count of removed sessions."""
```

### Integration Points

1. **Server Startup**: Call `InteractionStore.load()` and `InteractionStore.cleanup()`
2. **Session Completion**: Call `InteractionStore.save_session()` after `set_result()`
3. **Interaction List**: Merge in-memory sessions with `InteractionStore.get_recent()`

## Cleanup Strategy

1. **On Startup**: Remove sessions older than `retention_days`
2. **On Save**: If `max_sessions` exceeded, remove oldest sessions
3. **Periodic**: Optional background task every hour (if server runs long)

## Configuration

Add to `ProvideChoiceConfig`:
```python
retention_days: int = 3        # Days to keep sessions
max_sessions: int = 100        # Maximum sessions to store
persistence_enabled: bool = True  # Toggle persistence
```

## Migration

No migration needed - this is additive. Existing config file remains at current location.
