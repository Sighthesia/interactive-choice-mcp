# Tasks: Add WebSocket and Timeout Synchronization

- [ ] **Research & Setup**
    - [ ] Verify FastAPI WebSocket dependencies (should be included in standard FastAPI/Uvicorn).
    - [ ] Plan the WebSocket message schema.

- [ ] **Server-side Implementation (`choice/web.py`)**
    - [ ] Refactor `run_web_choice` to use a `deadline` timestamp instead of a fixed `asyncio.wait_for`.
    - [ ] Implement a background task to monitor the deadline and trigger timeout.
    - [ ] Add a WebSocket endpoint `/ws/{choice_id}`.
    - [ ] Implement a periodic push of `remaining_seconds` over WebSocket.
    - [ ] Handle `update_timeout` messages (or ensure POST config updates the deadline).
    - [ ] Implement a global `ACTIVE_CHOICES` registry.
    - [ ] Add a `/` dashboard route to list active choices.

- [ ] **Client-side Implementation (`choice/templates/choice.html`)**
    - [ ] Add WebSocket client initialization logic.
    - [ ] Implement message handlers for `sync` and `status`.
    - [ ] Update `startTimeout` and the countdown loop to accept external sync signals.
    - [ ] Implement Browser Notifications API logic (permission request + alerts).
    - [ ] Create a simple dashboard template/view for the `/` route.
    - [ ] Ensure the UI reflects the "Connected" status via the existing `connectionDot`.

- [ ] **Validation & Testing**
    - [ ] Manual test: Open web portal, verify countdown starts.
    - [ ] Manual test: Change timeout in UI, verify server deadline updates and client syncs.
    - [ ] Manual test: Disconnect/Reconnect WebSocket (if possible) and check recovery.
    - [ ] Unit test: Verify `deadline` calculation and update logic in `web.py`.
