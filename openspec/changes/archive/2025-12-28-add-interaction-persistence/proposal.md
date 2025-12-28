# Change Proposal: Add Interaction Persistence

## Summary
Add persistent storage for completed interactions, allowing users to view historical sessions after server restart. Sessions are stored with full data (options, selections, annotations) and automatically cleaned up based on configurable retention policies.

## Motivation
Currently, interaction history is lost when the server restarts. Users may want to:
- Review past interactions for reference
- Track decision patterns over time
- Recover context after server restarts

## Scope
- **In Scope**:
  - Persist completed sessions to local JSON storage
  - Load historical sessions on server startup
  - Automatic cleanup based on retention policy (default: 3 days)
  - Configurable maximum session count
  - Integration with existing interaction list WebSocket/REST endpoints
  
- **Out of Scope**:
  - Cloud/remote storage backends
  - Session export/import functionality
  - Search/filter historical sessions by content

## Technical Approach
1. Create `InteractionStore` class for session persistence
2. Store sessions as JSON files in `~/.local/share/interactive-choice-mcp/sessions/`
3. Add retention configuration to `ProvideChoiceConfig`:
   - `retention_days`: Default 3 days
   - `max_sessions`: Default 100 sessions
4. Clean up expired sessions on server startup and periodically during runtime
5. Extend `get_interaction_list()` to include persisted historical sessions

## Risk Assessment
- **Low**: Local file storage is simple and reliable
- **Medium**: Large session data could consume disk space → mitigated by retention limits

## Dependencies
- Existing `choice/storage.py` module for file operations pattern
- Existing `InteractionEntry` model for session representation

## Acceptance Criteria
- [ ] Completed sessions are persisted to disk
- [ ] Historical sessions appear in interaction list after server restart
- [ ] Sessions older than retention period are automatically cleaned
- [ ] Session count does not exceed configured maximum
