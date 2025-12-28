# Tasks: Add Interaction Persistence

## Phase 1: Core Storage Implementation

### Task 1.1: Create InteractionStore Class
- [x] Create `choice/interaction_store.py` module
- [x] Implement `InteractionStore` class with:
  - `__init__`: Initialize paths and load index
  - `load()`: Load session index from disk
  - `save_session()`: Persist completed session
  - `get_recent()`: Get recent sessions for list
  - `cleanup()`: Remove expired sessions
- [x] Add unit tests for storage operations

### Task 1.2: Define Persistence Data Models
- [x] Add `PersistedSession` dataclass to `choice/interaction_store.py`
- [x] Add persistence config fields to `ProvideChoiceConfig`:
  - `retention_days: int = 3`
  - `max_sessions: int = 100`
  - `persistence_enabled: bool = True`

## Phase 2: Server Integration

### Task 2.1: Integrate with WebChoiceServer
- [x] Initialize `InteractionStore` in server startup
- [x] Call `cleanup()` on startup
- [x] Call `save_session()` after session completion
- [x] Merge persisted sessions in `get_interaction_list()`

### Task 2.2: Integrate with Terminal Sessions
- [x] Call `save_session()` after terminal session completion
- [x] Ensure terminal sessions are included in persistence

## Phase 3: Testing & Documentation

### Task 3.1: Add Integration Tests
- [x] Test session persistence across server restart
- [x] Test cleanup of expired sessions
- [x] Test max session limit enforcement

### Task 3.2: Update Documentation
- [x] Update AGENTS.md with persistence configuration
- [x] Update spec with new requirements
